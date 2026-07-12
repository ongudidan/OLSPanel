#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def run_command(cmd, shell=False):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, shell=shell)
    if res.returncode != 0:
        print(f"❌ Command failed with return code {res.returncode}")
        sys.exit(1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("🛠️ Starting Build Pipeline for OLSPanel Server Wrapper...")

    # Detect pip
    if not shutil.which("pip") and not shutil.which("pip3"):
        print("❌ pip or pip3 not found. Please install python3-pip first.")
        sys.exit(1)

    pip_cmd = "pip3" if shutil.which("pip3") else "pip"

    # Install/Verify PyInstaller
    print("📦 Verifying PyInstaller installation...")
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed.")
    except ImportError:
        print("📥 PyInstaller not found. Installing via pip...")
        run_command([pip_cmd, "install", "pyinstaller"])

    # Clean previous builds
    print("🧹 Cleaning previous builds...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    spec_file = "olspanelcp.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)

    # Run PyInstaller compile
    print("🚀 Compiling server.py to standalone binary...")
    pyinstaller_bin = shutil.which("pyinstaller")
    if not pyinstaller_bin:
        # Fallback to python module execution
        run_command([sys.executable, "-m", "PyInstaller", "--onefile", "--name", "olspanelcp", "server.py"])
    else:
        run_command([pyinstaller_bin, "--onefile", "--name", "olspanelcp", "server.py"])

    # Verify output
    binary_path = os.path.join("dist", "olspanelcp")
    if os.path.exists(binary_path):
        print("\n🎉 Build Completed Successfully!")
        print(f"📁 Standalone Binary Location: {os.path.abspath(binary_path)}")
        print(f"⚖️ Binary Size: {os.path.getsize(binary_path) / (1024*1024):.2f} MB")
    else:
        print("❌ Build failed: output binary not found.")
        sys.exit(1)

if __name__ == '__main__':
    main()
