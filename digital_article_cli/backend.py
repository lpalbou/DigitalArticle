"""
Digital Article Backend Starter

Console script entry point for starting the backend server.
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path


def kill_process_on_port(port: int) -> None:
    """Kill any process running on the specified port."""
    try:
        # Find processes using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        print(f"🔄 Killing existing process {pid} on port {port}")
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)  # Give it a moment to terminate gracefully
                        # Force kill if still running
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # Process already terminated
                    except (ValueError, ProcessLookupError):
                        pass
        else:
            print(f"✅ No existing process found on port {port}")
            
    except FileNotFoundError:
        print("⚠️  lsof command not found, skipping port cleanup")
    except subprocess.TimeoutExpired:
        print(f"⚠️  Timeout while checking port {port}")
    except Exception as e:
        print(f"⚠️  Error cleaning port {port}: {e}")


def find_project_root() -> Path:
    """Find the project root directory by looking for backend folder."""
    current = Path.cwd()
    
    # First, try current directory
    if (current / 'backend').exists():
        return current
    
    # Then try the directory where this script is located
    script_dir = Path(__file__).parent.parent
    if (script_dir / 'backend').exists():
        return script_dir
    
    # Look up the directory tree
    for parent in current.parents:
        if (parent / 'backend').exists():
            return parent
    
    raise FileNotFoundError("Could not find Digital Article project root (no 'backend' directory found)")


def check_backend_dependencies() -> None:
    """Check if required backend dependencies are available."""
    try:
        import uvicorn
        print(f"✅ uvicorn {uvicorn.__version__}")
    except ImportError:
        print("❌ uvicorn not found. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'uvicorn[standard]'], check=True)
            print("✅ uvicorn installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install uvicorn. Please install manually:")
            print("   pip install uvicorn[standard]")
            sys.exit(1)


def main() -> None:
    """Main entry point for da-backend command."""
    print("🚀 Starting Digital Article Backend...")
    
    try:
        # Find project root
        project_root = find_project_root()
        backend_dir = project_root / 'backend'
        
        print(f"📁 Project root: {project_root}")
        print(f"📁 Backend directory: {backend_dir}")
        
        # Check dependencies
        check_backend_dependencies()
        
        # Kill any existing process on port 8000
        kill_process_on_port(8000)
        
        # Change to backend directory
        os.chdir(backend_dir)
        
        # Start the backend server
        print("📡 Launching backend server on http://localhost:8000")
        print("📝 API docs available at http://localhost:8000/docs")
        print("🔄 Server will auto-reload on code changes")
        print("🛑 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', 
            '--reload', 
            '--port', '8000',
            '--host', '0.0.0.0'
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped by user")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("💡 Make sure you're running this from the Digital Article project directory")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start backend server: {e}")
        print("💡 Check that all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
