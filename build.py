"""Build script - run this to create the exe."""
import subprocess
import sys
import os
import shutil

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(os.path.dirname(script_dir), "openclaw.ico")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "OpenClaw",
    "--icon", icon_path,
    "--hidden-import=customtkinter",
    "--hidden-import=PIL",
    "--collect-data", "customtkinter",
    os.path.join(script_dir, "openclaw_launcher.py")
]

print("Building OpenClaw.exe ...")
subprocess.run(cmd, cwd=script_dir)

# Copy .ico next to the exe so it can be found at runtime
dist_dir = os.path.join(script_dir, "dist")
if os.path.exists(icon_path) and os.path.isdir(dist_dir):
    shutil.copy2(icon_path, os.path.join(dist_dir, "openclaw.ico"))
    print("Copied openclaw.ico to dist/")

print("\nDone! Check launcher/dist/OpenClaw.exe")
