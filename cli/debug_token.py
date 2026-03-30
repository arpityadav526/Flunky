# debug_token.py
from cli.config import load_token
import json
from pathlib import Path

# Load token
token = load_token()

print("=" * 50)
print("TOKEN DEBUG INFO")
print("=" * 50)

if token:
    print(f"Token exists: YES")
    print(f"Token length: {len(token)}")
    print(f"Token repr: {repr(token)}")
    print(f"First 20 chars: {repr(token[:20])}")
    print(f"Last 20 chars: {repr(token[-20:])}")
    print(f"Has leading space: {token[0] == ' '}")
    print(f"Has trailing space: {token[-1] == ' '}")
    print(f"Has newline: {'\\n' in token}")
    
    # Check what the header would look like
    header_value = f"Bearer {token.strip()}"
    print(f"\nHeader value: {repr(header_value)}")
    print(f"Header length: {len(header_value)}")
    
    # Raw file content
    config_file = Path.home() / ".flunky" / "config.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            raw_content = f.read()
        print(f"\nRaw file content:")
        print(repr(raw_content))
else:
    print("Token NOT found!")

print("=" * 50)
