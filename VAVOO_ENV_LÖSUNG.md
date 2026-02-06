# ✅ Vavoo Environment Variable Lösung

## Einfache Lösung

Statt komplizierte Funktionen zu ändern, lesen wir `PUBLIC_HOST` und `PORT` direkt aus Environment-Variablen.

## Änderungen

### 1. vavoo2.py (Zeile 1-10)

```python
import os

# Read from environment variables (set by Docker)
PORT = int(os.getenv("VAVOO_PORT", "4323"))
PUBLIC_HOST = os.getenv("VAVOO_PUBLIC_HOST", "")
PLAYLIST_DIR = "/app/data/vavoo_playlists"
```

**Vorher**: Hardcoded `PORT = 4323` und `PUBLIC_HOST = ""`
**Nachher**: Aus Environment-Variablen gelesen

### 2. start.sh

```bash
# Extract hostname from HOST env var
# HOST="http://your-domain.com:8001"
# → VAVOO_PUBLIC_HOST="your-domain.com"
# → VAVOO_PORT="4323"

PUBLIC_HOSTNAME=$(echo "$HOST" | sed 's|https\?://||' | cut -d':' -f1)
export VAVOO_PUBLIC_HOST="$PUBLIC_HOSTNAME"
export VAVOO_PORT="4323"
```

## Wie es funktioniert

### Beispiel 1: Lokaler Zugriff

```bash
HOST="0.0.0.0:8001"
→ VAVOO_PUBLIC_HOST="0.0.0.0"
→ VAVOO_PORT="4323"
→ Playlist URLs: http://0.0.0.0:4323/vavoo?...
```

### Beispiel 2: Externer Zugriff

```bash
HOST="http://your-domain.com:8001"
→ VAVOO_PUBLIC_HOST="your-domain.com"
→ VAVOO_PORT="4323"
→ Playlist URLs: http://your-domain.com:4323/vavoo?...
```

## Deployment

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Test

1. Playlist generieren: `http://your-domain.com:4323/playlist/DE.m3u`
2. Playlist öffnen → URLs sollten `your-domain.com:4323` enthalten
3. VLC öffnen → Stream sollte funktionieren ✅

## Vorteile

- ✅ **Einfach**: Nur 2 Dateien geändert
- ✅ **Sauber**: Keine komplexen Funktionen
- ✅ **Flexibel**: Funktioniert lokal und extern
- ✅ **Wartbar**: Vavoo-Code bleibt größtenteils original

## Zusammenfassung

**Geänderte Dateien**:
1. `vavoo/vavoo2.py` - Zeile 1-10 (Environment-Variablen)
2. `start.sh` - Setzt VAVOO_PUBLIC_HOST und VAVOO_PORT

**Keine weiteren Änderungen nötig!**

Vavoo nutzt jetzt automatisch die richtigen URLs basierend auf der `HOST` Environment-Variable.
