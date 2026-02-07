# Scanner Stealth Mode - Missing Feature

## What's Missing

### Stealth Settings (for avoiding detection)

**From MacAttack.pyw/mcbash:**
1. **Request Delay** - Pause between requests (e.g., 0.5-2s)
2. **User-Agent Rotation** - Random User-Agents per request
3. **Randomized MAC Generation** - More random patterns
4. **Connection Throttling** - Limit requests per second
5. **Proxy Rotation Strategy** - Force rotation every N requests

## Why It's Important

Portals can detect and block scanners by:
- Too many requests from same IP
- Predictable MAC patterns (00:1A:79:00:00:01, 00:1A:79:00:00:02, ...)
- Same User-Agent repeatedly
- Too fast request rate

## Recommended Implementation

### UI Addition (Settings Tab)

```
┌─────────────────────────────────────────────────────┐
│ 🥷 Stealth Settings                                 │
├─────────────────────────────────────────────────────┤
│ ☐ Enable Stealth Mode                              │
│                                                     │
│ Request Delay: [1.0] seconds (0.5-5s)              │
│ User-Agent Rotation: ☑ Enabled                     │
│ Proxy Rotation: Every [10] requests                │
│ MAC Randomization: ☑ Enhanced                      │
│                                                     │
│ [Apply Stealth Settings]                           │
└─────────────────────────────────────────────────────┘
```

### Backend Settings

```python
DEFAULT_SCANNER_SETTINGS = {
    # ... existing settings ...
    "stealth_mode": False,
    "request_delay": 1.0,  # seconds
    "user_agent_rotation": True,
    "force_proxy_rotation_every": 10,  # requests
    "enhanced_mac_randomization": True
}
```

### Implementation

```python
# In scanner loop
if settings.get("stealth_mode"):
    # Random delay
    await asyncio.sleep(random.uniform(0.5, settings["request_delay"]))
    
    # Rotate User-Agent
    if settings["user_agent_rotation"]:
        headers["User-Agent"] = random.choice(USER_AGENTS)
    
    # Force proxy rotation
    if request_count % settings["force_proxy_rotation_every"] == 0:
        current_proxy = get_next_proxy()
```

## Preset: Stealth Mode

Add 5th preset button:

**🥷 Stealth Mode**
- Speed: 5 threads / 25 tasks (slow)
- Request Delay: 1.5s
- User-Agent Rotation: ON
- Proxy Rotation: Every 5 requests
- Enhanced MAC Randomization: ON
- Timeout: 20s (patient)

## Priority

**Medium-High** - Important for:
- Avoiding IP bans
- Scanning sensitive portals
- Long-running scans
- Professional use

## Comparison

| Scanner | Stealth Mode |
|---------|--------------|
| mcbash | ✅ Has delay option |
| MacAttack.pyw | ⚠️ Basic (manual delay) |
| MacAttackWeb | ❌ No stealth |
| **Your Scanner** | ❌ **Missing** |
