import requests
import json

url = "http://localhost:8000/mcp/"

# === EXAMPLE 1: Check if JAVA_HOME is set ===
payload = {
    "jsonrpc": "2.0",
    "method": "tool_action_wrapper",
    "id": 1,
    "params": {
        "task": "system_config",
        "tool_name": "JAVA_HOME",
        "action": "check"
    }
}

response = requests.post(url, json=payload)
print("=== JAVA_HOME ===")
print(json.dumps(response.json(), indent=2))


# === EXAMPLE 2: Append to PATH ===
payload = {
    "jsonrpc": "2.0",
    "method": "tool_action_wrapper",
    "id": 2,
    "params": {
        "task": "system_config",
        "tool_name": "C:\\Program Files\\Java\\bin",
        "action": "append_to_path"
    }
}

response = requests.post(url, json=payload)
print("\n=== Append to PATH ===")
print(json.dumps(response.json(), indent=2))