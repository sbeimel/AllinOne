#!/usr/bin/env python3
"""
Syntax Test für alle Python Module
Prüft nur die Syntax, keine Runtime-Tests
"""
import py_compile
import sys

modules = [
    "scanner.py",
    "scanner_async.py",
    "stb_scanner.py",
    "stb_async.py",
    "scanner_scheduler.py",
    "mac_pattern_generator.py",
    "migrate_vpn_detection.py",
    "app-docker.py"
]

print("=" * 60)
print("SYNTAX TEST - Alle Python Module")
print("=" * 60)
print()

failed = []
passed = []

for module in modules:
    try:
        py_compile.compile(module, doraise=True)
        print(f"✅ {module:40s} - Syntax OK")
        passed.append(module)
    except py_compile.PyCompileError as e:
        print(f"❌ {module:40s} - Syntax ERROR")
        print(f"   {e}")
        failed.append(module)

print()
print("=" * 60)
print("ERGEBNIS")
print("=" * 60)
print(f"✅ Passed: {len(passed)}/{len(modules)}")
print(f"❌ Failed: {len(failed)}/{len(modules)}")

if failed:
    print()
    print("Fehlerhafte Module:")
    for module in failed:
        print(f"  - {module}")
    sys.exit(1)
else:
    print()
    print("🎉 ALLE MODULE HABEN KORREKTE SYNTAX!")
    print()
    print("Nächste Schritte:")
    print("1. Dependencies installieren: pip install -r requirements.txt")
    print("2. Runtime Tests durchführen")
    print("3. Docker Container bauen und testen")
    sys.exit(0)
