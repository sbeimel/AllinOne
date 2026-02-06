# ✅ Vavoo Integration - Single Container Lösung

## Architektur

**Ein Container, zwei Prozesse:**
- MacReplayXC läuft auf Port 8001 (Foreground)
- Vavoo läuft auf Port 4323 (Background)

## Wie es funktioniert

### Startup-Ablauf

```bash
Container startet
    ↓
start.sh wird ausgeführt
    ↓
1. Vavoo startet im Hintergrund (Port 4323)
    ↓
2. MacReplayXC startet im Vordergrund (Port 8001)
    ↓
Beide Apps laufen im gleichen Container
```

### Dateien

1. **start.sh** - Startup-Script
   - Startet Vavoo im Hintergrund
   - Startet MacReplayXC im Vordergrund
   - Beide Prozesse im gleichen Container

2. **Dockerfile** - Angepasst
   - Kopiert Vavoo-Dateien
   - Kopiert start.sh
   - Exponiert beide Ports (8001, 4323)
   - CMD: `./start.sh`

3. **docker-compose.yml** - Vereinfacht
   - Nur ein Service: `macreplayxc`
   - Beide Ports gemappt: 8001, 4323

4. **templates/vavoo.html** - iFrame
   - Lädt `http://localhost:4323/`

## Deployment

```bash
# Container stoppen
docker-compose down

# Neu bauen
docker-compose build --no-cache

# Starten
docker-compose up -d

# Logs anschauen
docker-compose logs -f
```

## Erwartete Logs

```
🚀 Starting MacReplayXC + Vavoo...
📡 Starting Vavoo on port 4323...
✅ Vavoo started (PID: 123)
🎬 Starting MacReplayXC on port 8001...
[INFO] MacReplayXC v3.0.0 - Server started on http://0.0.0.0:8001
```

## Test

1. Browser: `http://localhost:8001`
2. Login in MacReplayXC
3. Klick "Vavoo" in Navigation
4. **Erwartung**: Vavoo Dashboard lädt im iFrame

## Vorteile

- ✅ **Ein Container**: Einfacher zu managen
- ✅ **Beide Ports**: 8001 (MacReplayXC), 4323 (Vavoo)
- ✅ **Shared Filesystem**: Beide Apps können auf gleiche Daten zugreifen
- ✅ **Einfaches Deployment**: `docker-compose up -d`

## Troubleshooting

### Problem: Vavoo lädt nicht

**Lösung**: Logs prüfen
```bash
docker-compose logs | grep -i vavoo
```

Sollte zeigen:
```
✅ Vavoo started (PID: ...)
```

### Problem: Port 4323 nicht erreichbar

**Lösung**: Container neu starten
```bash
docker-compose restart
```

### Problem: Beide Apps starten nicht

**Lösung**: start.sh Permissions prüfen
```bash
docker exec -it MacReplayXC ls -la /app/start.sh
# Sollte executable sein: -rwxr-xr-x
```

## Zusammenfassung

### Was wurde geändert:

1. ✅ **start.sh** erstellt - Startet beide Apps
2. ✅ **Dockerfile** angepasst - Kopiert Vavoo + start.sh
3. ✅ **docker-compose.yml** vereinfacht - Ein Service, zwei Ports
4. ✅ **templates/vavoo.html** - iFrame auf localhost:4323

### Ergebnis:

- ✅ Ein Container
- ✅ Zwei Prozesse (MacReplayXC + Vavoo)
- ✅ Zwei Ports (8001 + 4323)
- ✅ iFrame Integration
- ✅ Sauber und einfach

## Fertig! 🎉

Jetzt läuft alles in **einem Container**!
