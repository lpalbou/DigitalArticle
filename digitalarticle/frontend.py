"""
Digital Article Frontend Starter

Console script entry point for starting the frontend development server.
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
    """Find the project root directory by looking for frontend folder."""
    current = Path.cwd()
    
    # First, try current directory
    if (current / 'frontend').exists():
        return current
    
    # Then try the directory where this script is located
    script_dir = Path(__file__).parent.parent
    if (script_dir / 'frontend').exists():
        return script_dir
    
    # Look up the directory tree
    for parent in current.parents:
        if (parent / 'frontend').exists():
            return parent
    
    raise FileNotFoundError("Could not find Digital Article project root (no 'frontend' directory found)")


def check_node_and_npm() -> None:
    """Check if Node.js and npm are available."""
    try:
        # Check Node.js
        node_result = subprocess.run(
            ['node', '--version'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        if node_result.returncode != 0:
            raise FileNotFoundError("Node.js not found")
        
        # Check npm
        npm_result = subprocess.run(
            ['npm', '--version'], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        if npm_result.returncode != 0:
            raise FileNotFoundError("npm not found")
            
        print(f"✅ Node.js {node_result.stdout.strip()}")
        print(f"✅ npm {npm_result.stdout.strip()}")
        
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Node.js/npm not found. Please install Node.js first:")
        print("   https://nodejs.org/")
        sys.exit(1)


def install_dependencies(frontend_dir: Path) -> None:
    """Install npm dependencies if node_modules doesn't exist."""
    node_modules = frontend_dir / 'node_modules'
    package_json = frontend_dir / 'package.json'
    
    if not package_json.exists():
        print(f"❌ package.json not found in {frontend_dir}")
        sys.exit(1)
    
    if not node_modules.exists():
        print("📦 Installing npm dependencies...")
        try:
            subprocess.run(
                ['npm', 'install'], 
                cwd=frontend_dir, 
                check=True,
                timeout=300  # 5 minutes timeout
            )
            print("✅ Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("❌ Timeout while installing dependencies")
            sys.exit(1)


def main() -> None:
    """Main entry point for da-frontend command."""
    print("🚀 Starting Digital Article Frontend...")
    
    try:
        # Find project root
        project_root = find_project_root()
        frontend_dir = project_root / 'frontend'
        
        print(f"📁 Project root: {project_root}")
        print(f"📁 Frontend directory: {frontend_dir}")
        
        # Check Node.js and npm
        check_node_and_npm()
        
        # Kill any existing process on port 3000
        kill_process_on_port(3000)
        
        # Install dependencies if needed
        install_dependencies(frontend_dir)
        
        # Change to frontend directory
        os.chdir(frontend_dir)
        
        # Start the frontend development server
        print("🌐 Launching frontend development server on http://localhost:3000")
        print("🔄 Server will auto-reload on code changes")
        print("🛑 Press Ctrl+C to stop the server")
        print("-" * 50)
        
        subprocess.run(['npm', 'run', 'dev'], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped by user")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("💡 Make sure you're running this from the Digital Article project directory")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start frontend server: {e}")
        print("💡 Try running 'npm install' in the frontend directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
