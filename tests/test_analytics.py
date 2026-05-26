import sys
import json
from pathlib import Path
from experimental.analytics import calculate_complexity, calculate_health_score
from watcher import update_dashboard_stats, DEFAULT_CONFIG

def test_metrics():
    print("Testing Analytics Metrics...")
    
    # Simple code example
    code = """
def hello():
    if True:
        print("World")
    """
    comp = calculate_complexity(code)
    print(f"Complexity (Simple): {comp} (Expected ~1-2)")
    
    # Complex code example
    complex_code = """
def complex():
    if True:
        if True:
            if True:
                if True:
                    print("Deep")
    """
    comp_deep = calculate_complexity(complex_code)
    print(f"Complexity (Deep): {comp_deep}")
    
    assert comp_deep > comp
    
    # Health Score
    issues = {"critical": ["error"], "warning": ["warn"], "suggestion": []}
    health = calculate_health_score(issues, comp)
    print(f"Health Score: {health} (Expected < 100)")
    
def test_stats_update():
    print("\nTesting Stats Update...")
    root = Path(".")
    config = DEFAULT_CONFIG
    
    # Create dummy reviews folder
    (root / "reviews").mkdir(exist_ok=True)
    
    issues = {"critical": ["e1"], "warning": ["w1"], "suggestion": []}
    
    # Create dummy file to read
    dummy_file = root / "test_file.py"
    dummy_file.write_text("def foo():\n    pass")
    
    try:
        update_dashboard_stats(".", config, "test_file.py", issues)
        
        stats_path = root / "reviews/stats.json"
        assert stats_path.exists()
        
        with open(stats_path) as f:
            stats = json.load(f)
            
        print("Stats Keys:", stats.keys())
        assert "health_score" in stats
        assert "hotspots" in stats
        print(f"Global Health Score: {stats['health_score']}")
        print(f"Hotspots: {len(stats['hotspots'])}")
        print("✅ Stats updated successfully")
        
    finally:
        if dummy_file.exists(): dummy_file.unlink()
        # cleanup stats if needed, or leave for manual inspection

if __name__ == "__main__":
    test_metrics()
    test_stats_update()
