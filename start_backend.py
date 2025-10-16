#!/usr/bin/env python3
"""
Startup script for the Digital Article backend.

This script starts the FastAPI server with proper configuration.
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Start the FastAPI backend server."""
    
    # Change to backend directory
    backend_dir = Path(__file__).parent / "backend"
    backend_dir = backend_dir.resolve()  # Get absolute path
    
    print("🚀 Starting Digital Article Backend...")
    print(f"📁 Script location: {Path(__file__).parent}")
    print(f"📁 Backend directory: {backend_dir}")
    print(f"📁 App directory exists: {(backend_dir / 'app').exists()}")
    print(f"📁 Current working directory before: {os.getcwd()}")
    
    os.chdir(backend_dir)
    print(f"📁 Current working directory after: {os.getcwd()}")
    
    # Verify app module exists
    app_dir = backend_dir / "app"
    main_py = app_dir / "main.py"
    if not app_dir.exists():
        print(f"❌ Error: app directory not found at {app_dir}")
        sys.exit(1)
    if not main_py.exists():
        print(f"❌ Error: main.py not found at {main_py}")
        sys.exit(1)
    
    print("🌐 Server will be available at: http://localhost:8000")
    print("📖 API documentation will be available at: http://localhost:8000/docs")
    print("\n" + "="*60)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
