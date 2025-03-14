import requests
import sys

print("Python version:", sys.version)
print("Testing API connection...")

def test_basic_connection():
    """Test basic connectivity with direct print statements"""
    print("Testing direct print output...")
    try:
        r = requests.get("http://localhost:5000/health", timeout=5)
        print(f"Connection successful - Status: {r.status_code}")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("Script started")
    success = test_basic_connection()
    
    if success:
        print("Connection test passed, running full tests...")
        tester = ApiTester()
        try:
            tester.run_tests()
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Cannot run tests due to connection failure")