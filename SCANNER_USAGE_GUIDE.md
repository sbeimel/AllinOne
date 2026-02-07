# 📖 MAC Scanner - Usage Guide

## 🎯 Overview

The MAC Scanner is a powerful tool for discovering valid MAC addresses on IPTV/Stalker portals. It now uses **SQLite database storage** for fast queries and scalability.

---

## 🚀 Quick Start

### 1. Access Scanner
Navigate to: **http://your-server:8001/scanner**

### 2. Start a Scan
1. Enter **Portal URL** (e.g., `http://portal.com/c`)
2. Choose **Mode**:
   - **Random MACs**: Generate random MACs with prefix
   - **MAC List**: Test specific MACs from list
3. Set **Speed** (threads): 1-50 (default: 10)
4. Set **Timeout**: 5-30 seconds (default: 10)
5. Optional: Add **Proxies** (one per line)
6. Click **Start Scan**

### 3. Monitor Progress
- View **Active Scans** section
- See real-time stats: Tested, Hits, Errors
- Check current MAC and proxy being tested
- Pause/Resume or Stop scan anytime

### 4. View Results
- **Found MACs** table shows all hits
- Use **filters** to narrow results
- **Group** by portal or DE status
- **Export** results as JSON
- **Create Portal** from any hit with one click

---

## 🔍 Filtering & Grouping

### Filter Options

#### 1. Filter by Portal
Select a specific portal from dropdown to see only hits from that portal.

#### 2. Min. Channels
Set minimum channel count (e.g., 100) to filter out low-quality hits.

#### 3. DE Only
Show only hits with German (DE) channels.

### Grouping Options

#### 1. No Grouping
Shows all hits in chronological order (newest first).

#### 2. By Portal
Groups hits by portal URL, showing hit count per portal.

#### 3. By DE Status
Groups hits into:
- 🇩🇪 **German Channels** (has DE genres)
- **Other Channels** (no DE genres)

---

## 📊 Statistics Dashboard

The stats dashboard shows:
- **Total Hits**: Total number of found MACs
- **Unique Portals**: Number of different portals
- **DE Hits**: Number of hits with German channels
- **Avg. Channels**: Average channel count per hit

---

## 🎯 Scanner Modes

### Random Mode
- Generates random MACs with specified prefix
- Default prefix: `00:1A:79:`
- Continues until stopped
- Best for discovering new MACs

### List Mode
- Tests specific MACs from your list
- One MAC per line
- Shows progress (X / Y MACs)
- Stops when list is exhausted
- Best for validating known MACs

---

## 🌐 Proxy Support

### Why Use Proxies?
- Avoid IP bans from portals
- Distribute load across multiple IPs
- Increase scan speed with parallel requests

### Proxy Formats
```
# HTTP Proxy
http://proxy.com:8080
proxy.com:8080

# SOCKS5 Proxy
socks5://proxy.com:1080

# With Authentication
http://user:pass@proxy.com:8080
socks5://user:pass@proxy.com:1080
```

### Proxy Management
1. **Add Proxies**: Paste list in scan form
2. **Fetch Proxies**: Auto-fetch from sources
3. **Test Proxies**: Verify connectivity
4. **Auto-Detect**: Detect proxy type (HTTP/SOCKS4/SOCKS5)
5. **Remove Failed**: Clean up dead proxies

### Smart Proxy Rotation
The scanner uses intelligent proxy rotation:
- **Performance Tracking**: Monitors speed and success rate
- **Automatic Failover**: Switches to better proxies
- **Blocked Detection**: Avoids proxies blocked by portal
- **Rehabilitation**: Retries "dead" proxies after cooldown

---

## ⚙️ Advanced Settings

### Scanner Settings
Access via Settings API or config file:

