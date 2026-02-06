# 🐳 Docker Setup für Vavoo Integration

## ✅ Durchgeführte Änderungen

### 1. Dockerfile
**Änderungen:**
- ✅ Vavoo-Blueprint kopiert: `COPY vavoo_blueprint.py .`
- ✅ Vavoo-Verzeichnis kopiert: `COPY vavoo/ vavoo/`
- ✅ Playlist-Verzeichnis erstellt: `RUN mkdir -p /app/data/vavoo_playlists`

**Vollständiger Abschnitt:**
```dockerfile
# Copy application files
COPY app-docker.py app.py
COPY stb.py .
COPY utils.py .
COPY templates/ templates/
COPY static/ static/

# Copy Vavoo integration files
COPY vavoo_blueprint.py .
COPY vavoo/ vavoo/

# Copy documentation files (optional)
COPY docs/ docs/
```

### 2. .dockerignore
**Änderungen:**
- ✅ Vavoo-Dokumentation nicht ignoriert
- ✅ Test-Skript nicht ignoriert

**Hinzugefügt:**
```
!VAVOO_INTEGRATION.md
!VAVOO_CHANGES_SUMMARY.md
!test_vavoo_integration.py
```

### 3. docker-compose.yml
**Keine Änderungen nötig!** ✅

Die bestehende Konfiguration funktioniert bereits:
```yaml
services:
  macreplayxc:
    build: .
    container_name: MacReplayXC
    ports:
      - "8001:8001"  # Vavoo läuft auf demselben Port
    volumes:
      - ./data:/app/data              # Enthält vavoo_playlists/
      - ./logs:/app/logs
    environment:
      - HOST=0.0.0.0:8001
      - CONFIG=/app/data/MacReplayXC.json
    restart: unless-stopped
```

## 📁 Container-Verzeichnisstruktur

```
/app/
├── app.py                          # app-docker.py (umbenannt)
├── stb.py
├── utils.py
├── vavoo_blueprint.py              # NEU: Blueprint-Wrapper
├── templates/
│   ├── dashboard.html
│   ├── vavoo.html                  # NEU: Vavoo-Seite
│   └── ...
├── static/
├── vavoo/                          # NEU: Vavoo-Verzeichnis
│   ├── vavoo2.py                   # Vavoo-App
│   ├── mapping.json                # Channel-Mappings
│   ├── logos.txt                   # Logo-Index
│   ├── logos/                      # Channel-Logos
│   └── config.json                 # Vavoo-Config (wird erstellt)
├── data/                           # Volume-Mount
│   ├── MacReplayXC.json
│   ├── channels.db
│   ├── vods.db
│   └── vavoo_playlists/            # NEU: Vavoo-Playlists
│       ├── vavoo_playlist_DE.m3u
│       ├── vavoo_playlist_FR.m3u
│       └── ...
└── logs/                           # Volume-Mount
    └── MacReplayXC.log
```

## 🚀 Build & Deploy

### 1. Image neu bauen
```bash
# Container stoppen
docker-compose down

# Image neu bauen (mit --no-cache für sauberen Build)
docker-compose build --no-cache

# Container starten
docker-compose up -d

# Logs prüfen
docker-compose logs -f
```

### 2. Erwartete Log-Ausgaben
```
✅ Vavoo Blueprint created successfully
✅ Vavoo Blueprint registered successfully at /vavoo
MacReplayXC v3.0.0 - Server started on http://0.0.0.0:8001
```

### 3. Vavoo testen
```bash
# Health Check
curl http://localhost:8001/vavoo/health

# Erwartete Ausgabe:
# OK
# Channels: 0
# Resolved: 0

# Stats
curl http://localhost:8001/vavoo/stats

# Dashboard
curl http://localhost:8001/vavoo/
```

## 🔧 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'vavoo_blueprint'"
**Ursache:** Blueprint-Datei nicht kopiert

**Lösung:**
```bash
# Prüfen ob Datei im Container ist
docker exec -it MacReplayXC ls -la /app/vavoo_blueprint.py

# Wenn nicht vorhanden: Neu bauen
docker-compose build --no-cache
docker-compose up -d
```

