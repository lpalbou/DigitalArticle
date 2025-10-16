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
    os.chdir(backend_dir)
    
    print("🚀 Starting Digital Article Backend...")
    print(f"📁 Working directory: {backend_dir}")
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
