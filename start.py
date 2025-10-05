#!/usr/bin/env python3
"""
Startup script for EPFO Bot Backend.
Provides easy commands for development and production.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Please copy env.example to .env and fill in your values:")
        print("   cp env.example .env")
        return False
    return True

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    try:
        subprocess.run([sys.executable, "test_main.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        return False

def run_dev():
    """Run in development mode."""
    if not check_env_file():
        return False
    
    print("🚀 Starting development server...")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Development server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        return False
    return True

def run_prod():
    """Run in production mode."""
    if not check_env_file():
        return False
    
    print("🚀 Starting production server...")
    try:
        subprocess.run([
            sys.executable, "-m", "gunicorn", 
            "app.main:app", 
            "-w", "4", 
            "-k", "uvicorn.workers.UvicornWorker",
            "--bind", "0.0.0.0:8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Production server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        return False
    return True

def show_help():
    """Show help message."""
    print("""
🤖 EPFO Bot Backend - Startup Script

Usage: python start.py [command]

Commands:
  install    Install Python dependencies
  test       Run test suite
  dev        Start development server (with auto-reload)
  prod       Start production server
  help       Show this help message

Examples:
  python start.py install    # Install dependencies
  python start.py test       # Run tests
  python start.py dev       # Start development server
  python start.py prod      # Start production server

Environment Setup:
  1. Copy env.example to .env
  2. Fill in your API keys and configuration
  3. Run: python start.py install
  4. Run: python start.py test
  5. Run: python start.py dev

API Documentation:
  Once running, visit: http://localhost:8000/docs
""")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "install":
        install_dependencies()
    elif command == "test":
        run_tests()
    elif command == "dev":
        run_dev()
    elif command == "prod":
        run_prod()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()
