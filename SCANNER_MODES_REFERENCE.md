# 📖 SCANNER MODES REFERENCE
## Schnellreferenz für alle Scanner Modi

---

## 🎯 VERFÜGBARE MODI

### 1. RANDOM MODE ✅
**Beschreibung:** Generiert zufällige MAC Adressen und testet sie

**Verwendung:**
```
Mode: Random
MAC Prefix: 00:1A:79: (anpassbar)
```

**Funktionsweise:**
- Generiert MACs mit konfigurierbarem Prefix
- Testet jede MAC einmal
- Vermeidet Duplikate (scanned_macs Set)
- Läuft endlos bis gestoppt

**Use Cases:**
- Neue MACs finden
- Portal Discovery
- Brute Force Scanning
- Kontinuierliches Scanning

**Performance:**
- Sync: 10-50 MACs/Sekunde
- Async: 100-1000 MACs/Sekunde

---

### 2. LIST MODE ✅
**Beschreibung:** Scannt eine vordefinierte Liste von MAC Adressen

**Verwendung:**
```
Mode: List
MAC List: 
00:1A:79:XX:XX:XX
00:1A:79:YY:YY:YY
00:1A:79:ZZ:ZZ:ZZ
```

**Funktionsweise:**
- Lädt MACs aus Textfeld
- Scannt jede MAC einmal
- Stoppt wenn Liste erschöpft
- Retry Queue für fehlgeschlagene MACs

**Use Cases:**
- Bekannte MACs testen
- Import von MAC Listen
- Gezielte Scans
- Batch Validation

**Performance:**
- Sync: 10-50 MACs/Sekunde
- Async: 100-1000 MACs/Sekunde

**Hinweis:** Liste wird beim Start geparst und dedupliziert

---

### 3. REFRESH MODE ✅ **NEU!**
**Beschreibung:** Re-scannt alle gefundenen MACs für ein Portal

**Verwendung:**
```
Mode: Refresh
Portal URL: http://portal.example.com
```

**Funktionsweise:**
- Lädt alle MACs für dieses Portal aus Database
- Scannt jede MAC erneut
- Aktualisiert Status in Database
- Stoppt wenn alle MACs gescannt

**Use Cases:**
- MAC Status prüfen (noch aktiv?)
- Expiry Dates aktualisieren
- Channel Counts aktualisieren
- Regelmäßige Re-Validation
- Monitoring

**Performance:**
- Sync: 10-50 MACs/Sekunde
- Async: 100-1000 MACs/Sekunde

**Beispiel:**
```
1. Scan Portal mit Random Mode → 100 MACs gefunden
2. Nach 1 Woche: Refresh Mode starten
3. Scanner lädt 100 MACs aus DB
4. Re-scannt alle 100 MACs
5. Aktualisiert Status (aktiv/inaktiv)
```

---

## 🔄 MODE VERGLEICH

| Feature | Random | List | Refresh |
|---------|:------:|:----:|:-------:|
| MAC Source | Generiert | User Input | Database |
| Stoppt automatisch | ❌ | ✅ | ✅ |
| Endlos | ✅ | ❌ | ❌ |
| Duplikate | Vermeidet | Möglich | Keine |
| Use Case | Discovery | Validation | Monitoring |
| MAC Count | Unbegrenzt | User definiert | DB Count |

---

## 🚀 SCANNER TYPEN

### SYNC SCANNER (scanner.py)
**Route:** `/scanner`  
**Icon:** 🔍 Radar  
**Performance:** 2-5x schneller als Original

**Specs:**
- ThreadPoolExecutor (max 50 threads)
- DNS Caching (2-5x speedup)
- HTTP Connection Pooling (1.5-5x speedup)
- Batch DB Writes (10-50x speedup)

**Wann benutzen:**
- Wenige Proxies (<50)
- Kleine MAC Lists (<1000)
- Normale Scans
- Stabile Performance

---

### ASYNC SCANNER (scanner_async.py) ✅ **NEU!**
**Route:** `/scanner-new`  
**Icon:** 🚀 Rocket  
**Performance:** 10-100x schneller als Original

**Specs:**
- asyncio (max 1000 concurrent tasks)
- Async HTTP (aiohttp, 1000 connections)
- DNS Caching (2-5x speedup)
- Batch DB Writes (10-50x speedup)
- 70% weniger RAM
- 50% weniger CPU

**Wann benutzen:**
- Viele Proxies (>50)
- Große MAC Lists (>1000)
- Schnelle Scans gewünscht
- Maximale Performance

**Dependencies:**
```bash
pip install aiohttp aiodns
```

---

## 📊 MODE SELECTION GUIDE

### Szenario 1: Neues Portal entdecken
```
Scanner: Sync oder Async
Mode: Random
Speed: 10-50 (Sync) oder 100-500 (Async)
Proxies: Optional
```

### Szenario 2: Bekannte MACs testen
```
Scanner: Sync
Mode: List
MAC List: [Deine MACs]
Speed: 10-20
Proxies: Optional
```

