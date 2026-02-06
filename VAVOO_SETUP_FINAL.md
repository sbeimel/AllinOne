# ✅ Vavoo Setup - Finale Anleitung

## Wichtig: HOST Environment Variable

Damit Vavoo die richtigen URLs generiert, muss die `HOST` Variable in `docker-compose.yml` auf deine **externe URL** gesetzt werden.

## 1. docker-compose.yml anpassen

```yaml
environment:
  - HOST=http://your-domain.com:your-port  # ← DEINE URL HIER!
```

**Beispiele**: 
- Lokal: `HOST=http://localhost:8001`
- Extern: `HOST=http://your-domain.com:8001`
- Mit Port-Forwarding: `HOST=http://your-domain.com:61096`

## 2. Wie es funktioniert

```
docker-compose.yml
    ↓
HOST=http://your-domain.com:61096
    ↓
Container startet
    ↓
start.sh extrahiert Hostname
    ↓
VAVOO_PUBLIC_HOST=your-domain.com
VAVOO_PORT=4323
    ↓
vavoo2.py liest Environment-Variablen
    ↓
Playlist URLs: http://your-domain.com:4323/vavoo?...
```

## 3. Deployment

```bash
# 1. docker-compose.yml anpassen (HOST setzen)
# 2. Container neu bauen
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 4. Test

### Logs prüfen
```bash
docker-compose logs | grep -i vavoo
```

**Erwartung**:
```
📡 Vavoo public host: your-domain.com:4323
✅ Vavoo started (PID: 7)
📡 Server URL: http://your-domain.com:4323
```

### Playlist testen
```bash
# Playlist herunterladen
curl http://your-domain.com:4323/playlist/DE.m3u

# Sollte URLs mit your-domain.com:4323 enthalten
```

### VLC testen
1. VLC öffnen
2. Playlist laden: `http://your-domain.com:4323/playlist/DE.m3u`
3. Channel abspielen → Sollte funktionieren ✅

## 5. Port-Weiterleitung

**Wichtig**: Port 4323 muss von außen erreichbar sein!

### Router/Firewall
- Port 4323 → Container Port 4323
- Genau wie dein MacReplayXC Port → Container Port 8001

### Prüfen
```bash
# Von außen testen
curl http://your-domain.com:4323/

# Sollte Vavoo Login-Seite zurückgeben
```

## 6. Zusammenfassung

### Geänderte Dateien
1. ✅ `docker-compose.yml` - HOST auf externe URL setzen
2. ✅ `vavoo/vavoo2.py` - Liest PORT und PUBLIC_HOST aus ENV
3. ✅ `start.sh` - Setzt VAVOO_PUBLIC_HOST und VAVOO_PORT
4. ✅ `Dockerfile` - Kommentar hinzugefügt

### Ports
- **8001** (MacReplayXC) → Extern: Dein Port
- **4323** (Vavoo) → Extern: 4323

### Environment-Variablen
- `HOST` → Externe URL (z.B. http://your-domain.com:8001)
- `VAVOO_PUBLIC_HOST` → Automatisch gesetzt (your-domain.com)
- `VAVOO_PORT` → Automatisch gesetzt (4323)

## 7. Troubleshooting

### Problem: Playlist URLs zeigen falsche IP

**Ursache**: HOST nicht richtig gesetzt

**Lösung**: 
```yaml
# In docker-compose.yml
environment:
  - HOST=http://YOUR-DOMAIN:YOUR-PORT
```

### Problem: VLC kann Stream nicht öffnen

**Ursache**: Port 4323 nicht von außen erreichbar

**Lösung**: Port-Weiterleitung im Router prüfen

### Problem: Vavoo startet nicht

**Ursache**: Fehler in vavoo2.py

**Lösung**: Logs prüfen
```bash
docker-compose logs vavoo
```

## Fertig! 🎉

Jetzt sollte alles funktionieren:
- ✅ MacReplayXC läuft auf Port 8001
- ✅ Vavoo läuft auf Port 4323
- ✅ Beide im gleichen Container
- ✅ Vavoo generiert korrekte URLs
- ✅ VLC kann Streams abspielen
