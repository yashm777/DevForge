# Status Keys
SUCCESS = "success"
FAILURE = "failure"
ERROR = "error"

# Operation Messages
INSTALL_SUCCESS = "Tool '{tool}' installed successfully."
INSTALL_FAIL = "Failed to install tool '{tool}'."
INSTALL_UNSUPPORTED = "Installation for tool '{tool}' is not supported on {os}."

UNINSTALL_SUCCESS = "Tool '{tool}' uninstalled successfully."
UNINSTALL_FAIL = "Failed to uninstall tool '{tool}'."
UNINSTALL_UNSUPPORTED = "Uninstallation for tool '{tool}' is not supported on {os}."

UPGRADE_SUCCESS = "Tool '{tool}' upgraded successfully."
UPGRADE_FAIL = "Failed to upgrade tool '{tool}'."
UPGRADE_UNSUPPORTED = "Upgrade for tool '{tool}' is not supported on {os}."

VERSION_CHECK_SUCCESS = "Version of '{tool}' retrieved successfully: {version}."
VERSION_CHECK_FAIL = "Failed to retrieve version for tool '{tool}'."
VERSION_UNSUPPORTED = "Version check for tool '{tool}' is not supported on {os}."

# Generic Messages
MISSING_TOOL_PARAM = "Missing required parameter 'tool'."
UNKNOWN_TASK = "Unknown task: {task}"
UNSUPPORTED_OS = "Unsupported operating system."
