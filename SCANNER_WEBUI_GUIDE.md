# 📖 Scanner WebUI - Komplette Anleitung

## 🎯 Wo werden die Daten gespeichert?

### Scanner Daten:
```
/app/data/scanner_config.json
```

**Inhalt:**
```json
{
  "settings": {
    "speed": 10,
    "timeout": 10,
    "mac_prefix": "00:1A:79:",
    "auto_save": true,
    ...
  },
  "found_macs": [
    {
      "mac": "00:1A:79:XX:XX:XX",
      "portal": "http://portal.com/c",
      "expiry": "December 31, 2025",
      "channels": 1234,
      "genres": ["DE Sport", "DE Movies", ...],
      "has_de": true,
      "de_genres": ["DE Sport", ...],
      "backend_url": "http://backend.com",
      "username": "user123",
      "password": "pass123",
      "found_at": "2026-02-07T12:34:56"
    }
  ],
  "proxies": ["http://proxy1:port", ...],
  "proxy_sources": ["https://spys.me/proxy.txt", ...]
}
```

### MacReplay Daten:
```
/app/data/MacReplayXC.json
```

**Beide Dateien sind im gleichen `/app/data` Volume!**

---

## 🔄 Wie greift MacReplay auf Scanner-Daten zu?

### Im Code:
```python
import scanner

# Get all found MACs
found_macs = scanner.get_found_macs()

# Get scanner settings
settings = scanner.get_scanner_settings()

# Add found MAC
scanner.add_found_mac(hit_data)
```

### Via API:
```bash
# Get all found MACs
curl http://localhost:8001/scanner/found-macs

# Get scanner settings
curl http://localhost:8001/scanner/settings

# Export found MACs
curl http://localhost:8001/scanner/export-found-macs > found_macs.json
```

---

## 🖥️ WebUI - Schritt für Schritt

### 1. Scanner öffnen

**URL:** `http://localhost:8001/scanner`

**Navigation:** Klick auf "MAC Scanner" in der Sidebar

---

### 2. Neuen Scan starten

#### Formular ausfüllen:

**Portal URL** (erforderlich)
```
http://portal.example.com/c
```

**Mode** (Dropdown)
- `Random MACs` - Generiert zufällige MACs
- `MAC List` - Nutzt eigene MAC-Liste

**Speed (Threads)**
```
10 (Standard)
1-50 möglich
```

**MAC Prefix** (für Random Mode)
```
00:1A:79: (Standard)
```

**Timeout (Sekunden)**
```
10 (Standard)
5-30 möglich
```

**Proxies** (optional, eine pro Zeile)
```
http://proxy1.com:8080
socks5://proxy2.com:1080
http://user:pass@proxy3.com:3128
```

**MAC List** (nur bei Mode "MAC List", eine pro Zeile)
```
00:1A:79:XX:XX:XX
00:1A:79:YY:YY:YY
00:1A:79:ZZ:ZZ:ZZ
```

#### Button klicken:
```
🚀 Start Scan
```

---

### 3. Scan überwachen

#### Active Scans Bereich zeigt:
- **Portal URL**
- **Mode** (Random/List)
- **Status** (Running/Paused)
- **Statistiken**:
  - Tested: Anzahl getesteter MACs
  - Hits: Anzahl gefundener MACs
  - Errors: Anzahl Fehler
  - Elapsed: Verstrichene Zeit
- **Progress Bar**: Hit-Rate in %
- **Current MAC**: Aktuell getesteter MAC
- **Current Proxy**: Aktuell genutzter Proxy

#### Steuerung:
- **⏸ Pause** - Scan pausieren
- **⏹ Stop** - Scan stoppen

**Auto-Refresh:** Alle 5 Sekunden

---

### 4. Hits anzeigen

#### Found MACs Tabelle zeigt:
- **Portal**: Portal URL
- **MAC**: MAC-Adresse
- **Expiry**: Ablaufdatum
- **Channels**: Anzahl Channels
- **DE**: 🇩🇪 wenn deutsche Channels
- **Found At**: Zeitpunkt des Fundes
- **Actions**: "Create Portal" Button

#### Buttons:
- **🔄 Refresh** - Hits neu laden
- **📥 Export** - Als JSON exportieren
- **🗑️ Clear All** - Alle Hits löschen

**Datenquelle:**
- Persistent: `/app/data/scanner_config.json`
- Live: Aktive Scans

**Auto-Refresh:** Alle 10 Sekunden

---

### 5. Portal aus Hit erstellen

#### Schritt 1: Hit auswählen
In der "Found MACs" Tabelle einen Hit finden

#### Schritt 2: "Create Portal" klicken
Button in der Actions-Spalte klicken

#### Schritt 3: Bestätigen
```
Create portal from MAC 00:1A:79:XX:XX:XX?
[OK] [Cancel]
```

#### Was passiert:
1. ✅ MAC wird validiert (Token + Expiry)
2. ✅ Portal wird erstellt mit:
   - Name: `domain.com 🇩🇪 (1234ch)`
   - URL: Portal URL
   - MAC: Gefundene MAC
   - Expiry: Ablaufdatum
3. ✅ Channels werden automatisch geladen
4. ✅ Genres werden erkannt
5. ✅ Redirect zu `/portals`

