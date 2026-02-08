#!/usr/bin/env python3
"""
Test ob alle benötigten Dateien im Dockerfile kopiert werden
"""
import re
import os

# Lese Dockerfile
with open('Dockerfile', 'r') as f:
    dockerfile_content = f.read()

# Finde alle COPY Befehle für .py Dateien
copied_files = set()
for line in dockerfile_content.split('\n'):
    if line.strip().startswith('COPY') and '.py' in line:
        # Extrahiere Dateinamen
        parts = line.split()
        for part in parts:
            if part.endswith('.py'):
                copied_files.add(part)

# Liste aller Python Module die existieren
existing_modules = set()
for file in os.listdir('.'):
    if file.endswith('.py') and not file.startswith('test_'):
        existing_modules.add(file)

# Prüfe welche Module importiert werden
import ast

required_modules = set()
main_files = ['app-docker.py', 'scanner.py', 'scanner_async.py', 'stb.py', 'utils.py']

for file in main_files:
    if os.path.exists(file):
        with open(file, 'r') as f:
            try:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module_file = alias.name + '.py'
                            if module_file in existing_modules:
                                required_modules.add(module_file)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_file = node.module + '.py'
                            if module_file in existing_modules:
                                required_modules.add(module_file)
            except Exception as e:
                print(f"⚠️  Fehler beim Parsen von {file}: {e}")

print("=" * 70)
print("DOCKERFILE COMPLETENESS TEST")
print("=" * 70)
print()

print("📦 EXISTIERENDE PYTHON MODULE:")
for module in sorted(existing_modules):
    print(f"   {module}")
print()

print("📋 BENÖTIGTE MODULE (importiert in Hauptdateien):")
for module in sorted(required_modules):
    print(f"   {module}")
print()

print("✅ IM DOCKERFILE KOPIERT:")
for module in sorted(copied_files):
    print(f"   {module}")
print()

# Finde fehlende Module
missing = required_modules - copied_files
if missing:
    print("❌ FEHLEN IM DOCKERFILE:")
    for module in sorted(missing):
        print(f"   {module}")
    print()
    print("🔧 FÜGE FOLGENDE ZEILEN ZUM DOCKERFILE HINZU:")
    print()
    for module in sorted(missing):
        print(f"COPY {module} .")
    print()
    exit(1)
else:
    print("🎉 ALLE BENÖTIGTEN MODULE WERDEN KOPIERT!")
    print()

# Prüfe auch optionale Module
optional = existing_modules - required_modules - copied_files
if optional:
    print("ℹ️  OPTIONALE MODULE (nicht importiert, nicht kopiert):")
    for module in sorted(optional):
        print(f"   {module}")
    print()

print("=" * 70)
print("ZUSAMMENFASSUNG")
print("=" * 70)
print(f"Existierende Module:  {len(existing_modules)}")
print(f"Benötigte Module:     {len(required_modules)}")
print(f"Kopierte Module:      {len(copied_files)}")
print(f"Fehlende Module:      {len(missing)}")
print()

if missing:
    print("❌ DOCKERFILE IST UNVOLLSTÄNDIG!")
    exit(1)
else:
    print("✅ DOCKERFILE IST VOLLSTÄNDIG!")
    exit(0)
