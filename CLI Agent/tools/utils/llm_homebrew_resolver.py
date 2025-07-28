"""
Simple Tool Name Resolver

This file helps us find the correct package name for Homebrew.
When someone wants to install "vscode", we need to know it's actually called "visual-studio-code" in Homebrew.

This is like a translator that speaks to an AI to find the right name.

How it works:
1. User says: "I want to install cursor"
2. We ask the AI: "What is cursor called in Homebrew?"
3. AI says: "It's called cursor and it's a cask"
4. We tell Homebrew: "Install cursor as a cask"
"""

import json
import logging
import os
import openai
from dotenv import load_dotenv

# Load our secret API key
load_dotenv()

# Set up logging so we can see what's happening
logger = logging.getLogger(__name__)

# Get our AI key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def find_homebrew_package(tool_name, version="latest", operation="install"):
    """
    Ask the AI to find the correct Homebrew package name.
    
    This is like asking a smart friend: "What is this tool called in Homebrew?"
    
    Args:
        tool_name: The name the user gave us (like "vscode")
        version: What version they want (usually "latest")
        operation: What they want to do ("install", "uninstall", etc.)
    
    Returns:
        A dictionary with:
        - status: "success" if we found it, "error" if we didn't
        - package: The real Homebrew name
        - is_cask: True if it's a GUI app, False if it's a command line tool
        - confidence: How sure the AI is (0.0 to 1.0)
    """
    logger.info(f"Looking for: {tool_name} (version: {version}, operation: {operation})")
    
    # Check if we have our AI key
    if not OPENAI_API_KEY:
        logger.warning("No AI key available")
        return {
            "status": "error", 
            "message": "AI key not set up",
            "original_tool": tool_name
        }
    
    try:
        # Create our AI client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Create a simple question for the AI
        question = create_simple_question(tool_name, version, operation)
        
        # Ask the AI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You help find correct Homebrew package names. Always return valid JSON."
                },
                {"role": "user", "content": question}
            ],
            temperature=0.1,  # Keep answers consistent
            max_tokens=200
        )
        
        # Process the AI's answer
        return process_ai_answer(response, tool_name, operation)
        
    except json.JSONDecodeError as e:
        logger.error(f"AI gave us bad JSON: {e}")
        return {
            "status": "error",
            "message": f"AI response was not valid JSON: {str(e)}",
            "original_tool": tool_name
        }
    except Exception as e:
        logger.error(f"Something went wrong with AI: {e}")
        return {
            "status": "error",
            "message": f"AI request failed: {str(e)}",
            "original_tool": tool_name
        }

def create_simple_question(tool_name, version, operation):
    """
    Create a simple question to ask the AI.
    
    This turns our request into a clear question the AI can understand.
    """
    if operation == "install":
        question = f"""
I want to install "{tool_name}" on macOS using Homebrew.

Please tell me:
1. What is the most recommended Homebrew package name?
2. Alternative package names if they exist (especially for tools like Java which might be openjdk, openjdk@21, default-jdk, etc.)
3. Is it a cask (GUI app) or formula (command line tool)?
4. How confident are you? (0.0 to 1.0)

Return your answer as JSON like this:
{{
    "package": "most-recommended-name",
    "alternatives": ["alternative-name-1", "alternative-name-2"],
    "is_cask": true or false,
    "confidence": 0.95
}}

Examples:
- For "java": might be "openjdk", with alternatives like ["openjdk@21", "openjdk@17", "default-jdk"]
- For "node": might be "node", with alternatives like ["node@18", "node@20"]

Tool name: {tool_name}
Version needed: {version}
"""
    elif operation == "uninstall":
        question = f"""
I want to uninstall "{tool_name}" on macOS using Homebrew.

What is the exact Homebrew package name I should uninstall?
Is it a cask or formula?

Return JSON:
{{
    "package": "exact-homebrew-name",
    "is_cask": true or false,
    "confidence": 0.95
}}

Tool name: {tool_name}
"""
    elif operation == "upgrade":
        question = f"""
I want to upgrade "{tool_name}" on macOS using Homebrew.

What is the most likely Homebrew package name and any alternatives?
Is it a cask or formula?

Return JSON:
{{
    "package": "most-likely-name",
    "alternatives": ["alternative-name-1", "alternative-name-2"],
    "is_cask": true or false,
    "confidence": 0.95
}}

Examples:
- For "java": might be "openjdk", with alternatives like ["openjdk@21", "openjdk@17", "default-jdk"]

Tool name: {tool_name}
Version target: {version}
"""
    else:  # version check
        question = f"""
I want to check the version of "{tool_name}" on macOS using Homebrew.

For version checking, I need to find what's actually installed on the system. Some tools have multiple possible package names.

Please provide:
1. The most likely Homebrew package name
2. Alternative package names if they exist (especially for tools like Java which might be openjdk, openjdk@21, default-jdk, etc.)
3. Whether it's a cask or formula
4. Your confidence level

Return JSON:
{{
    "package": "most-likely-name",
    "alternatives": ["alternative-name-1", "alternative-name-2"],
    "is_cask": true or false,
    "confidence": 0.95
}}

Examples:
- For "java": might be "openjdk", with alternatives like ["openjdk@21", "openjdk@17", "openjdk@11", "default-jdk"]
- For "node": might be "node", with alternatives like ["node@18", "node@20"]
- For "python": might be "python3", with alternatives like ["python@3.11", "python@3.12"]

Tool name: {tool_name}
"""
    
    return question