#### Portal-Name Format:
```
domain.com 🇩🇪 (1234ch)
         ↑      ↑
    DE-Genres  Channels
```

---

## 📊 Datenfluss

```
┌─────────────────────────────────────────────────────────┐
│  1. Scan starten                                        │
│     - Portal URL + Settings eingeben                    │
│     - "Start Scan" klicken                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  2. Scanner läuft                                       │
│     - Multi-threaded MAC Testing                        │
│     - Smart Proxy Rotation                              │
│     - Hit Detection                                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  3. Hit gefunden                                        │
│     - MAC validiert (Token + Channels)                  │
│     - Gespeichert in scanner_config.json                │
│     - Angezeigt in "Found MACs" Tabelle                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  4. "Create Portal" klicken                             │
│     - Hit-Daten werden gelesen                          │
│     - Portal wird erstellt                              │
│     - Channels werden geladen                           │
│     - Gespeichert in MacReplayXC.json                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  5. Portal verfügbar                                    │
│     - Sichtbar in /portals                              │
│     - Channels in channels.db                           │
│     - Bereit zum Streamen                               │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Erweiterte Nutzung

### Settings via API ändern:

```bash
curl -X POST http://localhost:8001/scanner/settings \
  -H "Content-Type: application/json" \
  -d '{
    "speed": 20,
    "timeout": 15,
    "require_channels_for_valid_hit": true,
    "min_channels_for_valid_hit": 10
  }'
```

### Proxies via API setzen:

```bash
curl -X POST http://localhost:8001/scanner/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "proxies": "http://proxy1:8080\nhttp://proxy2:8080"
  }'
```

### Found MACs via API abrufen:

```bash
curl http://localhost:8001/scanner/found-macs | jq
```

### Export via API:

```bash
curl http://localhost:8001/scanner/export-found-macs > found_macs.json
```

---

## 📁 Dateien & Locations

### Container:
```
/app/data/scanner_config.json    # Scanner Config & Found MACs
/app/data/MacReplayXC.json       # MacReplay Config & Portals
/app/data/channels.db            # Channel Database
/app/logs/MacReplayXC.log        # Logs
```

### Host (Docker Volume):
```
./data/scanner_config.json       # Scanner Config & Found MACs
./data/MacReplayXC.json          # MacReplay Config & Portals
./data/channels.db               # Channel Database
./logs/MacReplayXC.log           # Logs
```

---

## 🎯 Tipps & Tricks

### 1. Viele Hits finden:
- Nutze viele Proxies (50+)
- Erhöhe Speed (20-50 Threads)
- Nutze Random Mode
- Setze `min_channels_for_valid_hit: 1`

### 2. Nur gute Hits:
- Setze `min_channels_for_valid_hit: 100`
- Setze `require_channels_for_valid_hit: true`
- Filtere nach DE-Genres (🇩🇪)

### 3. Schneller scannen:
- Mehr Threads (Speed: 50)
- Kürzerer Timeout (5s)
- Viele Proxies nutzen

### 4. Proxy-Probleme vermeiden:
- Proxies vorher testen
- `max_proxy_errors: 10` erhöhen
- `unlimited_mac_retries: true` aktivieren

### 5. Hits persistent halten:
- `auto_save: true` (Standard)
- Regelmäßig exportieren
- Backup von `/app/data/scanner_config.json`

---

## ❓ FAQ

### Q: Wo sehe ich alle gefundenen MACs?
**A:** `/scanner` → "Found MACs" Tabelle (zeigt persistent + live)

### Q: Wie erstelle ich ein Portal aus einem Hit?
**A:** "Create Portal" Button in der "Found MACs" Tabelle klicken

### Q: Überleben Hits einen Container-Restart?
**A:** Ja! Gespeichert in `/app/data/scanner_config.json`

### Q: Kann ich Hits exportieren?
**A:** Ja! "Export" Button oder `/scanner/export-found-macs`

### Q: Wie lösche ich alle Hits?
**A:** "Clear All" Button in der "Found MACs" Tabelle

### Q: Wie ändere ich Scanner-Settings?
**A:** Via API: `POST /scanner/settings` oder Config-File editieren

### Q: Wo finde ich die Logs?
**A:** `/app/logs/MacReplayXC.log` oder `docker-compose logs -f`

### Q: Kann ich mehrere Scans parallel laufen lassen?
**A:** Ja! Jeder Scan läuft unabhängig

### Q: Was passiert wenn ein Scan pausiert wird?
**A:** Scan stoppt, kann mit "Pause" wieder fortgesetzt werden

### Q: Wie nutze ich Proxies?
**A:** Im Scan-Formular unter "Proxies" eingeben (eine pro Zeile)

---

## 🚀 Quick Start

```bash
# 1. Container starten
docker-compose up -d

# 2. Browser öffnen
http://localhost:8001

# 3. Login (falls aktiviert)

# 4. Scanner öffnen
Navigation → "MAC Scanner"

# 5. Scan starten
- Portal URL eingeben
- "Start Scan" klicken

# 6. Warten auf Hits
- Hits erscheinen in "Found MACs" Tabelle

# 7. Portal erstellen
- "Create Portal" Button klicken
- Fertig!
```

---

**Status:** ✅ Komplett dokumentiert und einsatzbereit!
