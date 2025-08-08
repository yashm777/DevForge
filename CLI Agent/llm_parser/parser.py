import openai
import json
import sys
import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Available tools and their schemas
AVAILABLE_TOOLS = {
    "install": {
        "description": "Install a development tool or package",
        "params": {
            "tool_name": "Name of the tool to install (e.g., docker, nodejs, python)",
            "version": "Version to install (optional, defaults to latest)"
        }
    },
    "uninstall": {
        "description": "Uninstall a development tool or package",
        "params": {
            "tool_name": "Name of the tool to uninstall"
        }
    },
    "update": {
        "description": "Update a development tool or package",
        "params": {
            "tool_name": "Name of the tool to update",
            "version": "Version to update to (optional, defaults to latest)"
        }
    },
    "version": {
        "description": "Check the version of a development tool",
        "params": {
            "tool_name": "Name of the tool to check version for"
        }
    },
    "info://server": {
        "description": "Get system/server information",
        "params": {}
    },
    "generate_code": {
        "description": "Generate code from a description using GPT-4o",
        "params": {
            "description": "Description of the code to generate"
        }
    },
    "system_config": {
        "description": "Perform system configuration tasks like checking env vars or modifying PATH",
        "params": {
            "action": "The system_config action to perform (e.g. check, set, append_to_path, remove_from_path, is_port_open, is_service_running, remove_env, list_env)",
            "tool_name": "The name of the variable, service, or path to act on",
            "value": "Optional value (used with 'set')"
        }
    },
    "install_vscode_extension": {
        "description": "Install a VSCode extension",
        "params": {
            "tool_name": "The ID of the extension to install (e.g., 'ms-python.python')"
        }
    },
    "uninstall_vscode_extension": {
        "description": "Uninstall a VSCode extension",
        "params": {
            "tool_name": "The ID of the extension to uninstall (e.g., 'ms-python.python')"
        }
    },
    "git_setup": {
        "description": "Perform git-related tasks such as cloning, switching branches, generating SSH keys, adding SSH keys to GitHub, or checking SSH authentication.",
        "params": {
            "action": "The git action to perform (clone, switch_branch, generate_ssh_key, add_ssh_key, check_ssh_key_auth)",
            "repo_url": "URL of the Git repository to clone (required for clone)",
            "dest_dir": "Destination directory (optional, for clone and switch_branch)",
            "branch": "Branch name (optional, for clone and switch_branch)",
            "username": "GitHub username (optional, for switch_branch)",
            "email": "Email address (optional, for generate_ssh_key, add_ssh_key, switch_branch)",
            "pat": "GitHub Personal Access Token (optional, for add_ssh_key)"
        }

    }

}

def build_prompt(user_input: str) -> str:
    """Constructs a prompt that guides GPT to generate a valid tool call, with extended guidance."""
    tool_docs = json.dumps(AVAILABLE_TOOLS, indent=2)

    additional_guidance = """
# Additional Guidelines:
- When users provide ambiguous tool names, map them to actual package names used by Linux package managers like APT.
- Interpret phrases like "get me X", "download X", "I need X", "install X for me" as install commands.
- Examples of name resolution:
  - "java" → "default-jdk"
  - "node" or "nodejs" → "nodejs"
  - "python" → "python3"
  - "gcc" → "gcc"
  - "vscode" → "code"
  - "nvim" or "neovim" → "neovim"
  - "docker" → "docker.io"
  - "jdk" → "default-jdk"
  - "intellij" → "intellij-idea-community"
  - "pycharm" → "pycharm-community"
  - "eclipse" → "eclipse"
  - "git" → "git"
  - "maven" → "maven"
  - "gradle" → "gradle"
- Always return the base package name commonly used on Ubuntu/Debian systems; do not include OS-specific variants.
- For version-specific installs, append the version number as part of the package name when specified, for example:
  - "java 11" → "openjdk-11-jdk"
  - "python 3.9" → "python3.9"
- If version is not specified or is "latest", use the default package name.
- If the package is not available via standard package managers and appears to be a known tool, provide a field called "manual_url" with the official website for manual installation.
- Return only a single valid JSON object with keys "method" and "params".
- For git/SSH key retrieval, interpret phrases like "get key", "get sshkey", "get public key", "show my ssh key", "show public key", "display ssh key", etc. as a request for the public SSH key. Use method 'tool_action_wrapper' with params: {"task": "git_setup", "action": "get_public_key"}.
- Do NOT include any explanations, aliases, markdown, or code blocks in the response.
"""

    return (
        "You are an AI assistant that converts natural language developer requests into structured tool calls.\n\n"
        f"The tools available are defined below in JSON:\n{tool_docs}\n\n"
        "IMPORTANT: For install, uninstall, update, and version actions, use method 'tool_action_wrapper' "
        "with params containing 'task' and 'tool_name'.\n"
        "For system info, use method 'info://server' with empty params.\n"
        "For code generation, use method 'generate_code' with 'description' param.\n\n"
        "Examples:\n"
        "- Install: {'method': 'tool_action_wrapper', 'params': {'task': 'install', 'tool_name': 'docker'}}\n"
        "- 'Get me docker': {'method': 'tool_action_wrapper', 'params': {'task': 'install', 'tool_name': 'docker'}}\n"
        "- 'I need python': {'method': 'tool_action_wrapper', 'params': {'task': 'install', 'tool_name': 'python3'}}\n"
        "- Version check: {'method': 'tool_action_wrapper', 'params': {'task': 'version', 'tool_name': 'python'}}\n"
        "- System info: {'method': 'info://server', 'params': {}}\n"
        "- Generate code: {'method': 'generate_code', 'params': {'description': 'hello world function'}}\n"
        "- System config: {'method': 'tool_action_wrapper', 'params': {'task': 'system_config', 'action': 'check', 'tool_name': 'JAVA_HOME'}}\n"
        "- Git setup (clone): {'method': 'tool_action_wrapper', 'params': {'task': 'git_setup', 'action': 'clone', 'repo_url': 'git@github.com:user/repo.git', 'dest_dir': '/path/to/dir'}}\n"
        "- Git setup (generate SSH key): {'method': 'tool_action_wrapper', 'params': {'task': 'git_setup', 'action': 'generate_ssh_key', 'email': 'user@example.com'}}\n"
        f"{additional_guidance}\n\n"
        "Given the user's instruction, identify the correct tool(s) and return a JSON object if only one action is required, or a JSON array if multiple actions are needed.\n"
        "DO NOT return multiple objects separated by commas. DO NOT include extra text, explanations, markdown, or comments. ONLY return valid JSON.\n\n"
        f"User input: \"{user_input}\""

    )

