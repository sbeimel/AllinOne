# 🚀 Scanner Features Quick Start

Schnellanleitung für alle neuen Scanner-Features.

---

## 📦 Installation

### Basis (erforderlich)
Alle Basis-Features funktionieren ohne zusätzliche Installation.

### Optional: Cloudscraper
Für Cloudflare-geschützte Portale:

```bash
pip install cloudscraper
```

Oder alle optionalen Dependencies:

```bash
pip install -r requirements_scanner_optional.txt
```

---

## 🔧 Setup

### 1. DB Migration (automatisch)
Die Datenbank wird beim nächsten Start automatisch migriert:
- `is_vpn` und `is_proxy` Spalten werden hinzugefügt
- Indices werden erstellt

**Oder manuell**:
```bash
python migrate_vpn_detection.py
```

### 2. Scheduler starten (optional)
```python
from scanner_scheduler import get_scheduler

scheduler = get_scheduler()
scheduler.load_jobs("/app/data/scheduler_jobs.json")
scheduler.start()
```

### 3. Pattern Generator laden (optional)
```python
from mac_pattern_generator import get_pattern_generator

generator = get_pattern_generator()
generator.load_patterns("/app/data/mac_patterns.json")
```

---

## 🎯 Feature 1: Portal Crawler

**Funktion**: Findet neue Portale von urlscan.io

### Verwendung (Python)
```python
import scanner

# Portale finden
portals = scanner.crawl_portals_urlscan()
print(f"Gefunden: {len(portals)} Portale")

# Async Version
import scanner_async
portals = await scanner_async.crawl_portals_urlscan_async()
```

### Verwendung (Frontend)
1. Scanner-Seite öffnen
2. Button "Find Portals" klicken
3. Portale werden in Alert angezeigt

---

## 🎯 Feature 2: Export All M3U

**Funktion**: Exportiert alle gefundenen MACs als M3U

### Verwendung (Frontend)
1. Scanner-Seite öffnen
2. Optional: Filter setzen (Portal, Min Channels, DE Only)
3. Button "Export All M3U" klicken
4. M3U wird automatisch heruntergeladen

### Verwendung (Python)
```python
import scanner

# Alle MACs exportieren
macs = scanner.get_found_macs()

# Mit Filtern
macs = scanner.get_found_macs(
    portal="http://portal.com/c",
    min_channels=10,
    de_only=True
)
```

---

## 🎯 Feature 3: 45+ Portal-Typen

**Funktion**: Erkennt 45+ verschiedene Portal-Typen

### Automatisch aktiv
Keine Konfiguration nötig! Das System erkennt automatisch:
- Stalker v1/v2/v3
- Ministra
- Flussonic
- TVIP
- Infomir/MAG
- Smart IPTV
- OTT Player
- Und 38+ weitere...

### Verwendung (Python)
```python
import stb_scanner

# Portal-Info abrufen
info = stb_scanner.get_portal_info("http://portal.com/c/c/c")
print(f"Portal-Typ: {info['portal_type']}")
print(f"Endpoint: {info['endpoint']}")
```

---

## 🎯 Feature 4: VPN/Proxy Detection

**Funktion**: Erkennt ob Portal hinter VPN/Proxy ist

### Verwendung (Python)
```python
import scanner

# Portal prüfen
result = scanner.detect_vpn_proxy("http://portal.com/c")

if result["is_vpn"]:
    print("⚠️ Portal ist hinter VPN/VPS")

if result["is_proxy"]:
    print("⚠️ Portal nutzt Proxy")

print(f"Confidence: {result['confidence']}")
```

### Verwendung (Async)
```python
import scanner_async

result = await scanner_async.detect_vpn_proxy_async("http://portal.com/c")
```

### Rate Limits
- **API**: ip-api.com
- **Limit**: 45 Requests/Minute (kostenlos)
- **Empfehlung**: Caching implementieren für häufige Portale

---

## 🎯 Feature 5: Cloudscraper

**Funktion**: Umgeht Cloudflare-Schutz automatisch

### Installation
```bash
pip install cloudscraper
```

