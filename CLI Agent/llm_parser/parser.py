import openai
import json
import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("Please set the OPENAI_API_KEY environment variable.")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Available tools and their schemas
AVAILABLE_TOOLS = {
    "tool_action_wrapper": {
        "description": "Performs actions like install, update, version check, or uninstall on tools.",
        "params": {
            "tool_name": "Name of the tool (e.g., nodejs, docker)",
            "action": "Action to perform (install, update, version, uninstall)",
            "version": "Version to install or update to (optional)"
        }
    }
}

def build_prompt(user_input: str) -> str:
    """Constructs a prompt that guides GPT to generate a valid tool call."""
    tool_docs = json.dumps(AVAILABLE_TOOLS, indent=2)
    return (
        "You are an AI assistant that converts natural language developer requests into structured tool calls.\n\n"
        f"The tools available are defined below in JSON:\n{tool_docs}\n\n"
        "Given the user's instruction, identify the correct tool and return a JSON object with the tool name and parameters.\n"
        "ONLY return valid JSON with no extra explanation.\n\n"
        f"User input: \"{user_input}\""
    )

def parse_user_command(user_input: str) -> dict:
    """Parses user input into a structured tool command."""
    prompt = build_prompt(user_input)
    try:
        logging.debug("Sending prompt to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI command parser."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        raw_response = response.choices[0].message.content.strip()
        logging.debug(f"Raw response: {raw_response}")

        parsed = json.loads(raw_response)
        return parsed

    except json.JSONDecodeError:
        logging.error("Response is not valid JSON.")
        return {"error": "Invalid JSON in model response."}
    except Exception as e:
        logging.exception("Exception occurred while parsing command.")
        return {"error": f"Failed to parse command: {str(e)}"}

def main():
    """Interactive CLI or one-off command mode."""
    try:
        if len(sys.argv) > 1:
            user_input = " ".join(sys.argv[1:])
        else:
            user_input = input("Enter your command: ").strip()

        if not user_input:
            print("No input provided.")
            return

        result = parse_user_command(user_input)
        print("Parsed Output:")
        print(json.dumps(result, indent=2))

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

if __name__ == "__main__":
    main()
