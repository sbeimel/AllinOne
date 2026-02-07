#!/usr/bin/env python3
"""
Migration Script: JSON → SQLite DB
Migrates scanner_config.json found_macs to scans.db
"""
import os
import json
import sqlite3
from datetime import datetime

# Paths
DATA_DIR = os.getenv("CONFIG", "/app/data").replace("MacReplayXC.json", "")
JSON_FILE = os.path.join(DATA_DIR, "scanner_config.json")
DB_FILE = os.path.join(DATA_DIR, "scans.db")

def migrate():
    """Migrate found_macs from JSON to DB"""
    
    print("=" * 60)
    print("Scanner Migration: JSON → SQLite DB")
    print("=" * 60)
    
    # Check if JSON file exists
    if not os.path.exists(JSON_FILE):
        print(f"✗ JSON file not found: {JSON_FILE}")
        print("  Nothing to migrate.")
        return
    
    # Load JSON
    print(f"\n1. Loading JSON file: {JSON_FILE}")
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Error loading JSON: {e}")
        return
    
    found_macs = data.get('found_macs', [])
    print(f"   Found {len(found_macs)} MACs in JSON")
    
    if len(found_macs) == 0:
        print("   Nothing to migrate.")
        return
    
    # Initialize DB
    print(f"\n2. Initializing database: {DB_FILE}")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create tables
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
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portal ON found_macs(portal)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_has_de ON found_macs(has_de)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channels ON found_macs(channels)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_found_at ON found_macs(found_at)')
        
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
        print("   ✓ Database initialized")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        conn.close()
        return
    
    # Migrate data
    print(f"\n3. Migrating {len(found_macs)} MACs to database...")
    migrated = 0
    skipped = 0
    errors = 0
    
    for hit in found_macs:
        try:
            # Insert MAC
            cursor.execute('''
                INSERT OR REPLACE INTO found_macs 
                (mac, portal, expiry, channels, has_de, backend_url, username, password, 
                 max_connections, created_at, client_ip, found_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                hit.get('mac'),
                hit.get('portal'),
                hit.get('expiry'),
                hit.get('channels', 0),
                hit.get('has_de', False),
                hit.get('backend_url'),
                hit.get('username'),
                hit.get('password'),
                hit.get('max_connections'),
                hit.get('created_at'),
                hit.get('client_ip'),
                hit.get('found_at', datetime.now().isoformat())
            ))
            
            mac_id = cursor.lastrowid
            
            # Insert genres
            for genre in hit.get('genres', []):
                is_de = 'DE' in genre.upper() or 'GERMAN' in genre.upper() or 'DEUTSCH' in genre.upper()
                cursor.execute('''
                    INSERT INTO genres (mac_id, genre, is_de)
                    VALUES (?, ?, ?)
                ''', (mac_id, genre, is_de))
            
            migrated += 1
            if migrated % 100 == 0:
                print(f"   Migrated {migrated}/{len(found_macs)}...")
        
        except Exception as e:
            errors += 1
            print(f"   ✗ Error migrating MAC {hit.get('mac')}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n4. Migration complete!")
    print(f"   ✓ Migrated: {migrated}")
    print(f"   ✗ Errors: {errors}")
    
    # Backup JSON and remove found_macs
    print(f"\n5. Cleaning up JSON file...")
    try:
        # Backup original
        backup_file = JSON_FILE + ".backup"
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   ✓ Backup created: {backup_file}")
        
        # Remove found_macs from JSON (keep settings, proxies, sources)
        if 'found_macs' in data:
            del data['found_macs']
        
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   ✓ Removed found_macs from JSON")
        print(f"   ✓ Settings, proxies, sources kept in JSON")
    except Exception as e:
        print(f"✗ Error cleaning up JSON: {e}")
    
    print("\n" + "=" * 60)
    print("Migration successful! 🎉")
    print("=" * 60)
    print(f"\nDatabase: {DB_FILE}")
    print(f"Config:   {JSON_FILE}")
    print(f"Backup:   {backup_file}")
    print("\nYou can now restart the container.")

if __name__ == "__main__":
    migrate()
