import openai
import json
import sys
import os
import logging
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)

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
    }
}

def build_prompt(user_input: str) -> str:
    """Constructs a prompt that guides GPT to generate a valid tool call."""
    tool_docs = json.dumps(AVAILABLE_TOOLS, indent=2)
    return (
        "You are an AI assistant that converts natural language developer requests into structured tool calls.\n\n"
        f"The tools available are defined below in JSON:\n{tool_docs}\n\n"
        "IMPORTANT: For install, uninstall, update, and version actions, use method 'tool_action_wrapper' with params containing 'task' and 'tool_name'.\n"
        "For system info, use method 'info://server' with empty params.\n"
        "For code generation, use method 'generate_code' with 'description' param.\n\n"
        "Examples:\n"
        "- Install: {'method': 'tool_action_wrapper', 'params': {'task': 'install', 'tool_name': 'docker'}}\n"
        "- Version check: {'method': 'tool_action_wrapper', 'params': {'task': 'version', 'tool_name': 'python'}}\n"
        "- System info: {'method': 'info://server', 'params': {}}\n"
        "- Generate code: {'method': 'generate_code', 'params': {'description': 'hello world function'}}\n\n"
        "Given the user's instruction, identify the correct tool and return a JSON object with the method and params for a JSON-RPC 2.0 call.\n"
        "ONLY return valid JSON with no extra explanation.\n\n"
        f"User input: \"{user_input}\""
    )

def parse_user_command(user_input: str) -> Dict[str, Any]:
    """Parses user input into a structured tool command using OpenAI API."""
    
    # Check for OpenAI API key - required for all parsing
    if not OPENAI_API_KEY:
        return {
            "error": "OpenAI API key not set. Please set OPENAI_API_KEY environment variable.",
            "fallback": "Try using specific commands like 'install docker' or 'check version nodejs'"
        }
    
    # Use OpenAI for parsing
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        prompt = build_prompt(user_input)
        
        logging.debug("Sending prompt to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI command parser. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=200
        )

        raw_response = response.choices[0].message.content.strip()
        logging.debug(f"Raw response: {raw_response}")

        # Clean up the response
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        elif raw_response.startswith("```"):
            raw_response = raw_response[3:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3].strip()
        try:
            return json.loads(raw_response)
        except Exception as e:
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