### Automatisch aktiv
Nach Installation ist Cloudscraper automatisch aktiv:
- Cloudflare Challenges werden automatisch gelöst
- Fallback auf `requests` wenn nicht installiert
- Keine Code-Änderungen nötig

### Status prüfen
```python
import scanner

# Check ob Cloudscraper aktiv ist
# Log zeigt: "✅ Cloudscraper enabled - Cloudflare bypass active"
# Oder: "ℹ️ Cloudscraper not available - install with: pip install cloudscraper"
```

---

## 🎯 Feature 6: MAC-Listen Scheduler

**Funktion**: Automatische Scans zu festgelegten Zeiten

### Verwendung
```python
from scanner_scheduler import get_scheduler

scheduler = get_scheduler()

# Job hinzufügen
job_id = scheduler.add_job(
    portal_url="http://portal.com/c",
    mac_list=["00:1A:79:00:00:01", "00:1A:79:00:00:02"],
    schedule_time="02:00",  # 2 AM
    repeat="daily",         # once, hourly, daily, weekly
    name="Daily Portal Scan",
    proxy="http://proxy:8080",  # Optional
    settings={"speed": 50}      # Optional
)

# Scheduler starten
scheduler.start()

# Jobs speichern
scheduler.save_jobs("/app/data/scheduler_jobs.json")

# Jobs laden
scheduler.load_jobs("/app/data/scheduler_jobs.json")

# Job deaktivieren
scheduler.enable_job(job_id, enabled=False)

# Job entfernen
scheduler.remove_job(job_id)

# Alle Jobs anzeigen
jobs = scheduler.get_all_jobs()
for job in jobs:
    print(f"{job['name']}: Next run at {job['next_run']}")

# Scheduler stoppen
scheduler.stop()
```

### Repeat-Modi
- **once**: Einmalig zur angegebenen Zeit
- **hourly**: Jede Stunde zur angegebenen Minute
- **daily**: Jeden Tag zur angegebenen Zeit
- **weekly**: Jede Woche zur angegebenen Zeit

### Job Statistics
```python
job = scheduler.get_job(job_id)
print(f"Runs: {job['run_count']}")
print(f"Success: {job['success_count']}")
print(f"Fails: {job['fail_count']}")
print(f"Last run: {job['last_run']}")
print(f"Next run: {job['next_run']}")
```

---

## 🎯 Feature 7: MAC-Generator mit Patterns

**Funktion**: Lernt von erfolgreichen MACs und generiert ähnliche

### Verwendung
```python
from mac_pattern_generator import get_pattern_generator

generator = get_pattern_generator()

# Von erfolgreichen MACs lernen
successful_macs = [
    "00:1A:79:12:34:56",
    "00:1A:79:12:34:57",
    "00:1A:79:12:34:58",
    "00:1A:79:12:34:67",
    "00:1A:79:12:34:68"
]

generator.learn_from_mac_list(successful_macs)

# Kandidaten generieren
candidates = generator.generate_candidates(
    count=100,
    strategy="mixed"  # prefix, sequential, gap, mixed
)

print(f"Generiert: {len(candidates)} Kandidaten")
for mac in candidates[:5]:
    print(f"  - {mac}")

# Statistics anzeigen
stats = generator.get_statistics()
print(f"\nGelernt von {stats['total_macs_learned']} MACs")
print(f"Unique Prefixes: {stats['unique_prefixes']}")
print(f"\nTop Prefixes:")
for p in stats['top_prefixes']:
    print(f"  - {p['prefix']}: {p['count']}x")

# Patterns speichern
generator.save_patterns("/app/data/mac_patterns.json")

# Patterns laden
generator.load_patterns("/app/data/mac_patterns.json")
```

### Strategien

#### 1. Prefix-based
Nutzt häufige OUIs (erste 3 Oktette):
```python
candidates = generator.generate_candidates(100, strategy="prefix")
```

#### 2. Sequential
Generiert MACs um bekannte herum:
```python
candidates = generator.generate_candidates(100, strategy="sequential")
```

#### 3. Gap-based
Nutzt häufige Abstände zwischen MACs:
```python
candidates = generator.generate_candidates(100, strategy="gap")
```

