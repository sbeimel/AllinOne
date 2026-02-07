#!/usr/bin/env python3
"""
DB Migration: Add VPN/Proxy Detection Columns
Adds is_vpn and is_proxy columns to found_macs table
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Scanner database file
SCANNER_DB_FILE = os.path.join(
    os.getenv("CONFIG", "/app/data").replace("MacReplayXC.json", ""),
    "scans.db"
)

def migrate_vpn_detection():
    """Add VPN/Proxy detection columns to found_macs table"""
    try:
        conn = sqlite3.connect(SCANNER_DB_FILE)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(found_macs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_needed = []
        
        if 'is_vpn' not in columns:
            migrations_needed.append('is_vpn')
        
        if 'is_proxy' not in columns:
            migrations_needed.append('is_proxy')
        
        if not migrations_needed:
            logger.info("✅ VPN/Proxy detection columns already exist")
            conn.close()
            return True
        
        # Add missing columns
        for column in migrations_needed:
            logger.info(f"Adding column: {column}")
            cursor.execute(f'ALTER TABLE found_macs ADD COLUMN {column} BOOLEAN DEFAULT 0')
        
        # Create index for faster queries
        if 'is_vpn' in migrations_needed:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_vpn ON found_macs(is_vpn)')
        
        if 'is_proxy' in migrations_needed:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_proxy ON found_macs(is_proxy)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Migration complete: Added {', '.join(migrations_needed)} columns")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("VPN/Proxy Detection DB Migration")
    print("=" * 60)
    print(f"Database: {SCANNER_DB_FILE}")
    print()
    
    if migrate_vpn_detection():
        print("\n✅ Migration successful!")
    else:
        print("\n❌ Migration failed!")