def process_ai_answer(response, tool_name, operation):
    """
    Take the AI's answer and turn it into something we can use.
    
    The AI gives us text, we need to extract the useful information.
    """
    try:
        # Get the AI's answer
        ai_text = response.choices[0].message.content.strip()
        logger.info(f"AI said: {ai_text}")
        
        # Try to find JSON in the AI's answer
        json_start = ai_text.find('{')
        json_end = ai_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in AI response")
        
        json_text = ai_text[json_start:json_end]
        ai_answer = json.loads(json_text)
        
        # Make sure the AI gave us what we need
        required_fields = ["package", "is_cask", "confidence"]
        for field in required_fields:
            if field not in ai_answer:
                raise ValueError(f"AI didn't provide {field}")
        
        # Handle alternatives field (optional for version checks)
        alternatives = ai_answer.get("alternatives", [])
        if not isinstance(alternatives, list):
            alternatives = []
        
        # Check if the AI is confident enough
        confidence = float(ai_answer["confidence"])
        if confidence < 0.7:
            logger.warning(f"AI is not very confident: {confidence}")
        
        # Return the processed answer
        result = {
            "status": "success",
            "package": ai_answer["package"],
            "is_cask": bool(ai_answer["is_cask"]),
            "confidence": confidence,
            "original_tool": tool_name,
            "operation": operation
        }
        
        # Add alternatives if they exist (mainly for version checks)
        if alternatives:
            result["alternatives"] = alternatives
            
        return result
        
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"Could not understand AI answer: {e}")
        return {
            "status": "error",
            "message": f"AI gave unclear answer: {str(e)}",
            "original_tool": tool_name
        }

# Specific functions for each operation
# These are just simple wrappers that call the main function

def resolve_for_install(tool_name, version="latest"):
    """Ask AI how to install this tool"""
    return find_homebrew_package(tool_name, version, "install")

def resolve_for_uninstall(tool_name):
    """Ask AI how to uninstall this tool"""
    return find_homebrew_package(tool_name, "latest", "uninstall")

def resolve_for_upgrade(tool_name, version="latest"):
    """Ask AI how to upgrade this tool"""
    return find_homebrew_package(tool_name, version, "upgrade")

def resolve_for_version_check(tool_name):
    """Ask AI how to check version of this tool"""
    return find_homebrew_package(tool_name, "latest", "check")

def enhance_package_with_version(package_name, version):
    """
    Add version to package name if needed.
    
    Some packages need version numbers in their name.
    This function adds them if the version is not "latest".
    """
    if version == "latest" or not version:
        return package_name
    
    # If version is already in the name, don't add it again
    if version in package_name:
        return package_name
    
    # Add version with @ symbol (Homebrew style)
    return f"{package_name}@{version}"
