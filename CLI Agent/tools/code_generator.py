"""
Code Generation Tool

This module provides code generation functionality using OpenAI's GPT-4o model.
It can generate Python code from natural language descriptions.
"""

import os
import openai
from typing import Dict, Any

def generate_code(description: str) -> Dict[str, Any]:
    """
    Generate Python code from a natural language description.
    
    Args:
        description (str): Natural language description of the code to generate
        
    Returns:
        Dict[str, Any]: Dictionary containing status and generated code or error message
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "status": "error", 
            "message": "OPENAI_API_KEY not set. Cannot generate code."
        }
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful coding assistant. Generate only code, no explanation."
                },
                {
                    "role": "user", 
                    "content": f"Write code for: {description}"
                }
            ],
            max_tokens=512,
            temperature=0.2,
        )
        
        generated_code = response.choices[0].message.content.strip()
        
        return {
            "status": "success", 
            "code": generated_code
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Code generation failed: {e}"
        }

def generate_code_with_explanation(description: str) -> Dict[str, Any]:
    """
    Generate Python code with explanation from a natural language description.
    
    Args:
        description (str): Natural language description of the code to generate
        
    Returns:
        Dict[str, Any]: Dictionary containing status, generated code, and explanation
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "status": "error", 
            "message": "OPENAI_API_KEY not set. Cannot generate code."
        }
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful coding assistant. Generate code with a brief explanation."
                },
                {
                    "role": "user", 
                    "content": f"Write code with explanation for: {description}"
                }
            ],
            max_tokens=1024,
            temperature=0.2,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to separate code from explanation
        if "```python" in content:
            parts = content.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0].strip()
                explanation = parts[0].strip()
                if len(parts) > 2:
                    explanation += "\n" + parts[2].split("```")[-1].strip()
            else:
                code_part = content
                explanation = ""
        else:
            code_part = content
            explanation = ""
        
        return {
            "status": "success", 
            "code": code_part,
            "explanation": explanation
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Code generation failed: {e}"
        } 