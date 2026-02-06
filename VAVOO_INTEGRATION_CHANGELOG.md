# Vavoo Integration Changelog

## Übersicht
Vollständige Integration von Vavoo IPTV Proxy in MacReplayXC v3.0.0 als Single-Container-Lösung.

---

## Geänderte Dateien

### 1. **start.sh** (NEU)
**Zweck:** Startup-Script für beide Anwendungen in einem Container

**Änderungen:**
- Startet Vavoo im Hintergrund auf Port 4323
- Startet MacReplayXC im Vordergrund auf Port 8001
- Extrahiert `PUBLIC_HOST` aus `HOST` Environment-Variable
- Setzt `VAVOO_PUBLIC_HOST` und `VAVOO_PORT` automatisch

**Wichtig für Updates:**
- Bei Änderungen an Startup-Logik: `start.sh` anpassen
- Reihenfolge beibehalten: Vavoo zuerst (background), dann MacReplayXC (foreground)

---

### 2. **vavoo/vavoo2.py**
**Zweck:** Vavoo IPTV Proxy Server

**Änderungen:**

#### a) Environment Variables (Zeilen 1-10)
```python
PORT = int(os.getenv("VAVOO_PORT", "4323"))
PUBLIC_HOST = os.getenv("VAVOO_PUBLIC_HOST", "")
PLAYLIST_DIR = "/app/data/vavoo_playlists"
```
- Liest Port und Host aus Environment-Variablen
- Fallback auf Defaults wenn nicht gesetzt

#### b) public_port() Funktion (Zeile ~920)
```python
def public_port():
    return PORT
```
- Gibt konfigurierten Port zurück (aus ENV)

#### c) Static Route (nach /logout, Zeile ~1798)
```python
@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files (CSS, JS, images) for MacReplayXC theme integration."""
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, filename)
```
- Serviert statische Dateien (CSS für Theme)

#### d) CSS Link Injection (Zeile ~2717)
```html
</style>
<link rel="stylesheet" href="/static/macreplay-theme.css">
</head>
```
- Lädt MacReplayXC Theme CSS

**Wichtig für Updates:**
- Bei Vavoo-Updates: Environment-Variablen beibehalten
- Static Route nicht entfernen (für Theme)
- CSS Link im HTML-Head beibehalten

---

### 3. **vavoo/static/macreplay-theme.css** (NEU)
**Zweck:** Tabler Dark Theme für Vavoo

**Änderungen:**
- Komplettes CSS-Override für Vavoo UI
- Nutzt Tabler Dark Theme Farben
- Passt Buttons, Forms, Tables, etc. an MacReplayXC an

**Wichtig für Updates:**
- Bei Theme-Änderungen in MacReplayXC: CSS anpassen
- Farben in `:root` CSS-Variablen definiert

---

### 4. **app-docker.py**
**Zweck:** MacReplayXC Hauptanwendung

**Änderungen:**

#### a) Vavoo Route (Zeile ~9467)
```python
@app.route("/vavoo_page")
@login_required
def vavoo_page():
    """Vavoo IPTV Proxy integration page."""
    return render_template("vavoo.html")
```
- Route für Vavoo iFrame-Integration
- Nutzt MacReplayXC Login

**Wichtig für Updates:**
- Route beibehalten für Navigation
- `@login_required` Decorator nicht entfernen

---

### 5. **templates/base.html**
**Zweck:** Basis-Template mit Navigation

**Änderungen:**

#### Navigation Link (Zeile ~100-130)
```html
<li class="nav-item">
    <a class="nav-link {% if request.path == '/vavoo_page' or request.path.startswith('/vavoo') %}active{% endif %}"
        href="/vavoo_page">
        <i class="ti ti-broadcast me-1"></i>
        Vavoo
    </a>
</li>
```
- Fügt Vavoo-Tab zur Navigation hinzu
- Active-State für Vavoo-Seiten

**Wichtig für Updates:**
- Bei Navigation-Änderungen: Vavoo-Link beibehalten
- Icon: `ti-broadcast`

