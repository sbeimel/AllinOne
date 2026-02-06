# Vavoo Integration Architecture

## Overview

Vavoo is integrated into MacReplayXC as a **Flask Blueprint**, allowing it to run on the same port (8001) while maintaining its own code structure and functionality.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     MacReplayXC (Port 8001)                  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ app-docker.py (Main Flask App)                         │ │
│  │                                                         │ │
│  │  Routes:                                               │ │
│  │  ├── /dashboard (MacReplay Dashboard)                 │ │
│  │  ├── /portals (Portal Management)                     │ │
│  │  ├── /editor (Channel Editor)                         │ │
│  │  ├── /vavoo_page (Vavoo Entry Point)                  │ │
│  │  │   └── Auto-login + Redirect to /vavoo/             │ │
│  │  └── ... (other MacReplay routes)                     │ │
│  │                                                         │ │
│  │  Blueprints:                                           │ │
│  │  └── vavoo_blueprint (registered at /vavoo)           │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│                              │ Blueprint Registration        │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ vavoo_blueprint.py (Blueprint Wrapper)                 │ │
│  │                                                         │ │
│  │  Responsibilities:                                     │ │
│  │  ├── Import vavoo2.py Flask app                       │ │
│  │  ├── Patch login_required decorator                   │ │
│  │  ├── Start background workers                         │ │
│  │  ├── Copy all routes from vavoo2.py                   │ │
│  │  └── Register as Blueprint at /vavoo                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                              │                               │
│                              │ Imports & Wraps               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ vavoo/vavoo2.py (Original Vavoo App)                  │ │
│  │                                                         │ │
│  │  Routes (now at /vavoo/*):                            │ │
│  │  ├── / → /vavoo/ (Vavoo Dashboard)                    │ │
│  │  ├── /login → /vavoo/login (Vavoo Login)              │ │
│  │  ├── /logout → /vavoo/logout (Vavoo Logout)           │ │
│  │  ├── /config → /vavoo/config (Vavoo Settings)         │ │
│  │  ├── /playlist.m3u → /vavoo/playlist.m3u              │ │
│  │  └── ... (all other Vavoo routes)                     │ │
│  │                                                         │ │
│  │  Background Workers:                                   │ │
│  │  ├── Refresh Worker (daemon)                          │ │
│  │  └── Resolution Workers (optional, if RES=true)       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. app-docker.py (Main Application)

**Role**: Main Flask application for MacReplayXC

**Key Features**:
- Hosts all MacReplay routes (dashboard, portals, editor, etc.)
- Registers Vavoo Blueprint at `/vavoo`
- Provides `/vavoo_page` entry point with auto-login

**Vavoo Integration Code**:
```python
# Blueprint Registration (line ~320)
from vavoo_blueprint import vavoo_blueprint
app.register_blueprint(vavoo_blueprint)

# Entry Point Route (line ~9464)
@app.route("/vavoo_page")
@authorise
def vavoo_page():
    # Auto-login to Vavoo
    if not session.get("logged_in"):
        session["logged_in"] = True
        session["user"] = "macreplay_user"
    return redirect("/vavoo/", code=302)
```

### 2. vavoo_blueprint.py (Blueprint Wrapper)

**Role**: Wraps Vavoo as a Flask Blueprint

**Key Responsibilities**:

1. **Import Vavoo App**
   ```python
   from vavoo2 import app as vavoo_app
   ```

2. **Patch Authentication**
   ```python
   def blueprint_login_required(f):
       @wraps(f)
       def decorated(*args, **kwargs):
           if not session.get("logged_in"):
               return redirect("/vavoo/login")  # Blueprint-aware
           return f(*args, **kwargs)
       return decorated
   
   vavoo2.login_required = blueprint_login_required
   ```

3. **Start Background Workers**
   ```python
   # Refresh Worker (always runs)
   refresh_process = multiprocessing.Process(
       target=refresh_worker,
       daemon=True
   )
   refresh_process.start()
   
   # Resolution Workers (if RES=true)
   if CONFIG.get("RES", False):
       for _ in range(RES_WORKERS):
           p = multiprocessing.Process(
               target=resolution_worker,
               args=(RES_QUEUE,),
               daemon=True
           )
           p.start()
   ```

4. **Copy Routes to Blueprint**
   ```python
   for rule in vavoo_app.url_map.iter_rules():
       vavoo_blueprint.add_url_rule(
           rule_str,
           endpoint=rule.endpoint,
           view_func=view_func,
           methods=rule.methods
       )
   ```

### 3. vavoo/vavoo2.py (Original Vavoo App)

**Role**: Standalone Vavoo IPTV Proxy application

**Key Features**:
- IPTV playlist generation
- Channel resolution and caching
- Multi-region support
- Background refresh workers
- Web UI for configuration

**Routes** (now prefixed with `/vavoo`):
- `/` → Dashboard
- `/login` → Login page
- `/logout` → Logout
- `/config` → Settings
- `/playlist.m3u` → M3U playlist
- `/vavoo` → Stream proxy
- `/connections` → Active connections

## Authentication Flow

### MacReplayXC Authentication
```python
@authorise  # MacReplay decorator
def some_route():
    # Checks MacReplay session
    pass
```

### Vavoo Authentication (Patched)
```python
@login_required  # Vavoo decorator (patched)
def vavoo_route():
    # Checks Vavoo session
    # Redirects to /vavoo/login if not logged in
    pass
```

### Auto-Login Integration
```python
# When user clicks "Vavoo" in navigation:
1. @authorise checks MacReplay session → ✅ Valid
2. Auto-login creates Vavoo session
3. Redirect to /vavoo/
4. @login_required checks Vavoo session → ✅ Valid
5. Vavoo dashboard renders
```

## Session Management

### Shared Session
Both MacReplayXC and Vavoo use Flask's session system, which is shared:

```python
# MacReplayXC sets session
session["authenticated"] = True

# Vavoo checks session
session["logged_in"] = True  # Auto-set by /vavoo_page
```

### Session Keys
- **MacReplayXC**: `authenticated`, `username`
- **Vavoo**: `logged_in`, `user`

## Background Workers

### Refresh Worker
- **Purpose**: Periodically refreshes IPTV playlists
- **Interval**: 600 seconds (10 minutes)
- **Daemon**: Yes (stops when main process stops)

### Resolution Workers
- **Purpose**: Resolves channel URLs in parallel
- **Count**: min(4, CPU cores)
- **Enabled**: Only if `RES=true` in Vavoo config
- **Daemon**: Yes

### Worker Lifecycle
```
Docker Container Start
  ↓
app-docker.py loads
  ↓
vavoo_blueprint.py imports
  ↓
Workers start (daemon processes)
  ↓
Container runs
  ↓
Container stops → Workers stop automatically
```

## File Structure

```
MacReplayXC/
├── app-docker.py              # Main Flask app
├── vavoo_blueprint.py         # Blueprint wrapper
├── vavoo/                     # Vavoo directory
│   ├── vavoo2.py             # Original Vavoo app
│   ├── config.json           # Vavoo config
│   ├── mapping.json          # Channel mappings
│   └── templates/            # Vavoo templates (if any)
├── templates/
│   ├── base.html             # MacReplay navigation (includes Vavoo link)
│   └── ... (other templates)
└── data/
    └── vavoo_playlists/      # Vavoo playlist cache
```

## Port Configuration

**Single Port**: 8001 (shared by MacReplayXC and Vavoo)

```
http://localhost:8001/          → MacReplayXC
http://localhost:8001/dashboard → MacReplayXC Dashboard
http://localhost:8001/vavoo/    → Vavoo Dashboard
http://localhost:8001/vavoo/playlist.m3u → Vavoo Playlist
```

## Benefits of Blueprint Architecture

1. **Single Port**: Everything runs on port 8001
2. **Code Separation**: Vavoo code stays in `vavoo/` directory
3. **Independent Development**: Vavoo can be updated separately
4. **Shared Resources**: Same Flask app, session, logging
5. **Clean Integration**: No code duplication
6. **Backward Compatible**: Vavoo can still run standalone

## Limitations

1. **Styling**: Vavoo has its own styling (purple gradient) which differs from MacReplayXC's dark theme
2. **Session Sharing**: Both apps share the same session, which could cause conflicts if session keys overlap
3. **Worker Management**: Workers are daemon processes and can't be easily restarted without restarting the container

## Future Improvements

1. **Unified Styling**: Modify Vavoo templates to match MacReplayXC's Tabler theme
2. **Session Isolation**: Use separate session namespaces for MacReplayXC and Vavoo
3. **Worker Control**: Add UI controls to start/stop Vavoo workers
4. **Configuration**: Integrate Vavoo config into MacReplayXC settings page
