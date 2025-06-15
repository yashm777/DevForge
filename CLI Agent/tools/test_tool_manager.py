from tool_manager import handle_request

# Test installing Docker
request_1 = {"task": "install_tool", "tool": "docker"}
response_1 = handle_request(request_1)
print(response_1)

# Test installing Node.js
request_2 = {"task": "install_tool", "tool": "nodejs"}
response_2 = handle_request(request_2)
print(response_2)