---

### 6. **templates/vavoo.html** (NEU)
**Zweck:** iFrame-Integration für Vavoo

**Änderungen:**
```html
{% extends "base.html" %}
{% block title %}Vavoo IPTV Proxy - MacReplayXC{% endblock %}
{% block content %}
<div class="page-header d-print-none">
    <div class="container-xl">
        <div class="row g-2 align-items-center">
            <div class="col">
                <h2 class="page-title">
                    <i class="ti ti-broadcast me-2"></i>Vavoo IPTV Proxy
                </h2>
                <div class="text-muted mt-1">Multi-Region IPTV Streaming</div>
            </div>
        </div>
    </div>
</div>
<div class="page-body">
    <div class="container-xl">
        <div class="card">
            <div class="card-body p-0">
                <iframe src="http://localhost:4323" 
                        style="width: 100%; height: 85vh; border: none;"
                        title="Vavoo IPTV Proxy">
                </iframe>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```
- Eingebettetes iFrame für Vavoo
- Nutzt MacReplayXC Layout

**Wichtig für Updates:**
- iFrame src bleibt `localhost:4323` (Container-intern)
- Height: `85vh` für optimale Darstellung

---

### 7. **Dockerfile**
**Zweck:** Docker Image Build

**Änderungen:**

#### a) Vavoo Files kopieren
```dockerfile
# Copy Vavoo files
COPY vavoo/ vavoo/
```

#### b) Startup Script
```dockerfile
# Copy startup script
COPY start.sh .
RUN chmod +x start.sh
```

#### c) Vavoo Port freigeben
```dockerfile
# Expose the application ports
EXPOSE 8001
EXPOSE 4323
```

#### d) CMD angepasst
```dockerfile
CMD ["./start.sh"]
```

**Wichtig für Updates:**
- Bei Dockerfile-Änderungen: Vavoo-Zeilen beibehalten
- Port 4323 nicht entfernen

---

### 8. **docker-compose.yml**
**Zweck:** Docker Compose Konfiguration

**Änderungen:**

#### a) Vavoo Port Mapping
```yaml
ports:
  - "8001:8001"
  - "4323:4323"  # Vavoo port
```

#### b) HOST Environment Variable
```yaml
environment:
  - HOST=0.0.0.0:8001  # Change to your public URL if needed
```
- Wird von `start.sh` für Vavoo genutzt

**Wichtig für Updates:**
- Port 4323 Mapping beibehalten
- HOST-Variable wird für beide Apps genutzt

---

### 9. **templates/wiki.html**
**Zweck:** Feature-Dokumentation

**Änderungen:**
- Erweiterte Vavoo-Sektion mit Setup-Anleitung
- Environment Variables erklärt
- Port-Konfiguration dokumentiert
- Playlist-URLs und Stream-URLs erklärt
- Vorteile der Integration aufgelistet

**Wichtig für Updates:**
- Bei Vavoo-Änderungen: Wiki aktualisieren
- Setup-Anleitung auf dem neuesten Stand halten

---

## Zusammenfassung der Integration

### Architektur
```
┌─────────────────────────────────────┐
│   Docker Container (MacReplayXC)    │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ MacReplayXC  │  │   Vavoo     │ │
│  │  Port 8001   │  │  Port 4323  │ │
│  └──────────────┘  └─────────────┘ │
│         │                  │        │
│         └──────────────────┘        │
│         start.sh (beide starten)    │
└─────────────────────────────────────┘
```

### Datenfluss
1. User → `http://your-domain.com:8001/vavoo_page`
2. MacReplayXC → Login-Check → `templates/vavoo.html`
3. iFrame lädt → `http://localhost:4323` (Container-intern)
4. Vavoo serviert UI mit MacReplayXC Theme

### Environment Variables
- `HOST`: Öffentliche URL (z.B. `http://your-domain.com:8001`)
- `VAVOO_PUBLIC_HOST`: Automatisch aus HOST extrahiert
- `VAVOO_PORT`: Fest auf 4323

