#!/bin/bash
# Startup script for MacReplayXC + Vavoo in one container

echo "🚀 Starting MacReplayXC + Vavoo..."

# Start Vavoo in background
echo "📡 Starting Vavoo on port 4323..."
cd /app/vavoo
python vavoo2.py &
VAVOO_PID=$!
echo "✅ Vavoo started (PID: $VAVOO_PID)"

# Wait a moment for Vavoo to start
sleep 2

# Start MacReplayXC in foreground
echo "🎬 Starting MacReplayXC on port 8001..."
cd /app
python app-docker.py

# If MacReplayXC exits, kill Vavoo too
kill $VAVOO_PID 2>/dev/null