def parse_user_command(user_input: str) -> Dict[str, Any]:
    """Parses user input into a structured tool command using OpenAI API."""
    if not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key not set. Please set OPENAI_API_KEY environment variable.",
            "fallback": "Try using specific commands like 'install docker' or 'check version nodejs'"
        }

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = build_prompt(user_input)

        logging.debug("Sending prompt to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI command parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=200
        )

        raw_response = response.choices[0].message.content.strip()
        logging.debug(f"Raw response: {raw_response}")

        # Strip Markdown if present
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3].strip()

        # ✅ Primary parse attempt
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError as e:
            # ✅ Fallback: Detect multiple JSON objects and wrap in array
            if raw_response.count('"method"') > 1 and not raw_response.strip().startswith('['):
                fixed_response = "[" + raw_response.replace("}\n,", "},") + "]"
                try:
                    return json.loads(fixed_response)
                except json.JSONDecodeError as inner_e:
                    logging.error(f"Fallback parsing also failed: {inner_e}")

            logging.error(f"Failed to parse JSON from OpenAI response: {e}\nRaw response: {raw_response}")
            return {"error": "Failed to parse JSON from OpenAI response.", "raw_response": raw_response}

    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        return {"error": f"OpenAI API call failed: {e}"}


def get_command_suggestions() -> list:
    """Return a list of available commands and their descriptions."""
    suggestions = []
    for cmd, meta in AVAILABLE_TOOLS.items():
        suggestions.append({
            "command": cmd,
            "description": meta.get("description", "")
        })
    return suggestions


def generate_smart_tool_url(tool_name: str) -> str:
    if not OPENAI_API_KEY:
        return f"https://www.google.com/search?q=download+{tool_name.replace(' ', '+')}+official"

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            f"You are helping a developer locate the most appropriate and official website or trusted source to download or learn more about a tool called '{tool_name}'."
"If the tool is well-known (e.g., Java, Docker, IntelliJ), return the best URL — preferably the official website, trusted package repository (like apt, brew, snap), or GitHub page."
"If the tool is less known, research and return the most relevant and safe-looking link. You may include the GitHub repo, docs, or publisher's page — whichever looks best."
"If the tool name is very unclear, gibberish, or seems unrelated to software (e.g., 'carrot3000'), respond with a short note saying it doesn't appear to be a recognized tool."
"Return only the single most appropriate URL or response."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a developer assistant helping find trusted URLs."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=100
        )

        reply = response.choices[0].message.content.strip()
        # Return the URL directly if it's valid
        if reply.lower().startswith("http"):
            return reply
        return f"No trusted download link found: {reply}"

    except Exception as e:
        logger.error(f"Smart tool URL generation failed: {e}")
        return f"https://www.google.com/search?q=download+{tool_name.replace(' ', '+')}+official"