### Ports
- **8001**: MacReplayXC Web-Interface
- **4323**: Vavoo IPTV Proxy

---

## Update-Checkliste

Bei Updates von MacReplayXC oder Vavoo:

### MacReplayXC Updates
- [ ] `start.sh` prüfen (Startup-Logik)
- [ ] `app-docker.py` → `/vavoo_page` Route beibehalten
- [ ] `templates/base.html` → Vavoo Navigation-Link beibehalten
- [ ] `templates/vavoo.html` → iFrame beibehalten
- [ ] `Dockerfile` → Vavoo-Zeilen beibehalten
- [ ] `docker-compose.yml` → Port 4323 beibehalten

### Vavoo Updates
- [ ] `vavoo/vavoo2.py` → Environment-Variablen (Zeilen 1-10) beibehalten
- [ ] `vavoo/vavoo2.py` → `public_port()` Funktion beibehalten
- [ ] `vavoo/vavoo2.py` → Static Route beibehalten
- [ ] `vavoo/vavoo2.py` → CSS Link im HTML beibehalten
- [ ] `vavoo/static/macreplay-theme.css` → Theme beibehalten

### Theme Updates
- [ ] `vavoo/static/macreplay-theme.css` → Farben an MacReplayXC anpassen
- [ ] CSS-Variablen in `:root` aktualisieren

---

## Bekannte Probleme & Lösungen

### Problem: "Die Server-IP-Adresse von vavoo wurde nicht gefunden"
**Ursache:** iFrame versucht externe URL statt Container-intern
**Lösung:** iFrame src auf `http://localhost:4323` setzen (Container-intern)

### Problem: "localhost hat die Verbindung abgelehnt"
**Ursache:** Vavoo nicht gestartet oder Port nicht freigegeben
**Lösung:** 
- `docker logs MacReplayXC` prüfen
- Port 4323 in docker-compose.yml freigeben
- `start.sh` prüfen (Vavoo-Start)

### Problem: Vavoo-Streams nutzen falsche URL
**Ursache:** PUBLIC_HOST nicht korrekt gesetzt
**Lösung:** 
- `HOST` in docker-compose.yml auf öffentliche URL setzen
- Format: `http://your-domain.com:8001`
- `start.sh` extrahiert automatisch Hostname

### Problem: Theme passt nicht
**Ursache:** CSS nicht geladen oder falsche Farben
**Lösung:**
- Static Route in vavoo2.py prüfen
- CSS Link im HTML-Head prüfen
- `vavoo/static/macreplay-theme.css` anpassen

---

## Testing

### Manuelle Tests
1. **Container starten:**
   ```bash
   docker-compose up -d
   docker logs -f MacReplayXC
   ```

2. **Vavoo-Start prüfen:**
   - Log sollte zeigen: "✅ Vavoo started (PID: X)"
   - Log sollte zeigen: "🚀 Starting Waitress server (production-ready)..."

3. **Web-Interface testen:**
   - `http://your-domain.com:8001/vavoo_page` öffnen
   - Login sollte funktionieren
   - iFrame sollte Vavoo UI zeigen
   - Theme sollte dunkel sein (Tabler Dark)

4. **Playlists testen:**
   - `http://your-domain.com:4323/playlist/DE.m3u` öffnen
   - Sollte M3U-Playlist zurückgeben
   - URLs sollten öffentliche Domain enthalten

5. **Streams testen:**
   - Playlist in VLC öffnen
   - Channel abspielen
   - Stream sollte funktionieren

---

## Kontakt & Support

Bei Problemen oder Fragen:
- GitHub Issues: https://github.com/un1x-dev/MacReplayXC/issues
- Wiki: http://your-domain.com:8001/wiki

---

**Erstellt:** 2026-02-06  
**Version:** MacReplayXC v3.0.0 + Vavoo Integration  
**Autor:** Un1x & StiniStinson
