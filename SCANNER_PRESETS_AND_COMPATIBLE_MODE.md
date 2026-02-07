# Scanner Presets & Compatible Mode Added

## Summary

Added recommended settings presets and MacAttack.pyw Compatible Mode to both scanner UIs.

## What Was Added

### 1. Recommended Settings Presets

Both `scanner.html` and `scanner-new.html` now have a preset card at the top of the Settings tab with 4 quick-apply buttons:

#### **Max Accuracy** (Slower, fewer false negatives)
- **Sync Scanner**: Speed 12, Timeout 15s, Max Errors 10, Rotation 70%, Unlimited Retries ON
- **Async Scanner**: Speed 75, Timeout 15s, Max Errors 10, Rotation 70%, Unlimited Retries ON
- **Use case**: When you want maximum accuracy and don't mind slower scanning

#### **Balanced** (Good balance)
- **Sync Scanner**: Speed 18, Timeout 12s, Max Errors 6, Rotation 50%, Max Attempts 15
- **Async Scanner**: Speed 150, Timeout 12s, Max Errors 6, Rotation 50%, Max Attempts 15
- **Use case**: Default recommended settings for most users

#### **Fast Scan** (Faster, more false negatives)
- **Sync Scanner**: Speed 25, Timeout 8s, Max Errors 4, Rotation 30%, Max Attempts 5
- **Async Scanner**: Speed 350, Timeout 8s, Max Errors 4, Rotation 30%, Max Attempts 5
- **Use case**: When you want quick results and can tolerate some missed MACs

#### **No Proxy** (Direct connection)
- **Sync Scanner**: Speed 8, Timeout 20s, Use Proxies OFF
- **Async Scanner**: Speed 35, Timeout 20s, Use Proxies OFF
- **Use case**: When scanning without proxies (slower portals need longer timeout)

### 2. MacAttack.pyw Compatible Mode

Added checkbox in Settings tab:

```
☐ MacAttack.pyw Compatible Mode

ON:  Like MacAttack.pyw - no token = MAC invalid (no proxy retry)
OFF: Intelligent mode - analyze response to decide retry vs invalid
```

**What it does:**
- **ON**: Behaves exactly like original MacAttack.pyw - if no token received, MAC is immediately marked as invalid
- **OFF**: Intelligent mode - analyzes the response to determine if it's a proxy issue (retry) or truly invalid MAC

**Backend support:**
- Setting is saved as `macattack_compatible_mode` in scanner settings
- Backend already supports this setting (from original MacAttackWeb-NEW integration)

## UI Layout

### Settings Tab Structure

```
┌─────────────────────────────────────────────────────┐
│ 💡 Recommended Settings                             │
├─────────────────────────────────────────────────────┤
│ [Info box with all 4 preset descriptions]          │
│                                                     │
│ [Apply Max Accuracy] [Apply Balanced]              │
│ [Apply Fast Scan]    [Apply No Proxy]              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Scanner Settings                                    │
├─────────────────────────────────────────────────────┤
│ Speed: [__]  Timeout: [__]  MAC Prefix: [______]   │
│ Min Channels: [__]  Max Errors: [__]  Rotation: [__]│
│                                                     │
│ ☑ Use Proxies                                      │
│ ☑ Auto-save Found MACs                             │
│ ☑ Require Channels for Valid Hit                   │
│ ☐ Unlimited Proxy Retries                          │
│                                                     │
│ ☐ MacAttack.pyw Compatible Mode                    │
│   ON: Like MacAttack.pyw - no token = invalid      │
│   OFF: Intelligent mode - analyze response         │
│                                                     │
│ [Save Settings] [Reload Settings]                  │
└─────────────────────────────────────────────────────┘
```

## JavaScript Functions

### Preset Functions

```javascript
function applyMaxAccuracy()  // Apply max accuracy preset
function applyBalanced()     // Apply balanced preset
function applyFastScan()     // Apply fast scan preset
function applyNoProxy()      // Apply no proxy preset
```

**Behavior:**
- Sets all relevant settings to preset values
- Shows alert: "✅ Preset applied! Click 'Save Settings' to save."
- User must click "Save Settings" to persist changes

### Settings Functions (Updated)

```javascript
async function loadSettings()  // Now loads compatible_mode
async function saveSettings()  // Now saves compatible_mode
```

## Files Modified

1. `templates/scanner.html` - Added presets card, compatible mode checkbox, preset functions
2. `templates/scanner-new.html` - Added presets card, compatible mode checkbox, preset functions (async values)

## Differences Between Sync and Async Presets

| Preset | Sync Speed | Async Speed | Reason |
|--------|-----------|-------------|---------|
| Max Accuracy | 12 threads | 75 tasks | Async can handle more concurrent tasks |
| Balanced | 18 threads | 150 tasks | Async is ~8x more efficient |
| Fast Scan | 25 threads | 350 tasks | Async can go much higher |
| No Proxy | 8 threads | 35 tasks | Async still faster without proxies |

## Backend Support

The backend already supports all these settings:

```python
# scanner.py & scanner_async.py
DEFAULT_SCANNER_SETTINGS = {
    "speed": 10,
    "timeout": 10,
    "mac_prefix": "00:1A:79:",
    "use_proxies": False,
    "auto_save": True,
    "require_channels_for_valid_hit": True,
    "min_channels_for_valid_hit": 1,
    "max_proxy_errors": 10,
    "unlimited_mac_retries": True,
    "proxy_rotation_percentage": 80,
    "macattack_compatible_mode": False  # ← Already supported!
}
```

## User Experience

### Before
- User had to manually configure all settings
- No guidance on optimal values
- No quick way to switch between accuracy/speed profiles

### After
- ✅ 4 preset buttons for instant configuration
- ✅ Clear descriptions of each preset
- ✅ Compatible mode for MacAttack.pyw users
- ✅ One-click apply, then save

## Testing Checklist

- [ ] Sync scanner: All 4 preset buttons work
- [ ] Async scanner: All 4 preset buttons work
- [ ] Compatible mode checkbox loads correctly
- [ ] Compatible mode checkbox saves correctly
- [ ] Preset values are appropriate for each scanner type
- [ ] Alert messages appear after applying presets
- [ ] Settings persist after save

## Notes

- Presets only **apply** settings, they don't **save** them
- User must click "Save Settings" to persist
- This prevents accidental changes
- Compatible mode is OFF by default (intelligent mode)
