# 🚀 Vavoo Integration in MacReplayXC

## Übersicht

Vavoo wurde erfolgreich als **Blueprint** in MacReplayXC integriert. Die Vavoo IPTV Proxy-Funktionalität ist jetzt über denselben Port (8001) erreichbar.

## ✅ Was wurde implementiert

### 1. Blueprint-Integration
- **Datei**: `vavoo_blueprint.py`
- Konvertiert die Vavoo Flask-App in einen Blueprint
- Alle Vavoo-Routes sind unter `/vavoo/*` verfügbar
- Vavoo bleibt als separate `vavoo2.py` Datei erhalten
- **Background-Worker werden automatisch gestartet:**
  - Resolution Workers (wenn RES-Mode aktiviert)
  - Refresh Worker (für automatische Playlist-Updates)
  - Initial Refresh (lädt alle konfigurierten Regionen)

### 2. Web-UI Integration
- **Neuer Reiter**: "Vavoo" in der Navigation
- **Template**: `templates/vavoo.html`
- Eingebettetes Vavoo-Dashboard via iFrame
- Optisch an MacReplayXC angepasst (Dark Mode, Tabler UI)

### 3. Route-Struktur
```
MacReplayXC (Port 8001)
├── /                    → Dashboard
├── /portals             → Portal Management
├── /editor              → Channel Editor
├── /epg                 → EPG Manager
├── /vods                → VOD & Series
├── /xc-users            → XC API Users
├── /vavoo_page          → Vavoo UI (Wrapper)
│   └── iFrame → /vavoo/ (Vavoo Dashboard)
├── /vavoo/*             → Alle Vavoo-Routes
│   ├── /vavoo/          → Vavoo Dashboard
│   ├── /vavoo/health    → Health Check
│   ├── /vavoo/stats     → Statistics
│   ├── /vavoo/api/*     → Vavoo API
│   └── /vavoo/playlist/<region>.m3u
└── /settings            → Settings
```

## 📁 Dateistruktur

```
MacReplayXC/
├── app-docker.py                    # Haupt-App (Vavoo Blueprint registriert)
├── vavoo_blueprint.py               # Blueprint-Wrapper für Vavoo
├── templates/
│   ├── base.html                    # Navigation mit Vavoo-Link
│   └── vavoo.html                   # Vavoo-Seite (iFrame)
└── vavoo/
    ├── vavoo2.py                    # Original Vavoo-App
    ├── mapping.json                 # Channel-Mappings
    ├── logos.txt                    # Logo-Index
    ├── logos/                       # Channel-Logos
    └── config.json                  # Vavoo-Konfiguration
```

## 🔧 Konfiguration

### Vavoo-Pfade (Docker-optimiert)
```python
PLAYLIST_DIR = "/app/data/vavoo_playlists"  # Playlists
CONFIG_FILE = "config.json"                  # Vavoo-Config
MAPPING_FILE = "mapping.json"                # Channel-Mappings
```

### Background-Worker (Automatisch gestartet)
Vavoo startet beim Import automatisch mehrere Background-Prozesse:

1. **Refresh Worker** (Immer aktiv)
   - Aktualisiert Playlists alle 10 Minuten
   - Läuft als Daemon-Prozess

2. **Resolution Workers** (Optional, nur wenn RES=true)
   - FFmpeg-basierte Qualitätserkennung
   - 4 Worker-Prozesse (CPU-intensiv)

3. **Initial Refresh** (Einmalig beim Start)
   - Lädt alle konfigurierten Regionen

**Siehe:** `VAVOO_BACKGROUND_WORKERS.md` für Details

### Volumes (docker-compose.yml)
```yaml
volumes:
  - ./data:/app/data              # Enthält vavoo_playlists/
  - ./logs:/app/logs
```

## 🎯 Verwendung

### 1. Vavoo-Dashboard öffnen
- Navigiere zu **Vavoo** in der Menüleiste
- Oder direkt: `http://localhost:8001/vavoo_page`

### 2. Region hinzufügen
1. Im Vavoo-Dashboard: Region auswählen (z.B. Germany)
2. Klick auf "Add & Build"
3. Warten bis Playlist generiert ist

### 3. Playlist abrufen
```
http://localhost:8001/vavoo/playlist/DE.m3u
http://localhost:8001/vavoo/playlist/FR.m3u
http://localhost:8001/vavoo/playlist/IT.m3u
```

### 4. Kombinierte Playlists
- Mehrere Regionen auswählen (Multiselect)
- Erstellt kombinierte Playlist: `DE_FR_IT.m3u`

## 🔗 API-Endpunkte

