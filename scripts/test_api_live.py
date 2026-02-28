
import urllib.request
import json
import sys

BASE_URL = "http://localhost:8001/api/v1"

def test_endpoint(path, description):
    url = f"{BASE_URL}{path}"
    print(f"\nTesting {description} ({url})...")
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print("SUCCESS")
                # Pretty print the first few items or summary
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            print(f"Key '{key}' has {len(value)} items.")
                            if len(value) > 0:
                                print(f"First item: {value[0]}")
                        else:
                            print(f"{key}: {value}")
                else:
                    print(data)
                return True
            else:
                print(f"FAILED: Status {response.status}")
                return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Starting API Verification...")

    # 1. Test Majors
    test_endpoint("/majors", "Majors List")

    # 2. Test Courses
    test_endpoint("/courses", "Courses List")

    # 3. Test Public Policies
    test_endpoint("/public/policies", "Public Policies")

    # 4. Test Course Files (CDS524)
    test_endpoint("/courses/CDS524/files", "CDS524 Files")

    print("\nVerification Complete.")
