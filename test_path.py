from pathlib import Path
import os

root = os.getcwd()
filepath = "scripts\\watcher.py"

try:
    abs_path = str((Path(root) / filepath).resolve())
    print(f"Absolute path: {abs_path}")
except Exception as e:
    print(f"Error: {e}")
