# 🔄 Vavoo Background Workers

## Übersicht

Vavoo startet beim Import des Blueprints automatisch mehrere Background-Prozesse für die Verwaltung von Playlists und Streams.

## 🚀 Automatisch gestartete Prozesse

### 1. **Refresh Worker** (Immer aktiv)
**Zweck:** Automatische Aktualisierung der Playlists

**Funktion:**
- Läuft als Daemon-Prozess
- Aktualisiert alle konfigurierten Regionen
- Standard-Intervall: 600 Sekunden (10 Minuten)
- Kann manuell getriggert werden

**Aufgaben:**
```python
- Fetch Catalog von Vavoo API
- Resolve Stream URLs
- Gruppiere Channels nach Kategorien
- Generiere M3U Playlists
- Speichere auf Disk
```

**Log-Ausgabe:**
```
✅ Vavoo refresh worker started
✅ Vavoo initial refresh scheduled
```

### 2. **Resolution Workers** (Optional, nur wenn RES=true)
**Zweck:** FFmpeg-basierte Qualitätserkennung

**Funktion:**
- Läuft als Multiprocessing Pool
- Anzahl: min(4, CPU-Kerne)
- Probt jeden Stream mit FFmpeg
- Erkennt Auflösung und FPS

**Aufgaben:**
```python
- Parse Master-Playlist (m3u8)
- Teste Varianten mit FFmpeg
- Wähle beste Qualität (1080p50 > 720p50 > ...)
- Cache Ergebnis
```

**Log-Ausgabe:**
```
✅ 4 Vavoo resolution workers started
```

**⚠️ Warnung:**
- Sehr CPU-intensiv
- Erste Playlist-Generierung kann 2-5 Minuten dauern
- Nur aktivieren bei Problemen mit Stream-Qualität

### 3. **Initial Refresh** (Einmalig beim Start)
**Zweck:** Lädt alle konfigurierten Regionen beim Start

**Funktion:**
```python
request_refresh("*", rebuild=True)
```

**Bedeutung:**
- `"*"` = Alle Regionen
- `rebuild=True` = Kompletter Neu-Fetch (nicht nur URL-Refresh)

## 📊 Prozess-Hierarchie

```
MacReplayXC (Hauptprozess)
│
├── Waitress Server (48 Threads)
│   └── Flask App
│       ├── MacReplayXC Routes
│       └── Vavoo Blueprint
│
└── Vavoo Background Workers
    ├── Refresh Worker (Daemon)
    │   └── Läuft alle 10 Minuten
    │
    └── Resolution Workers (Optional, Daemon)
        ├── Worker 1
        ├── Worker 2
        ├── Worker 3
        └── Worker 4
```

## 🔧 Konfiguration

### Refresh-Intervall ändern
**Datei:** `vavoo/vavoo2.py`
```python
REFRESH_INTERVAL = 600  # Sekunden (Standard: 10 Minuten)
```

**Empfohlene Werte:**
- **300** (5 Min): Für häufige Updates
- **600** (10 Min): Standard, guter Kompromiss
- **1800** (30 Min): Für stabile Streams
- **3600** (1 Std): Minimale Updates

### RES-Mode aktivieren/deaktivieren
**Im Vavoo-Dashboard:**
1. Navigiere zu `/vavoo/`
2. Settings → Configuration
3. Checkbox "Resolution scan (RES)"
4. Save & Apply

**Oder in `vavoo/config.json`:**
```json
{
  "RES": false,
  "PLAYLIST_REBUILD_ON_START": true,
  "FILTER_ENABLED": false,
  "LOCALES": [["de", "DE"]],
  "COMBINED_PLAYLISTS": []
}
```

## 📈 Performance-Impact

### Ohne RES (Standard)
```
CPU: ~5-10% während Refresh
RAM: ~200-300 MB
Refresh-Dauer: 10-30 Sekunden
```

### Mit RES (Optional)
```
CPU: ~50-80% während Refresh
RAM: ~300-500 MB
Refresh-Dauer: 2-5 Minuten (erste Region)
```

## 🔍 Monitoring

