#!/bin/bash
# Pre-Deployment Test - Prüft alles vor Docker Build

set -e  # Exit on error

echo "=========================================="
echo "PRE-DEPLOYMENT TEST"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Test 1: Syntax Check
echo "1️⃣  Syntax Check..."
if python3 test_syntax.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Alle Module kompilieren${NC}"
else
    echo -e "   ${RED}❌ Syntax Fehler gefunden!${NC}"
    python3 test_syntax.py
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 2: Dockerfile Completeness
echo "2️⃣  Dockerfile Completeness..."
if python3 test_dockerfile_completeness.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Alle Module werden kopiert${NC}"
else
    echo -e "   ${RED}❌ Module fehlen im Dockerfile!${NC}"
    python3 test_dockerfile_completeness.py
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 3: Required Files
echo "3️⃣  Required Files Check..."
REQUIRED_FILES=(
    "app-docker.py"
    "scanner.py"
    "scanner_async.py"
    "stb.py"
    "stb_scanner.py"
    "stb_async.py"
    "utils.py"
    "scanner_scheduler.py"
    "mac_pattern_generator.py"
    "migrate_vpn_detection.py"
    "Dockerfile"
    "requirements.txt"
    "start.sh"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo -e "   ${GREEN}✅ Alle benötigten Dateien vorhanden${NC}"
else
    echo -e "   ${RED}❌ Fehlende Dateien:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo "      - $file"
    done
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 4: Templates Check
echo "4️⃣  Templates Check..."
REQUIRED_TEMPLATES=(
    "templates/scanner.html"
    "templates/scanner-new.html"
)

MISSING_TEMPLATES=()
for template in "${REQUIRED_TEMPLATES[@]}"; do
    if [ ! -f "$template" ]; then
        MISSING_TEMPLATES+=("$template")
    fi
done

if [ ${#MISSING_TEMPLATES[@]} -eq 0 ]; then
    echo -e "   ${GREEN}✅ Alle Templates vorhanden${NC}"
else
    echo -e "   ${RED}❌ Fehlende Templates:${NC}"
    for template in "${MISSING_TEMPLATES[@]}"; do
        echo "      - $template"
    done
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 5: Import Test (mit installierten Dependencies)
echo "5️⃣  Import Test..."
python3 -c "
import sys
errors = []

modules = [
    'scanner',
    'scanner_async', 
    'stb',
    'stb_scanner',
    'stb_async',
    'utils',
    'scanner_scheduler',
    'mac_pattern_generator'
]

for module in modules:
    try:
        __import__(module)
    except Exception as e:
        errors.append(f'{module}: {e}')

if errors:
    print('❌ Import Fehler:')
    for error in errors:
        print(f'   {error}')
    sys.exit(1)
else:
    print('✅ Alle Module importierbar')
" 2>&1

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Alle Module importierbar${NC}"
else
    echo -e "   ${RED}❌ Import Fehler gefunden!${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 6: Feature Verification
echo "6️⃣  Feature Verification..."
python3 -c "
import scanner
import scanner_async
import stb_scanner
import stb_async

features = {
    'Portal Crawler (sync)': hasattr(scanner, 'crawl_portals_urlscan'),
    'Portal Crawler (async)': hasattr(scanner_async, 'crawl_portals_urlscan_async'),
    'VPN Detection (sync)': hasattr(scanner, 'detect_vpn_proxy'),
    'VPN Detection (async)': hasattr(scanner_async, 'detect_vpn_proxy_async'),
    'Portal Info (sync)': hasattr(stb_scanner, 'get_portal_info'),
    'Portal Info (async)': hasattr(stb_async, 'get_portal_info'),
    'LRU Cache (sync)': hasattr(stb_scanner.get_portal_info, '__wrapped__'),
    'LRU Cache (async)': hasattr(stb_async.get_portal_info, '__wrapped__'),
}

all_ok = True
for feature, exists in features.items():
    status = '✅' if exists else '❌'
    print(f'   {status} {feature}')
    if not exists:
        all_ok = False

exit(0 if all_ok else 1)
" 2>&1

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Alle Features vorhanden${NC}"
else
    echo -e "   ${RED}❌ Features fehlen!${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Test 7: Dockerfile Syntax
echo "7️⃣  Dockerfile Syntax..."
if docker build --dry-run -f Dockerfile . > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Dockerfile Syntax OK${NC}"
else
    # Fallback: Basic syntax check
    if grep -q "FROM python" Dockerfile && grep -q "COPY" Dockerfile && grep -q "CMD" Dockerfile; then
        echo -e "   ${GREEN}✅ Dockerfile Syntax OK (basic check)${NC}"
    else
        echo -e "   ${RED}❌ Dockerfile Syntax Fehler!${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi
echo ""

# Summary
echo "=========================================="
echo "ZUSAMMENFASSUNG"
echo "=========================================="
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALLE TESTS BESTANDEN!${NC}"
    echo ""
    echo "✅ Code ist bereit für Deployment"
    echo ""
    echo "Nächste Schritte:"
    echo "1. docker build -t macreplayxc:latest ."
    echo "2. docker run -d -p 8001:8001 -v \$(pwd)/data:/app/data macreplayxc:latest"
    echo "3. docker logs -f <container-id>"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS TEST(S) FEHLGESCHLAGEN!${NC}"
    echo ""
    echo "Bitte behebe die Fehler vor dem Deployment."
    echo ""
    exit 1
fi
