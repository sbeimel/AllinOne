# Vavoo Integration for MacReplayXC
# Starts Vavoo as a separate process on port 4323

import os
import sys
import multiprocessing
import subprocess
import time
import requests

# Vavoo configuration
VAVOO_PORT = 4323
VAVOO_DIR = os.path.join(os.path.dirname(__file__), 'vavoo')
VAVOO_PROCESS = None

def start_vavoo_server():
    """Start Vavoo server as a separate process"""
    global VAVOO_PROCESS
    
    try:
        print("🚀 Starting Vavoo server on port 4323...")
        
        # Change to vavoo directory
        os.chdir(VAVOO_DIR)
        
        # Start vavoo2.py as subprocess
        VAVOO_PROCESS = subprocess.Popen(
            [sys.executable, 'vavoo2.py'],
            cwd=VAVOO_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get(f'http://localhost:{VAVOO_PORT}/', timeout=1)
                if response.status_code in [200, 302, 401]:
                    print(f"✅ Vavoo server started successfully on port {VAVOO_PORT}")
                    return True
            except:
                time.sleep(1)
        
        print(f"⚠️ Vavoo server may not have started properly")
        return False
        
    except Exception as e:
        print(f"❌ Error starting Vavoo server: {e}")
        import traceback
        traceback.print_exc()
        return False

def stop_vavoo_server():
    """Stop Vavoo server"""
    global VAVOO_PROCESS
    if VAVOO_PROCESS:
        print("🛑 Stopping Vavoo server...")
        VAVOO_PROCESS.terminate()
        VAVOO_PROCESS.wait()
        print("✅ Vavoo server stopped")

# Start Vavoo server on import
vavoo_started = start_vavoo_server()


