# Scanner Feature Comparison

## MacAttackWeb-NEW (Original) vs. Integrierte Version

### ✅ Übernommene Features:

| Feature | MacAttackWeb-NEW | Integriert | Status |
|---------|------------------|------------|--------|
| **Core Scanning** |
| Multi-threaded Scanning | ✅ | ✅ | ✅ |
| Random MAC Generation | ✅ | ✅ | ✅ |
| MAC List Scanning | ✅ | ✅ | ✅ |
| ProxyScorer (Smart Rotation) | ✅ | ✅ | ✅ |
| Hit Detection | ✅ | ✅ | ✅ |
| DE-Genre Detection | ✅ | ✅ | ✅ |
| Real-time Status | ✅ | ✅ | ✅ |
| Pause/Resume | ✅ | ✅ | ✅ |
| Stop Scan | ✅ | ✅ | ✅ |
| **Portal Creation** |
| Create Portal from Hit | ❌ | ✅ | ✅ BESSER! |
| Auto Channel Refresh | ❌ | ✅ | ✅ BESSER! |

### ❌ Fehlende Features (aus MacAttackWeb-NEW):

| Feature | Beschreibung | Wichtigkeit |
|---------|--------------|-------------|
| **Config Management** |
| Settings Persistence | Settings in JSON speichern | 🟡 Mittel |
| Auto-Save Found MACs | Hits automatisch speichern | 🟢 Wichtig |
| **Proxy Management** |
| Proxy Fetch | Proxies von URLs laden | 🟡 Mittel |
| Proxy Test | Proxies testen vor Scan | 🟢 Wichtig |
| Proxy Auto-Detect | Proxy-Typ erkennen | 🟡 Mittel |
| Proxy Sources Config | Proxy-Quellen konfigurieren | 🟡 Mittel |
| **Advanced Scanning** |
| Refresh Mode | Gefundene MACs re-scannen | 🟡 Mittel |
| Retry Queue | Failed MACs mit anderem Proxy | 🟢 Wichtig |
| Unlimited Retries | Retry bis alle Proxies durch | 🟡 Mittel |
| MAC Retry Settings | max_mac_retries, max_proxy_attempts | 🟡 Mittel |
| **Proxy Scoring Advanced** |
| Proxy Rehabilitation | Tote Proxies nach Zeit wieder nutzen | 🟡 Mittel |
| Proxy Stats | Active/Blocked/Dead Statistiken | 🟢 Wichtig |
| Portal-specific Blocking | Proxy nur für bestimmtes Portal blocken | 🟢 Wichtig |
| **Settings** |
| require_channels_for_valid_hit | Nur Hits mit Channels | 🟢 Wichtig |
| min_channels_for_valid_hit | Min. Channel-Anzahl | 🟢 Wichtig |
| macattack_compatible_mode | Kompatibilitätsmodus | 🟡 Mittel |
| aggressive_phase1_retry | Aggressive Retries | 🟡 Mittel |
| **Authentication** |
| Basic Auth | Login-Schutz | 🟡 Mittel |
| Setup Wizard | Ersteinrichtung | 🟡 Mittel |
| **Export** |
| Export Found MACs | JSON/TXT Export | 🟡 Mittel |
| **Player** |
| Built-in Player | MACs direkt testen | 🔴 Niedrig |

---

## 🔧 Was sollte noch hinzugefügt werden?

### 🟢 Wichtig (High Priority):

1. **Auto-Save Found MACs**
   - Hits in Config speichern
   - Überleben Container-Restart
   
2. **Retry Queue**
   - Failed MACs mit anderem Proxy retry
   - Wichtig für hohe Hit-Rate
   
3. **Proxy Stats**
   - Active/Blocked/Dead anzeigen
   - Besseres Proxy-Management
   
4. **Channel Validation**
   - `require_channels_for_valid_hit`
   - `min_channels_for_valid_hit`
   - Nur echte Hits speichern

5. **Proxy Test**
   - Proxies vor Scan testen
   - Tote Proxies aussortieren

### 🟡 Mittel (Medium Priority):

6. **Settings Persistence**
   - Scanner-Settings speichern
   - Nicht bei jedem Scan neu eingeben

7. **Refresh Mode**
   - Gefundene MACs re-scannen
   - Expiry aktualisieren

8. **Proxy Fetch**
   - Proxies automatisch laden
   - Von konfigurierbaren Quellen

9. **Proxy Rehabilitation**
   - Tote Proxies nach Zeit wieder nutzen
   - Mehr Proxies verfügbar

### 🔴 Niedrig (Low Priority):

10. **Export**
    - Found MACs exportieren
    - JSON/TXT Format

11. **Authentication**
    - Login-Schutz
    - Nicht kritisch (bereits in MacReplay)

---

## 📝 Empfehlung:

### Phase 1: Kritische Features (jetzt)
```
1. Auto-Save Found MACs
2. Retry Queue
3. Channel Validation Settings
4. Proxy Stats Display
```

### Phase 2: Wichtige Features (später)
```
5. Proxy Test
6. Settings Persistence
7. Refresh Mode
8. Proxy Fetch
```

### Phase 3: Nice-to-Have (optional)
```
9. Proxy Rehabilitation
10. Export
11. Advanced Settings UI
```

---

## 🚀 Soll ich die kritischen Features hinzufügen?

Die wichtigsten fehlenden Features sind:

1. **Auto-Save Found MACs** - Hits überleben Container-Restart
2. **Retry Queue** - Höhere Hit-Rate durch Proxy-Retry
3. **Channel Validation** - Nur echte Hits (mit Channels)
4. **Proxy Stats** - Besseres Proxy-Management

Diese 4 Features würden den Scanner auf das Niveau von MacAttackWeb-NEW bringen!

Soll ich diese implementieren?
