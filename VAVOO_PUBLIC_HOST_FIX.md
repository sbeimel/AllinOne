# Vavoo Public Host Fix

## Problem

Vavoo generiert Playlist-URLs mit der **internen Container-IP** (172.31.200.28:4323), aber VLC braucht die **externe URL** (rico.goip.de:4323).

## Lösung

### 1. Environment Variable (start.sh)

`start.sh` extrahiert den Public Host aus der `HOST` Environment-Variable:

```bash
# HOST="http://rico.goip.de:61096"
# → VAVOO_PUBLIC_HOST="rico.goip.de:4323"
```

### 2. Vavoo Anpassung (vavoo2.py)

Zwei neue Funktionen:

```python
def public_host():
    # Nutzt VAVOO_PUBLIC_HOST Environment-Variable
    env_host = os.getenv("VAVOO_PUBLIC_HOST", "").strip()
    if env_host and ":" in env_host:
        return env_host.split(":")[0]  # Nur Hostname
    # Fallback: AUTO-DETECT
    return ip()

def public_port():
    # Nutzt Port aus VAVOO_PUBLIC_HOST
    env_host = os.getenv("VAVOO_PUBLIC_HOST", "").strip()
    if env_host and ":" in env_host:
        return int(env_host.split(":")[1])  # Port extrahieren
    # Fallback: 4323
    return PORT
```

### 3. Alle PORT-Referenzen ersetzen

In vavoo2.py müssen alle `{PORT}` durch `{public_port()}` ersetzt werden:

**Suchen**: `:{PORT}/`
**Ersetzen**: `:{public_port()}/`

**Betroffene Zeilen** (ca. 10 Stellen):
- Playlist-Generierung
- Logo-URLs
- Segment-URLs
- Variant-URLs
- Server-URL Ausgabe

## Deployment

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Test

1. Playlist generieren: `http://rico.goip.de:4323/playlist/DE.m3u`
2. Playlist öffnen → URLs sollten `rico.goip.de:4323` enthalten
3. VLC öffnen → Stream sollte funktionieren

## Manuelle Änderungen nötig

Da automatisches Ersetzen fehlschlug, müssen folgende Zeilen in `vavoo/vavoo2.py` manuell geändert werden:

**Suche nach**: `:{PORT}/`
**Ersetze mit**: `:{public_port()}/`

**Beispiele**:
```python
# Vorher:
f"http://{host}:{PORT}/vavoo?"

# Nachher:
f"http://{host}:{public_port()}/vavoo?"
```

**Betroffene Funktionen**:
- `save_tv_playlist()` (Zeile ~252, ~263)
- `save_tv_playlist_external()` (Zeile ~1392, ~1403)
- `vavoo_variant()` (Zeile ~2033, ~2126, ~2130)
- `main()` (Zeile ~3361, ~3365)

## Zusammenfassung

- ✅ `start.sh` extrahiert Public Host
- ✅ `public_host()` und `public_port()` Funktionen hinzugefügt
- ⚠️ Alle `:{PORT}/` müssen manuell zu `:{public_port()}/` geändert werden

Nach diesen Änderungen sollten die Playlist-URLs die externe URL verwenden!