```json
{
  "speed": 10,                              // Threads (1-50)
  "timeout": 10,                            // Request timeout (seconds)
  "mac_prefix": "00:1A:79:",                // MAC prefix for random mode
  "auto_save": true,                        // Auto-save hits to DB
  "max_proxy_errors": 10,                   // Max errors before proxy marked dead
  "proxy_test_threads": 50,                 // Threads for proxy testing
  "unlimited_mac_retries": true,            // Retry MACs indefinitely
  "max_mac_retries": 3,                     // Max retries if unlimited=false
  "max_proxy_attempts_per_mac": 10,         // Max proxies to try per MAC
  "proxy_rotation_percentage": 80,          // Top % of proxies to use
  "proxy_connect_timeout": 2,               // Proxy connection timeout
  "require_channels_for_valid_hit": true,   // Require channels for hit
  "min_channels_for_valid_hit": 1,          // Min channels required
  "aggressive_phase1_retry": true           // Aggressive retry on timeout
}
```

### Retry Logic
The scanner has sophisticated retry logic:
1. **Soft Fail** (timeout, proxy error): Retry with different proxy
2. **Hard Fail** (invalid MAC): Don't retry
3. **Retry Queue**: Failed MACs queued for retry
4. **Unlimited Retries**: Keep trying until success or stop
5. **Max Attempts**: Limit retries per MAC (if unlimited=false)

---

## 🎯 Creating Portals from Hits

### One-Click Portal Creation
1. Find a good hit in **Found MACs** table
2. Click **Create Portal** button
3. Portal is automatically created with:
   - Portal name (domain + channels + 🇩🇪 if DE)
   - Portal URL
   - MAC address with expiry
   - Auto-refreshed channels in DB

### Portal Naming
Portals are named automatically:
```
portal.com 🇩🇪 (150ch)
```
- Domain from portal URL
- 🇩🇪 flag if German channels found
- Channel count in parentheses

### Auto-Refresh
When creating a portal from scanner hit:
1. ✅ Portal is created in config
2. ✅ Channels are fetched from portal
3. ✅ Channels are saved to `channels.db`
4. ✅ Portal is ready to use immediately

---

## 💾 Data Storage

### Hybrid Storage Architecture

#### JSON File (`scanner_config.json`):
```json
{
  "settings": { ... },
  "proxies": [ ... ],
  "proxy_sources": [ ... ]
}
```

#### SQLite Database (`scans.db`):
```
found_macs table:
- All found MACs with metadata
- Indexed for fast queries

genres table:
- Channel genres per MAC
- DE detection
```

### Benefits
- ✅ **Fast Queries**: 5-200x faster than JSON
- ✅ **Scalable**: Handles millions of hits
- ✅ **Persistent**: Survives restarts
- ✅ **Filterable**: SQL-based filtering
- ✅ **Statistics**: Aggregated in DB

---

## 📤 Export & Backup

### Export Found MACs
Click **Export** button to download all hits as JSON:
```json
[
  {
    "mac": "00:1A:79:XX:XX:XX",
    "portal": "http://portal.com/c",
    "expiry": "2025-12-31",
    "channels": 150,
    "has_de": true,
    "genres": ["DE: Sport", "DE: Movies"],
    "found_at": "2025-02-07T12:00:00"
  }
]
```

### Backup Database
```bash
# Backup scans.db
cp /app/data/scans.db /backup/scans_$(date +%Y%m%d).db

# Backup config
cp /app/data/scanner_config.json /backup/scanner_config_$(date +%Y%m%d).json
```

### Restore Database
```bash
# Restore scans.db
cp /backup/scans_20250207.db /app/data/scans.db

# Restart container
docker restart macreplay
```

---

## 🔧 Troubleshooting

### No Hits Found
1. ✅ Check portal URL is correct
2. ✅ Try different MAC prefix
3. ✅ Increase timeout (slow portal)
4. ✅ Use proxies (IP banned?)
5. ✅ Check portal is online

### Scan Too Slow
1. ✅ Increase speed (threads)
2. ✅ Use more proxies
3. ✅ Reduce timeout
4. ✅ Use faster proxies

### Proxies Not Working
1. ✅ Test proxies first
2. ✅ Use auto-detect for proxy type
3. ✅ Remove failed proxies
4. ✅ Fetch fresh proxies from sources

### Database Issues
1. ✅ Check `/app/data/scans.db` exists
2. ✅ Check file permissions
3. ✅ Run test script: `python test_scanner_db.py`
4. ✅ Check logs for errors

