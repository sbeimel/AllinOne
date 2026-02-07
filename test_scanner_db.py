#!/usr/bin/env python3
"""
Test Script: Scanner DB Implementation
Verifies that the SQLite database is working correctly
"""
import os
import sys
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scanner

def test_db_init():
    """Test database initialization"""
    print("=" * 60)
    print("TEST 1: Database Initialization")
    print("=" * 60)
    
    try:
        scanner.init_scanner_db()
        print("✓ Database initialized successfully")
        
        # Check if tables exist
        conn = scanner.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"✓ Tables created: {', '.join(tables)}")
        
        # Check indices
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = [row[0] for row in cursor.fetchall()]
        
        print(f"✓ Indices created: {', '.join(indices)}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_add_hit():
    """Test adding a hit to database"""
    print("\n" + "=" * 60)
    print("TEST 2: Add Hit to Database")
    print("=" * 60)
    
    try:
        test_hit = {
            "mac": "00:1A:79:AA:BB:CC",
            "portal": "http://test-portal.com/c",
            "expiry": "2025-12-31",
            "channels": 150,
            "has_de": True,
            "genres": ["DE: Sport", "DE: Movies", "Entertainment", "News"],
            "backend_url": "http://backend.com",
            "username": "test_user",
            "password": "test_pass",
            "max_connections": 1,
            "created_at": "2025-01-01",
            "client_ip": "192.168.1.1",
            "found_at": datetime.now().isoformat()
        }
        
        scanner.add_found_mac(test_hit)
        print(f"✓ Added hit: {test_hit['mac']} @ {test_hit['portal']}")
        print(f"  - Channels: {test_hit['channels']}")
        print(f"  - DE: {test_hit['has_de']}")
        print(f"  - Genres: {len(test_hit['genres'])}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_get_hits():
    """Test getting hits from database"""
    print("\n" + "=" * 60)
    print("TEST 3: Get Hits from Database")
    print("=" * 60)
    
    try:
        # Get all hits
        hits = scanner.get_found_macs()
        print(f"✓ Retrieved {len(hits)} hits")
        
        if hits:
            hit = hits[0]
            print(f"\nSample hit:")
            print(f"  - MAC: {hit['mac']}")
            print(f"  - Portal: {hit['portal']}")
            print(f"  - Channels: {hit['channels']}")
            print(f"  - DE: {hit['has_de']}")
            print(f"  - Genres: {hit.get('genres', [])}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_filters():
    """Test filtering hits"""
    print("\n" + "=" * 60)
    print("TEST 4: Filter Hits")
    print("=" * 60)
    
    try:
        # Add more test hits
        test_hits = [
            {
                "mac": "00:1A:79:11:22:33",
                "portal": "http://portal1.com/c",
                "expiry": "2025-12-31",
                "channels": 50,
                "has_de": False,
                "genres": ["Sport", "Movies"],
                "found_at": datetime.now().isoformat()
            },
            {
                "mac": "00:1A:79:44:55:66",
                "portal": "http://portal2.com/c",
                "expiry": "2025-12-31",
                "channels": 200,
                "has_de": True,
                "genres": ["DE: Sport", "DE: News"],
                "found_at": datetime.now().isoformat()
            },
            {
                "mac": "00:1A:79:77:88:99",
                "portal": "http://portal1.com/c",
                "expiry": "2025-12-31",
                "channels": 100,
                "has_de": True,
                "genres": ["DE: Movies", "Entertainment"],
                "found_at": datetime.now().isoformat()
            }
        ]
        
        for hit in test_hits:
            scanner.add_found_mac(hit)
        
        print(f"✓ Added {len(test_hits)} test hits")
        
        # Test filters
        print("\nFilter tests:")
        
        # Filter by portal
        portal1_hits = scanner.get_found_macs(portal="http://portal1.com/c")
        print(f"  - Portal 'portal1.com': {len(portal1_hits)} hits")
        
        # Filter by min channels
        high_channel_hits = scanner.get_found_macs(min_channels=100)
        print(f"  - Min 100 channels: {len(high_channel_hits)} hits")
        
        # Filter by DE only
        de_hits = scanner.get_found_macs(de_only=True)
        print(f"  - DE only: {len(de_hits)} hits")
        
        # Combined filters
        combined = scanner.get_found_macs(
            portal="http://portal1.com/c",
            min_channels=50,
            de_only=True
        )
        print(f"  - Combined (portal1 + min50ch + DE): {len(combined)} hits")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_stats():
    """Test statistics"""
    print("\n" + "=" * 60)
    print("TEST 5: Statistics")
    print("=" * 60)
    
    try:
        stats = scanner.get_found_macs_stats()
        
        print("Database statistics:")
        print(f"  - Total hits: {stats.get('total_hits', 0)}")
        print(f"  - Unique portals: {stats.get('unique_portals', 0)}")
        print(f"  - DE hits: {stats.get('de_hits', 0)}")
        print(f"  - Avg channels: {stats.get('avg_channels', 0):.1f}")
        print(f"  - Max channels: {stats.get('max_channels', 0)}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_portals_list():
    """Test portals list"""
    print("\n" + "=" * 60)
    print("TEST 6: Portals List")
    print("=" * 60)
    
    try:
        portals = scanner.get_portals_list()
        
        print(f"Found {len(portals)} unique portals:")
        for portal_info in portals:
            print(f"  - {portal_info['portal']}: {portal_info['hits']} hits")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_clear():
    """Test clearing database"""
    print("\n" + "=" * 60)
    print("TEST 7: Clear Database")
    print("=" * 60)
    
    try:
        # Get count before
        before = scanner.get_found_macs()
        print(f"Hits before clear: {len(before)}")
        
        # Clear
        scanner.clear_found_macs()
        print("✓ Database cleared")
        
        # Get count after
        after = scanner.get_found_macs()
        print(f"Hits after clear: {len(after)}")
        
        if len(after) == 0:
            print("✓ Database is empty")
            return True
        else:
            print("✗ Database not empty after clear")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SCANNER DATABASE TEST SUITE")
    print("=" * 60)
    print(f"Database file: {scanner.SCANNER_DB_FILE}")
    print(f"Config file: {scanner.SCANNER_CONFIG_FILE}")
    print()
    
    tests = [
        ("Database Initialization", test_db_init),
        ("Add Hit", test_add_hit),
        ("Get Hits", test_get_hits),
        ("Filters", test_filters),
        ("Statistics", test_stats),
        ("Portals List", test_portals_list),
        ("Clear Database", test_clear),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Database is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
