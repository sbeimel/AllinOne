# Änderungen für MacReplay-weiterentwickelt

## Übersicht
Diese Änderungen aus dem AllinOne-Projekt auf MacReplay-weiterentwickelt anwenden.

---

## 1. Layout-Verbesserungen

### templates/wiki.html
**Zeile ~15:** Container breiter machen
```html
<!-- VORHER -->
<div class="container-xl">

<!-- NACHHER -->
<div class="container-fluid" style="max-width: 1400px;">
```

**Tabellen:** Header und feste Spaltenbreiten hinzufügen
```html
<table class="table table-sm table-bordered">
    <thead>
        <tr>
            <th style="width: 25%;">Einstellung</th>
            <th style="width: 40%;">Beschreibung</th>
            <th style="width: 35%;">Werte / Empfehlung</th>
        </tr>
    </thead>
    <tbody>
        <!-- Tabelleninhalt -->
    </tbody>
</table>
```

---

### templates/portals.html
**Zeile ~180:** Container breiter machen
```html
<!-- VORHER -->
<div class="container-xl">

<!-- NACHHER -->
<div class="container-fluid" style="max-width: 1600px;">
```

**Zeile ~190:** Portal-Cards von 3 auf 4 Spalten
```html
<!-- VORHER -->
<div class="col-md-6 col-xl-4">

<!-- NACHHER -->
<div class="col-md-6 col-xl-3">
```

**Zeile ~240-280:** Buttons größer machen (btn-sm entfernen)
```html
<!-- VORHER -->
<button class="btn btn-outline-success btn-sm w-100">

<!-- NACHHER -->
<button class="btn btn-outline-success w-100">
```

---

## 2. MAC-Regionen-Erkennung (DE-Check)

### templates/portals.html

**Spaltenüberschrift ändern (Zeile ~545):**
```html
<!-- VORHER -->
<th>Regions</th>

<!-- NACHHER -->
<th>DE ?</th>
```

**JavaScript-Code anpassen (Zeile ~1171):**
```javascript
// Update each row with DE check (green checkmark if DE content found)
for (const [mac, regions] of Object.entries(macRegions)) {
    const flagCell = document.getElementById(`flags_${mac.replace(/:/g, '_')}`);
    if (flagCell && regions && regions.length > 0) {
        // Nur prüfen ob DE vorhanden ist
        const hasDE = regions.some(region => {
            const r = String(region).toLowerCase().trim();
            return r === 'de' || r === 'ger' || r === 'german' || r === 'deutsch' || r === 'germany' || r === 'allemagne';
        });
        
        // Grüner Haken wenn DE gefunden, sonst leer
        if (hasDE) {
            flagCell.innerHTML = '<span class="text-success">✓</span>';
        } else {
            flagCell.innerHTML = '';
        }
    } else if (flagCell) {
        flagCell.innerHTML = '';
    }
}
```

---

### templates/wiki.html

**MAC-Regionen-Erkennung Sektion anpassen:**
```html
<div class="mb-4">
    <h5><span class="badge bg-primary me-2">5</span>MAC-Regionen-Erkennung</h5>
    <p><strong>Automatische DE-Erkennung basierend auf Genre-Namen:</strong></p>
    <div class="row g-2">
        <div class="col-md-12">
            <div class="card">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <span style="font-size: 3em;">✓</span>
                        </div>
                        <div class="col">
                            <h6 class="mb-2">Deutsche Inhalte erkannt</h6>
                            <p class="text-muted mb-0">
                                Wenn Genre-Namen Keywords wie <strong>DE</strong>, <strong>GER</strong>, <strong>GERMAN</strong>, 
                                <strong>DEUTSCH</strong>, <strong>GERMANY</strong> oder <strong>ALLEMAGNE</strong> enthalten, 
                                wird ein grüner Haken in der Spalte "DE ?" angezeigt.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="alert alert-info mt-2 mb-0">
        <strong>Anzeige:</strong> Portals → Edit Portal → Current MACs → Spalte "DE ?"<br>
        <strong>Hinweis:</strong> AT und CH werden nicht mehr separat angezeigt - nur DE-Erkennung
    </div>
</div>
```

---

## 3. Vavoo Integration (falls gewünscht)

### Dateien kopieren:
- `vavoo/` (kompletter Ordner)
- `start.sh`
- `templates/vavoo.html`
- `docs/vavoo/` (Dokumentation)

### Dateien anpassen:
- `Dockerfile` - Vavoo-Zeilen hinzufügen
- `docker-compose.yml` - Port 4323 hinzufügen
- `app-docker.py` - `/vavoo_page` Route hinzufügen
- `templates/base.html` - Vavoo Navigation-Link hinzufügen

**Details siehe:** `docs/vavoo/INTEGRATION_CHANGELOG.md`

---

## 4. Zusammenfassung der Vorteile

### Layout:
✅ Mehr Bildschirmbreite genutzt (1400px Wiki, 1600px Portals)
✅ Weniger leerer Platz links und rechts
✅ Buttons größer und besser sichtbar
✅ Portal-Cards besser verteilt (4 statt 3 pro Reihe)
✅ Tabellen mit Header und festen Spaltenbreiten

### MAC-Regionen:
✅ Einfache DE-Erkennung mit grünem Haken ✓
✅ Keine unnötigen Flaggen mehr
✅ Klare Spaltenüberschrift "DE ?"

### Vavoo (optional):
✅ Single Container Solution
✅ Tabler Dark Theme
✅ Einheitliches Login
✅ Automatischer Start

---

## Anwendung

1. **Backup erstellen:**
   ```bash
   cd ../MacReplay-weiterentwickelt
   git stash  # oder git commit
   ```

2. **Änderungen anwenden:**
   - Dateien manuell anpassen (siehe oben)
   - Oder Dateien aus AllinOne kopieren

3. **Testen:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Verifizieren:**
   - Wiki-Seite: Breiteres Layout, saubere Tabellen
   - Portals-Seite: Größere Buttons, 4 Spalten, "DE ?" Spalte
   - Funktionalität testen

---

**Erstellt:** 2026-02-06  
**Projekt:** AllinOne → MacReplay-weiterentwickelt  
**Status:** Ready to apply