### Prozess-Status prüfen
```bash
# Im Container
docker exec -it MacReplayXC ps aux | grep python

# Erwartete Ausgabe:
# python app.py                    (Hauptprozess)
# python -c ... refresh_worker     (Refresh Worker)
# python -c ... resolution_worker  (Resolution Worker 1-4, wenn RES=true)
```

### Logs prüfen
```bash
# Vavoo-spezifische Logs
docker-compose logs -f | grep Vavoo

# Erwartete Ausgabe:
# ✅ Vavoo refresh worker started
# ✅ Vavoo initial refresh scheduled
# ✅ Vavoo Blueprint registered successfully at /vavoo
```

### API-Status prüfen
```bash
# Region-Status
curl http://localhost:8001/vavoo/api/status

# Health Check
curl http://localhost:8001/vavoo/health

# Statistiken
curl http://localhost:8001/vavoo/stats
```

## 🛑 Worker stoppen/neustarten

### Kompletter Neustart
```bash
# Container neustarten (stoppt alle Worker)
docker-compose restart

# Oder: Container neu bauen
docker-compose down
docker-compose up -d
```

### Manueller Refresh triggern
```bash
# Alle Regionen
curl -X POST http://localhost:8001/vavoo/api/refresh/*

# Einzelne Region
curl -X POST http://localhost:8001/vavoo/api/refresh/DE

# Mit Rebuild (kompletter Neu-Fetch)
curl -X POST http://localhost:8001/vavoo/api/rebuild/DE
```

## ⚠️ Troubleshooting

### Problem: Refresh Worker läuft nicht
**Symptome:**
- Playlists werden nicht aktualisiert
- Status zeigt "STALE"

**Lösung:**
```bash
# Logs prüfen
docker-compose logs -f | grep "refresh worker"

# Wenn nicht vorhanden: Container neustarten
docker-compose restart
```

### Problem: Resolution Workers verbrauchen zu viel CPU
**Symptome:**
- CPU-Last bei 80-100%
- Container langsam

**Lösung:**
```bash
# RES-Mode deaktivieren
curl -X POST http://localhost:8001/vavoo/api/config \
  -H "Content-Type: application/json" \
  -d '{"RES": false}'

# Container neustarten
docker-compose restart
```

### Problem: Playlists werden nicht generiert
**Symptome:**
- `/vavoo/playlist/DE.m3u` gibt 404
- Status zeigt "NO DATA"

**Lösung:**
```bash
# Manuellen Rebuild triggern
curl -X POST http://localhost:8001/vavoo/api/rebuild/DE

# Logs prüfen
docker-compose logs -f | grep "DE"

# Warten bis Status "FRESH" zeigt
curl http://localhost:8001/vavoo/api/status
```

## 📝 Best Practices

### 1. RES-Mode nur bei Bedarf
```
✅ RES=false (Standard)
   - Schneller
   - Weniger CPU
   - Für die meisten Fälle ausreichend

❌ RES=true (Nur bei Problemen)
   - Langsamer
   - Hohe CPU-Last
   - Nur wenn Streams nicht funktionieren
```

### 2. Refresh-Intervall anpassen
```
✅ 600s (10 Min) - Standard
   - Guter Kompromiss
   - Nicht zu häufig, nicht zu selten

✅ 1800s (30 Min) - Stabile Streams
   - Weniger Last
   - Für stabile Vavoo-Streams

❌ 60s (1 Min) - Zu häufig
   - Unnötige Last
   - Kann zu Rate-Limits führen
```

### 3. Kombinierte Playlists
```
✅ Mehrere Regionen kombinieren
   - DE + AT + CH = DACH-Playlist
   - Nur ein Refresh für alle

❌ Jede Region einzeln
   - Mehr Refreshes
   - Mehr Last
```

## 🎯 Zusammenfassung

**Vavoo startet automatisch:**
- ✅ 1x Refresh Worker (Daemon)
- ✅ 0-4x Resolution Workers (Optional, Daemon)
- ✅ 1x Initial Refresh (Einmalig)

**Keine manuelle Konfiguration nötig!**

Die Worker laufen im Hintergrund und kümmern sich automatisch um:
- Playlist-Updates
- Stream-Qualität (optional)
- Region-Management

**Einfach Container starten und loslegen!** 🚀