#### 4. Mixed (empfohlen)
Kombination aller Strategien:
```python
candidates = generator.generate_candidates(100, strategy="mixed")
```

### Integration in Scanner
```python
import scanner
from mac_pattern_generator import get_pattern_generator

# 1. Erfolgreiche MACs sammeln
found_macs = scanner.get_found_macs(min_channels=10)
successful_macs = [mac['mac'] for mac in found_macs]

# 2. Patterns lernen
generator = get_pattern_generator()
generator.learn_from_mac_list(successful_macs)

# 3. Neue Kandidaten generieren
candidates = generator.generate_candidates(1000, strategy="mixed")

# 4. Kandidaten scannen
scanner.start_attack(
    portal_url="http://portal.com/c",
    mac_list=candidates
)
```

---

## 📊 Monitoring

### Cloudscraper Status
```bash
# Log prüfen
tail -f /app/logs/MacReplayXC.log | grep -i cloudscraper
```

### Scheduler Status
```python
from scanner_scheduler import get_scheduler

scheduler = get_scheduler()
jobs = scheduler.get_all_jobs()

print(f"Total Jobs: {len(jobs)}")
print(f"Active Jobs: {sum(1 for j in jobs if j['enabled'])}")

for job in jobs:
    if job['enabled']:
        print(f"\n{job['name']}:")
        print(f"  Next run: {job['next_run']}")
        print(f"  Runs: {job['run_count']}")
        print(f"  Success: {job['success_count']}")
        print(f"  Fails: {job['fail_count']}")
```

### Pattern Generator Stats
```python
from mac_pattern_generator import get_pattern_generator

generator = get_pattern_generator()
stats = generator.get_statistics()

print(f"Total MACs learned: {stats['total_macs_learned']}")
print(f"Unique Prefixes: {stats['unique_prefixes']}")
print(f"Unique Suffixes: {stats['unique_suffixes']}")
```

---

## 🐛 Troubleshooting

### Cloudscraper nicht aktiv
```bash
# Installation prüfen
pip list | grep cloudscraper

# Installieren
pip install cloudscraper

# Neustart
# Container/Service neu starten
```

### DB Migration fehlgeschlagen
```bash
# Manuell ausführen
python migrate_vpn_detection.py

# Oder DB neu initialisieren
rm /app/data/scans.db
# Beim nächsten Start wird DB neu erstellt
```

### Scheduler läuft nicht
```python
from scanner_scheduler import get_scheduler

scheduler = get_scheduler()

# Status prüfen
print(f"Running: {scheduler.running}")

# Starten falls nicht aktiv
if not scheduler.running:
    scheduler.start()
```

### Pattern Generator generiert keine MACs
```python
from mac_pattern_generator import get_pattern_generator

generator = get_pattern_generator()
stats = generator.get_statistics()

# Prüfen ob Patterns gelernt wurden
if stats['total_macs_learned'] == 0:
    print("Keine Patterns gelernt!")
    print("Lösung: Erst erfolgreiche MACs mit learn_from_mac_list() hinzufügen")
```

---

## 📚 Weitere Dokumentation

- **Vollständige Dokumentation**: `ALL_FEATURES_COMPLETE_2026-02-08.md`
- **Status**: `IMPLEMENTATION_STATUS_2026-02-08.md`
- **Migration Script**: `migrate_vpn_detection.py`
- **Scheduler**: `scanner_scheduler.py`
- **Pattern Generator**: `mac_pattern_generator.py`

---

## 🎉 Zusammenfassung

Alle 7 Features sind implementiert und einsatzbereit:

1. ✅ **Portal Crawler** - Findet neue Portale
2. ✅ **Export All M3U** - Exportiert alle MACs
3. ✅ **45+ Portal-Typen** - Erkennt mehr Portale
4. ✅ **VPN/Proxy Detection** - Erkennt VPN/Proxy
5. ✅ **Cloudscraper** - Umgeht Cloudflare
6. ✅ **Scheduler** - Automatische Scans
7. ✅ **Pattern Generator** - Intelligente MAC-Generierung

**Viel Erfolg!** 🚀
