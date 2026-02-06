# Vavoo Integration for MacReplayXC
# This file integrates Vavoo as a sub-application using DispatcherMiddleware

import os
import sys
import multiprocessing
import threading

# Add vavoo directory to path
vavoo_dir = os.path.join(os.path.dirname(__file__), 'vavoo')
sys.path.insert(0, vavoo_dir)

# Import and setup Vavoo
vavoo_app = None
vavoo_initialized = False

def init_vavoo():
    """Initialize Vavoo application and workers"""
    global vavoo_app, vavoo_initialized
    
    if vavoo_initialized:
        return vavoo_app
    
    try:
        # Change to vavoo directory
        original_cwd = os.getcwd()
        os.chdir(vavoo_dir)
        
        # Import vavoo
        from vavoo2 import (
            app as vavoo_flask_app,
            load_config_from_disk,
            load_mappings,
            resolution_worker,
            refresh_worker,
            request_refresh,
            CONFIG
        )
        
        # Initialize configuration
        print("🔧 Initializing Vavoo configuration...")
        load_config_from_disk()
        load_mappings()
        
        # Start background workers
        print("🚀 Starting Vavoo background workers...")
        
        # Create multiprocessing queue for resolution workers
        RES_QUEUE = multiprocessing.Queue()
        
        # Start resolution workers if RES mode is enabled
        if bool(CONFIG.get("RES", False)):
            RES_WORKERS = min(4, multiprocessing.cpu_count())
            for _ in range(RES_WORKERS):
                p = multiprocessing.Process(
                    target=resolution_worker,
                    args=(RES_QUEUE,),
                    daemon=True
                )
                p.start()
            print(f"✅ {RES_WORKERS} Vavoo resolution workers started")
        
        # Start refresh worker
        refresh_process = multiprocessing.Process(
            target=refresh_worker,
            daemon=True
        )
        refresh_process.start()
        print("✅ Vavoo refresh worker started")
        
        # Request initial refresh
        request_refresh("*", rebuild=True)
        print("✅ Vavoo initial refresh scheduled")
        
        # Change back
        os.chdir(original_cwd)
        
        vavoo_app = vavoo_flask_app
        vavoo_initialized = True
        print("✅ Vavoo application initialized successfully")
        
        return vavoo_app
        
    except Exception as e:
        print(f"❌ Error initializing Vavoo: {e}")
        import traceback
        traceback.print_exc()
        os.chdir(original_cwd)
        return None

# Initialize Vavoo on import
vavoo_app = init_vavoo()

