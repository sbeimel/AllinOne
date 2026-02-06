#!/usr/bin/env python3
"""
Test script for Vavoo integration in MacReplayXC
"""

import requests
import sys

def test_vavoo_integration():
    """Test if Vavoo is properly integrated."""
    
    base_url = "http://localhost:8001"
    
    tests = [
        {
            "name": "MacReplayXC Dashboard",
            "url": f"{base_url}/dashboard",
            "expected": 200
        },
        {
            "name": "Vavoo Page (Wrapper)",
            "url": f"{base_url}/vavoo_page",
            "expected": 200
        },
        {
            "name": "Vavoo Dashboard",
            "url": f"{base_url}/vavoo/",
            "expected": [200, 302]  # 302 if login required
        },
        {
            "name": "Vavoo Health Check",
            "url": f"{base_url}/vavoo/health",
            "expected": 200
        },
        {
            "name": "Vavoo Stats",
            "url": f"{base_url}/vavoo/stats",
            "expected": 200
        }
    ]
    
    print("🧪 Testing Vavoo Integration in MacReplayXC\n")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            response = requests.get(test["url"], timeout=5, allow_redirects=False)
            
            expected = test["expected"]
            if isinstance(expected, list):
                success = response.status_code in expected
            else:
                success = response.status_code == expected
            
            if success:
                print(f"✅ {test['name']}")
                print(f"   URL: {test['url']}")
                print(f"   Status: {response.status_code}")
                passed += 1
            else:
                print(f"❌ {test['name']}")
                print(f"   URL: {test['url']}")
                print(f"   Expected: {expected}, Got: {response.status_code}")
                failed += 1
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {test['name']}")
            print(f"   URL: {test['url']}")
            print(f"   Error: Connection refused (Is the server running?)")
            failed += 1
        except Exception as e:
            print(f"❌ {test['name']}")
            print(f"   URL: {test['url']}")
            print(f"   Error: {e}")
            failed += 1
        
        print()
    
    print("=" * 60)
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Vavoo integration is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(test_vavoo_integration())
