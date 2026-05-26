import sys
import os
from pathlib import Path

# Add script dir to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.cortex.indexer import get_indexer

def main():
    print("🚀 Starting RAG Index Build...")
    project_root = os.getcwd()
    print(f"📂 Project Root: {project_root}")
    
    try:
        indexer = get_indexer()
        indexer.full_scan(project_root)
        print("✅ Indexing Complete!")
    except Exception as e:
        print(f"❌ Indexing Failed: {e}")

if __name__ == "__main__":
    main()