### Szenario 3: Große MAC Liste (>1000)
```
Scanner: Async ✅
Mode: List
MAC List: [Deine MACs]
Speed: 200-500
Proxies: Empfohlen (>50)
```

### Szenario 4: MACs re-validieren
```
Scanner: Sync oder Async
Mode: Refresh ✅
Portal URL: [Dein Portal]
Speed: 10-50 (Sync) oder 100-500 (Async)
Proxies: Optional
```

### Szenario 5: Kontinuierliches Monitoring
```
Scanner: Async ✅
Mode: Refresh ✅
Portal URL: [Dein Portal]
Speed: 100-200
Proxies: Empfohlen
Schedule: Täglich/Wöchentlich
```

---

## 🔧 SETTINGS PRO MODE

### Random Mode Settings:
```json
{
  "speed": 10-50 (Sync) oder 100-500 (Async),
  "timeout": 10,
  "mac_prefix": "00:1A:79:",
  "proxies": "Optional",
  "unlimited_mac_retries": true
}
```

### List Mode Settings:
```json
{
  "speed": 10-20 (Sync) oder 100-200 (Async),
  "timeout": 10,
  "mac_list": "[MACs]",
  "proxies": "Optional",
  "max_mac_retries": 3
}
```

### Refresh Mode Settings:
```json
{
  "speed": 10-50 (Sync) oder 100-500 (Async),
  "timeout": 10,
  "portal_url": "[Portal]",
  "proxies": "Empfohlen",
  "max_mac_retries": 3
}
```

---

## 📈 PERFORMANCE TIPPS

### Random Mode:
- ✅ Höhere Speed = mehr MACs/Sekunde
- ✅ Proxies = weniger Blocks
- ✅ Async = 10-100x schneller
- ⚠️ Zu hohe Speed = mehr Errors

### List Mode:
- ✅ Batch Processing (100-1000 MACs)
- ✅ Async für große Listen (>1000)
- ✅ Proxies für schnellere Scans
- ⚠️ Duplikate entfernen vor Scan

### Refresh Mode:
- ✅ Regelmäßig ausführen (täglich/wöchentlich)
- ✅ Async für viele MACs (>100)
- ✅ Proxies für schnellere Re-Validation
- ✅ Niedrigere Speed = weniger Portal Load

---

## 🎯 BEST PRACTICES

### Mode Selection:
1. **Discovery:** Random Mode
2. **Validation:** List Mode
3. **Monitoring:** Refresh Mode

### Scanner Selection:
1. **Kleine Scans:** Sync Scanner
2. **Große Scans:** Async Scanner
3. **Viele Proxies:** Async Scanner

### Speed Settings:
1. **Sync:** 10-50 threads
2. **Async:** 100-500 tasks
3. **Mit Proxies:** Höher
4. **Ohne Proxies:** Niedriger

### Proxy Usage:
1. **Random Mode:** Empfohlen (weniger Blocks)
2. **List Mode:** Optional
3. **Refresh Mode:** Empfohlen (schneller)

---

## 🔄 MODE SWITCHING

### Von Random zu Refresh:
```
1. Random Mode starten
2. MACs finden und in DB speichern
3. Scanner stoppen
4. Refresh Mode starten (gleiches Portal)
5. MACs werden aus DB geladen
6. Re-Scan startet
```

### Von List zu Refresh:
```
1. List Mode mit MACs starten
2. Hits werden in DB gespeichert
3. Scanner stoppen
4. Refresh Mode starten (gleiches Portal)
5. Alle Hits werden re-gescannt
```

---

## 📊 MONITORING

### Random Mode:
- Tested: Anzahl getesteter MACs
- Hits: Anzahl gefundener MACs
- Errors: Anzahl Fehler
- Rate: MACs/Sekunde

### List Mode:
- Progress: X/Y MACs gescannt
- Hits: Anzahl gefundener MACs
- Errors: Anzahl Fehler
- ETA: Geschätzte Restzeit

### Refresh Mode:
- Progress: X/Y MACs re-gescannt
- Updated: Anzahl aktualisierter MACs
- Inactive: Anzahl inaktiver MACs
- ETA: Geschätzte Restzeit

---

## 🎉 ZUSAMMENFASSUNG

### Verfügbare Modi:
✅ **Random** - MAC Discovery  
✅ **List** - MAC Validation  
✅ **Refresh** - MAC Monitoring ✨ **NEU!**

### Verfügbare Scanner:
✅ **Sync** - Stabil, 2-5x schneller  
✅ **Async** - Ultra-schnell, 10-100x schneller ✨ **NEU!**

### Kombinationen:
- Random + Sync = Standard Discovery
- Random + Async = Schnelle Discovery
- List + Sync = Standard Validation
- List + Async = Schnelle Validation
- Refresh + Sync = Standard Monitoring
- Refresh + Async = Schnelle Monitoring ✨ **EMPFOHLEN!**

---

**Reference Ende**