### Vavoo-spezifische Endpunkte
```
GET  /vavoo/                          → Dashboard
GET  /vavoo/health                    → Health Check
GET  /vavoo/stats                     → Statistiken
GET  /vavoo/playlist/<region>.m3u     → M3U Playlist
GET  /vavoo/api/status                → Region Status
POST /vavoo/api/refresh/<region>      → Region aktualisieren
POST /vavoo/api/rebuild/<region>      → Region neu bauen
GET  /vavoo/api/connections           → Live Connections
```

### MacReplayXC-Endpunkte (unverändert)
```
GET  /player_api.php                  → XC API
GET  /get.php                         → M3U Playlist
GET  /xmltv.php                       → EPG
```

## ⚙️ Features

### Vavoo-Features
- ✅ Multi-Region Support (DE, FR, IT, ES, etc.)
- ✅ Resolution Scanning (FFmpeg)
- ✅ Proxy/Direct Streaming Mode
- ✅ Channel Filtering
- ✅ Live Connection Monitoring
- ✅ Kombinierte Playlists
- ✅ Logo-Mapping

### Integration-Features
- ✅ Selber Port (8001)
- ✅ Einheitliche Navigation
- ✅ Dark Mode Support
- ✅ Authentifizierung (MacReplayXC Auth)
- ✅ Docker-optimiert

## 🐛 Troubleshooting

### Problem: Vavoo-Blueprint nicht geladen
**Lösung:**
```bash
# Logs prüfen
docker-compose logs -f macreplayxc | grep Vavoo

# Erwartete Ausgabe:
# ✅ Vavoo Blueprint registered successfully at /vavoo
```

### Problem: Playlists werden nicht generiert
**Lösung:**
1. Vavoo-Dashboard öffnen: `/vavoo_page`
2. Region Status prüfen
3. "Rebuild" klicken
4. Logs prüfen: `docker-compose logs -f`

### Problem: iFrame lädt nicht
**Lösung:**
- Browser-Konsole öffnen (F12)
- Prüfen auf CORS/CSP-Fehler
- Direkt `/vavoo/` aufrufen zum Testen

### Problem: Logos fehlen
**Lösung:**
```bash
# Logos-Verzeichnis prüfen
ls -la vavoo/logos/

# logos.txt prüfen
cat vavoo/logos.txt | head -20
```

## 📊 Performance

### Speicherverbrauch
- **Vavoo allein**: ~200-300 MB RAM
- **MacReplayXC + Vavoo**: ~500-700 MB RAM
- **Mit RES-Scan**: +100-200 MB RAM

### Startup-Zeit
- **Ohne RES**: ~10-30 Sekunden
- **Mit RES**: ~2-5 Minuten (erste Region)

## 🔐 Sicherheit

### Authentifizierung
- Vavoo nutzt MacReplayXC-Authentifizierung
- Login-Seite: `/vavoo/login`
- Logout: `/vavoo/logout`

### Erste Anmeldung
- Beim ersten Login werden Credentials erstellt
- Username/Password werden in `vavoo/config.json` gespeichert

## 🚀 Nächste Schritte

### Mögliche Erweiterungen
1. **Vavoo-Channels in MacReplayXC-Editor**
   - Vavoo-Channels als zusätzliche Quelle
   - Gemeinsame Playlist-Generierung

2. **Unified EPG**
   - Vavoo-EPG + Portal-EPG kombinieren
   - Einheitliches XMLTV

3. **Channel-Mapping**
   - Automatisches Mapping zwischen Vavoo und Portals
   - Duplicate-Detection

4. **Performance-Optimierung**
   - Shared Cache zwischen Vavoo und MacReplayXC
   - Unified Proxy-System

## 📝 Changelog

### v3.0.0 - Vavoo Integration
- ✅ Vavoo als Blueprint integriert
- ✅ Neuer Reiter "Vavoo" in Navigation
- ✅ Einheitlicher Port (8001)
- ✅ Docker-optimierte Pfade
- ✅ Dark Mode Support

## 💡 Tipps

### Best Practices
1. **RES-Scan nur bei Bedarf aktivieren** (langsam)
2. **Proxy-Mode für Internet-Zugriff** (empfohlen)
3. **Direct-Mode nur für LAN** (schneller)
4. **Filter für Sport-Channels** (reduziert Playlist-Größe)
5. **Kombinierte Playlists für Multi-Country** (praktisch)

### Empfohlene Einstellungen
```json
{
  "RES": false,                          // Nur bei Problemen aktivieren
  "STREAM_MODE": true,                   // Proxy-Mode (empfohlen)
  "FILTER_ENABLED": false,               // Nur für spezielle Use-Cases
  "PLAYLIST_REBUILD_ON_START": true      // Immer aktuell
}
```

## 🎉 Fertig!

Vavoo ist jetzt vollständig in MacReplayXC integriert und über denselben Port erreichbar. Viel Spaß! 🚀
