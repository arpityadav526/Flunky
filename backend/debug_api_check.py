import httpx
from cli.config import load_token

BASE_URL = "http://127.0.0.1:8000"


def main():
    token = load_token()

    if not token:
        print("❌ No token found! Please login first.")
        return

    clean_token = token.strip()

    print(f"Token loaded: {clean_token[:50]}...")
    print(f"Token length: {len(clean_token)}")

    headers = {
        "Authorization": f"Bearer {clean_token}"
    }

    print(f"\nHeaders: {headers}")

    try:
        response = httpx.post(
            f"{BASE_URL}/tasks",
            json={
                "task_title": "Test Task",
                "task_description": "Test Description"
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


if __name__ == "__main__":
    main()