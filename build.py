"""
build.py  –  Builds Kopirovacka.exe using PyInstaller
Run: python build.py
Output: dist/Kopirovacka.exe
"""
import subprocess
import sys
import os
import shutil

APP_NAME = "Kopirovacka"
ENTRY = "app/main.py"
ICON = "assets/icon.ico"

def build():
    print("=" * 50)
    print(f"  Building {APP_NAME}...")
    print("=" * 50)

    # Install deps first
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "-r", "app/requirements.txt", "--quiet"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={APP_NAME}",
        "--add-data=app;app",
    ]

    if os.path.exists(ICON):
        cmd.append(f"--icon={ICON}")

    cmd += [
        "--hidden-import=win32clipboard",
        "--hidden-import=win32con",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=keyboard",
        ENTRY,
    ]

    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe = f"dist/{APP_NAME}.exe"
        print(f"\n Build successful: {exe}")
        print(f"   Size: {os.path.getsize(exe) / 1024 / 1024:.1f} MB")
    else:
        print("\n Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build()
