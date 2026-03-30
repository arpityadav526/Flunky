# test_api.py
import httpx
from cli.config import load_token

# Load token
token = load_token()

if not token:
    print("❌ No token found! Please login first.")
    exit(1)

print(f"Token loaded: {token[:50]}...")

# Test creating a task
BASE_URL = "http://127.0.0.1:8000"

# Clean the token
clean_token = token.strip()

print(f"\nCleaned token: {clean_token[:50]}...")
print(f"Token length: {len(clean_token)}")

# Create headers
headers = {
    "Authorization": f"Bearer {clean_token}"
}

print(f"\nHeaders: {headers}")

# Make request
try:
    response = httpx.post(
        f"{BASE_URL}/tasks",
        json={
            "title": "Test Task",
            "description": "Test Description"
        },
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 201:
        print("✅ SUCCESS!")
    else:
        print("❌ FAILED!")
        
except Exception as e:
    print(f"❌ Error: {e}")