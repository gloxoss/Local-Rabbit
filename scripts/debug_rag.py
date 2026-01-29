
import sys
import os
from pathlib import Path

# Add script dir to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.cortex.indexer import get_indexer

def debug_query(text):
    print(f"🔎 Querying: '{text}'")
    try:
        indexer = get_indexer()
        results = indexer.query(text)
        print(f"✅ Found {len(results)} results:")
        for r in results:
            print(f"--- {r['metadata']['path']} (dist: {r['distance']:.4f}) ---")
            print(r['text'][:200] + "...")
            print("-" * 50)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "hello"
    debug_query(query)