### Problem: "FileNotFoundError: vavoo/vavoo2.py"
**Ursache:** Vavoo-Verzeichnis nicht kopiert

**Lösung:**
```bash
# Prüfen ob Verzeichnis im Container ist
docker exec -it MacReplayXC ls -la /app/vavoo/

# Wenn nicht vorhanden: Neu bauen
docker-compose build --no-cache
docker-compose up -d
```

### Problem: Vavoo-Playlists werden nicht gespeichert
**Ursache:** Verzeichnis nicht erstellt oder Volume nicht gemountet

**Lösung:**
```bash
# Prüfen ob Verzeichnis existiert
docker exec -it MacReplayXC ls -la /app/data/vavoo_playlists/

# Manuell erstellen falls nötig
docker exec -it MacReplayXC mkdir -p /app/data/vavoo_playlists

# Oder: Container neu starten
docker-compose restart
```

### Problem: Vavoo-Logos fehlen
**Ursache:** logos/ Verzeichnis nicht kopiert

**Lösung:**
```bash
# Prüfen ob Logos vorhanden sind
docker exec -it MacReplayXC ls -la /app/vavoo/logos/ | head -20

# Wenn leer: Neu bauen
docker-compose build --no-cache
docker-compose up -d
```

## 📊 Image-Größe

### Vorher (ohne Vavoo)
```
macreplayxc:3.0.0    ~450 MB
```

### Nachher (mit Vavoo)
```
macreplayxc:3.0.0    ~470 MB (+20 MB)
```

**Zusätzlicher Speicher:**
- vavoo2.py: ~100 KB
- vavoo_blueprint.py: ~5 KB
- mapping.json: ~50 KB
- logos.txt: ~100 KB
- logos/: ~20 MB (5000+ PNG-Dateien)

## 🔐 Sicherheit

### Vavoo-Authentifizierung
Vavoo hat ein **eigenes Login-System**:

1. **Erste Anmeldung:**
   - Beim ersten Zugriff auf `/vavoo/` wird Login-Seite angezeigt
   - Username/Password eingeben
   - Credentials werden in `/app/vavoo/config.json` gespeichert

2. **Nachfolgende Anmeldungen:**
   - Gleiche Credentials verwenden
   - Session wird in Cookie gespeichert

3. **Unabhängig von MacReplayXC:**
   - Vavoo-Login ≠ MacReplayXC-Login
   - Separate Authentifizierung

### Empfohlene Konfiguration
```json
{
  "WEB_USER": "admin",
  "WEB_PASS_HASH": "...",
  "RES": false,
  "STREAM_MODE": true,
  "FILTER_ENABLED": false,
  "LOCALES": [["de", "DE"]],
  "COMBINED_PLAYLISTS": []
}
```

## 🎯 Nächste Schritte

### Nach dem Build
1. ✅ Container starten: `docker-compose up -d`
2. ✅ Logs prüfen: `docker-compose logs -f | grep Vavoo`
3. ✅ Vavoo aufrufen: `http://localhost:8001/vavoo_page`
4. ✅ Region hinzufügen (z.B. Germany)
5. ✅ Playlist generieren
6. ✅ In IPTV-Player verwenden

### Empfohlene Einstellungen
```
RES Scan: false (nur bei Problemen)
Stream Mode: Proxy (für Internet-Zugriff)
Filter: false (alle Channels)
Rebuild on Start: true (immer aktuell)
```

## 📝 Checkliste

- [x] Dockerfile angepasst (vavoo_blueprint.py, vavoo/)
- [x] .dockerignore angepasst (Dokumentation nicht ignoriert)
- [x] docker-compose.yml geprüft (keine Änderungen nötig)
- [x] Verzeichnis erstellt (/app/data/vavoo_playlists)
- [x] Dokumentation erstellt (DOCKER_VAVOO_SETUP.md)

## 🎉 Fertig!

Das Docker-Setup ist vollständig für Vavoo konfiguriert. Nach dem Build ist Vavoo sofort einsatzbereit! 🚀

### Quick Start
```bash
# 1. Build
docker-compose build

# 2. Start
docker-compose up -d

# 3. Test
curl http://localhost:8001/vavoo/health

# 4. Browser
open http://localhost:8001/vavoo_page
```
