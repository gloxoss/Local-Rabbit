
import sys
import os
from pathlib import Path

# Add script dir to path
sys.path.append(str(Path(__file__).parent))

from scanners.secret_scanner import get_scanner

def main():
    print("🔒 Testing Secret Scanner...")
    scanner = get_scanner()
    
    test_cases = [
        ("Safe code", False),
        ("const aws_key = 'AKIAIOSFODNN7EXAMPLE';", True),
        ("github_token = 'ghp_1234567890abcdef1234567890abcdef36';", True),
        ("slack_url = 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX';", True),
        ("private_key = '-----BEGIN RSA PRIVATE KEY-----';", True),
        ("password = 'super_secret_password';", True)
    ]
    
    passed = 0
    for code, should_fail in test_cases:
        issues = scanner.scan(code)
        did_fail = len(issues) > 0
        
        if did_fail == should_fail:
            print(f"✅ Passed: {code[:30]}...")
            passed += 1
        else:
            print(f"❌ Failed: {code[:30]}... (Expected secrets: {should_fail}, Found: {did_fail})")
            if issues:
                print(f"   Issues: {issues}")

    if passed == len(test_cases):
        print(f"\n✅ All {passed} tests passed!")
    else:
        print(f"\n❌ {len(test_cases) - passed} tests failed.")

if __name__ == "__main__":
    main()