### High Memory Usage
1. ✅ Clear old hits: Click **Clear All**
2. ✅ Reduce concurrent scans
3. ✅ Reduce speed (threads)
4. ✅ Stop inactive scans

---

## 📊 Performance Tips

### Optimal Settings

#### For Few Proxies (0-10):
```
Speed: 5-10 threads
Timeout: 10 seconds
Proxy Rotation: 80%
```

#### For Many Proxies (10-100):
```
Speed: 20-30 threads
Timeout: 5 seconds
Proxy Rotation: 50%
```

#### For Massive Proxies (100+):
```
Speed: 50 threads
Timeout: 3 seconds
Proxy Rotation: 30%
```

### Speed vs Quality
- **Low Speed** (5-10): Better quality, fewer errors
- **Medium Speed** (10-20): Balanced
- **High Speed** (20-50): Faster, more errors

### Timeout Tuning
- **Short** (3-5s): Fast portals, good proxies
- **Medium** (5-10s): Most portals
- **Long** (10-30s): Slow portals, bad proxies

---

## 🎯 Best Practices

### 1. Start Small
- Test with 5-10 threads first
- Increase speed gradually
- Monitor error rate

### 2. Use Proxies
- Always use proxies for large scans
- Test proxies before scanning
- Remove failed proxies regularly

### 3. Filter Results
- Set min channels (e.g., 50)
- Focus on DE hits if needed
- Group by portal to find best sources

### 4. Create Portals
- Create portals from best hits
- Check channel count and DE status
- Test portal before adding to production

### 5. Maintain Database
- Export hits regularly
- Clear old/invalid hits
- Backup database weekly

---

## 🔌 API Reference

### Get Found MACs
```bash
# Get all hits
curl http://localhost:8001/scanner/found-macs

# Filter by portal
curl "http://localhost:8001/scanner/found-macs?portal=http://portal.com/c"

# Filter by min channels
curl "http://localhost:8001/scanner/found-macs?min_channels=100"

# Filter DE only
curl "http://localhost:8001/scanner/found-macs?de_only=true"

# Combined filters
curl "http://localhost:8001/scanner/found-macs?portal=http://portal.com/c&min_channels=50&de_only=true&limit=100"
```

### Get Statistics
```bash
curl http://localhost:8001/scanner/found-macs/stats
```

### Get Portals List
```bash
curl http://localhost:8001/scanner/portals-list
```

### Clear All Hits
```bash
curl -X DELETE http://localhost:8001/scanner/found-macs
```

### Export Hits
```bash
curl http://localhost:8001/scanner/export-found-macs > scanner_hits.json
```

---

## 📝 Example Workflow

### Scenario: Find German IPTV Portals

1. **Start Scan**
   - Portal: `http://target-portal.com/c`
   - Mode: Random
   - Speed: 20 threads
   - MAC Prefix: `00:1A:79:`
   - Proxies: 50 proxies from list

2. **Monitor Progress**
   - Wait for 100+ hits
   - Check hit rate (should be >1%)
   - Monitor proxy stats

3. **Filter Results**
   - Set "DE Only" filter
   - Set "Min Channels" to 100
   - Group by portal

4. **Select Best Hits**
   - Sort by channel count
   - Check expiry dates
   - Verify DE genres

5. **Create Portals**
   - Click "Create Portal" on best hits
   - Wait for auto-refresh
   - Test portals in player

6. **Export & Backup**
   - Export all hits as JSON
   - Backup database
   - Clear old hits

---

## 🎉 Summary

The MAC Scanner with SQLite database provides:
- ✅ **Fast Performance**: 5-200x faster queries
- ✅ **Scalability**: Millions of hits supported
- ✅ **Advanced Filtering**: Portal, channels, DE status
- ✅ **Smart Grouping**: By portal or DE status
- ✅ **Statistics**: Real-time aggregated stats
- ✅ **One-Click Portals**: Create portals from hits
- ✅ **Proxy Support**: Smart rotation and failover
- ✅ **Persistent Storage**: Survives restarts

**Happy Scanning! 🚀**
