#!/usr/bin/env python3

import sys
import subprocess
import time
import os
from typing import Dict, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from llm_parser.parser import parse_user_command
from mcp_client.client import HTTPMCPClient
from tools.utils import ensure_server_running

# Initialize Rich console
console = Console()

app = typer.Typer(
    name="cli-agent",
    help="AI-powered development assistant with MCP integration. Just type what you want!",
    add_completion=False
)

# Global HTTP MCP client
mcp_client = None

def extract_java_version_from_request(command: str) -> str:
    """Extract Java version number from user request"""
    import re
    # Look for patterns like "java 17", "java 11", "jdk 21", etc.
    version_patterns = [
        r'java\s+(\d+)',
        r'jdk\s+(\d+)', 
        r'openjdk\s+(\d+)',
        r'version\s+(\d+)',
        r'to\s+(\d+)'
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None

def check_java_version_installed(version: str) -> bool:
    """Check if a specific Java version is installed on Mac"""
    try:
        import subprocess
        import os
        # Check if the specific Java version directory exists
        java_path = f"/opt/homebrew/Cellar/openjdk@{version}"
        return os.path.exists(java_path)
    except:
        return False

def get_active_java_version() -> str:
    """Get the currently active Java version by running java -version"""
    try:
        import subprocess
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            # Java version info goes to stderr
            output = result.stderr
            # Parse the output to extract version
            import re
            # Look for patterns like "17.0.16" or "21.0.8"
            version_match = re.search(r'"(\d+)\.', output)
            if version_match:
                return version_match.group(1)
            # Try alternative pattern
            version_match = re.search(r'version "(\d+)', output)
            if version_match:
                return version_match.group(1)
        return "unknown"
    except:
        return "unknown"

def get_display_name(tool_name: str) -> str:
    """Convert Linux package names back to user-friendly names for display"""
    display_mapping = {
        "default-jdk": "java",
        "docker.io": "docker", 
        "python3": "python",
        "nodejs": "node",
        "golang": "go",  # LLM transforms go -> golang, but show as go
        "intellij-idea-community": "intellij",
        "pycharm-community": "pycharm",
    }
    return display_mapping.get(tool_name, tool_name)

def format_result(result: Dict[str, Any], is_mac_java_check: bool = False) -> str:
    """Format the result object into a clean, readable string or table"""
    if isinstance(result, dict):
        # Extract the actual message from the result
        if "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            # If it's a plain info dict (like system info), pretty print as table
            if all(isinstance(v, (str, int, float)) for v in inner_result.values()):
                # Check if this is a Mac Java case and we want clean status only
                if is_mac_java_check:
                    status = inner_result.get("status", "success")
                    message = inner_result.get("message", "")
                    if message and "Next steps:" in message:
                        clean_message = message.split("Next steps:")[0].strip()
                        return f"{clean_message}" if clean_message else "Java installation completed successfully"
                    return f"{message}" if message else "Operation completed successfully"
                
                table = Table(show_header=False, box=None, width=None)
                for k, v in inner_result.items():
                    table.add_row(f"[bold]{k}[/bold]", str(v))
                return table
            # --- Updated error extraction logic ---
            if "message" in inner_result:
                return inner_result["message"]
            elif "details" in inner_result and isinstance(inner_result["details"], dict):
                details = inner_result["details"]
                if "message" in details:
                    return details["message"]
                elif "status" in details:
                    status = details["status"]
                    message = details.get("message", "")
                    if status == "success":
                        return f"✓ {message}" if message else "✓ Operation completed successfully"
                    elif status == "error":
                        return f"✗ {message}" if message else "✗ Operation failed"
                    else:
                        return message
                else:
                    return str(details)
            elif "status" in inner_result:
                status = inner_result["status"]
                message = inner_result.get("message", "")
                if status == "success":
                    return f"{message}" if message else "Operation completed successfully"
                elif status == "error":
                    return f"Error: {message}" if message else "Operation failed"
                else:
                    return message
            else:
                return str(inner_result)
        elif "message" in result:
            return result["message"]
        elif "status" in result:
            status = result["status"]
            message = result.get("message", "")
            if status == "success":
                return f"{message}" if message else "Operation completed successfully"
            elif status == "error":
                return f"Error: {message}" if message else "Operation failed"
            else:
                return message
        else:
            return str(result)
    else:
        return str(result)


def setup_instances():
    """Initialize global instances"""
    global mcp_client
    if mcp_client is None:
        # Ensure MCP server is running before creating client
        with console.status("[bold yellow]Checking MCP server status..."):
            started = ensure_server_running()
            if not started:
                console.print("[red]Failed to start MCP server. See error output above for details.[/red]")
                return False
            else:
                console.print("[green]MCP server is running[/green]")
        mcp_client = HTTPMCPClient()
    return True


@app.command()
def run(
    command: str = typer.Argument(..., help="Your request in natural language, e.g. 'get me docker', 'remove node', 'what's the python version?', 'set up a dev environment for react'"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file path for code generation (optional)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    if not setup_instances():
        return

    try:
        # Check if this is a Mac Java version request or verification
        requested_java_version = None
        is_mac_system = sys.platform == "darwin"
        is_switch_command = "switch" in command.lower()
        is_version_check = any(phrase in command.lower() for phrase in ["java version", "what java", "current java", "active java"])
        
        # Handle Java version checking
        if is_mac_system and is_version_check:
            active_version = get_active_java_version()
            if active_version != "unknown":
                console.print(Panel(f"Currently active Java version: {active_version}", title="Java Version Check", border_style="blue"))
                return
            else:
                console.print(Panel("Java not found or not configured", title="Java Version Check", border_style="red"))
                return
        
        if is_mac_system and ("java" in command.lower() or "jdk" in command.lower()):
            requested_java_version = extract_java_version_from_request(command)
            
            # If a specific version is requested and not installed, install it first
            if requested_java_version and not check_java_version_installed(requested_java_version):
                console.print(f"[yellow]Java {requested_java_version} is not installed. Installing it first...[/yellow]")
                
                # Install the specific Java version
                install_result = mcp_client.tool_action("install", f"openjdk@{requested_java_version}", "latest")
                if install_result.get("result", {}).get("status") == "success":
                    console.print(f"[green]Java {requested_java_version} installed successfully[/green]")
                else:
                    console.print(f"[red]Failed to install Java {requested_java_version}[/red]")
                    return
            elif requested_java_version and is_switch_command and check_java_version_installed(requested_java_version):
                # For switch commands with already installed versions, trigger the switching logic
                console.print(f"[green]Java {requested_java_version} is already installed. Switching to it...[/green]")
                
                # Create a simulated result that will trigger our Mac Java detection
                java_home_path = f"/opt/homebrew/Cellar/openjdk@{requested_java_version}"
                # Find the actual version directory
                try:
                    import os
                    version_dirs = [d for d in os.listdir(java_home_path) if os.path.isdir(os.path.join(java_home_path, d))]
                    if version_dirs:
                        actual_version = version_dirs[0]  # Take the first (and usually only) version directory
                        full_java_home = f"{java_home_path}/{actual_version}/libexec/openjdk.jdk/Contents/Home"
                        
                        # Trigger the Mac Java configuration update directly
                        console.print(Panel(f"Switching to Java {requested_java_version}", title=f"Java Version Switch", border_style="green"))
                        console.print(f"\n[bold cyan]Updating shell configuration automatically...[/bold cyan]")
                        
                        try:
                            # Comment out old Java configuration  
                            subprocess.run([
                                'sed', '-i', '', 
                                's/^export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/# Java 24 (old) - export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/',
                                os.path.expanduser('~/.zshrc')
                            ], check=True, capture_output=True)
                            
                            subprocess.run([
                                'sed', '-i', '',
                                's/^export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/',
                                os.path.expanduser('~/.zshrc')
                            ], check=True, capture_output=True)
                            
                            # Add Java configuration
                            with open(os.path.expanduser('~/.zshrc'), 'a') as f:
                                f.write(f'\n# Java {requested_java_version} (current)\n')
                                f.write(f'export JAVA_HOME={full_java_home}\n')
                                f.write(f'export PATH="{full_java_home}/bin:$PATH"\n')
                            
                            console.print("Shell configuration updated successfully")
                            console.print(f"\n[bold yellow]Final step - Copy and run this command:[/bold yellow]")
                            print(f"\033[32msource ~/.zshrc\033[0m")
                            
                            # Add verification instructions
                            console.print(f"\n[bold cyan]After running source, verify with:[/bold cyan]")
                            print(f"\033[36mjava -version\033[0m")
                            console.print(f"[dim]Expected: OpenJDK {requested_java_version}[/dim]")
                            console.print("")
                            return  # Exit early since we handled the switch
                            
                        except Exception as e:
                            console.print(f"[red]Error updating shell configuration: {e}[/red]")
                            # Fall through to normal processing
                            
                except Exception as e:
                    console.print(f"[yellow]Could not auto-switch. Proceeding with normal command processing...[/yellow]")
        
        parsed = parse_user_command(command)

        if isinstance(parsed, dict) and "error" in parsed:
            console.print(f"[red]Error parsing command: {parsed['error']}[/red]")
            return

        if isinstance(parsed, dict):
            parsed = [parsed]

        for i, action_item in enumerate(parsed, start=1):
            method = action_item.get("method")
            params = action_item.get("params", {})

            console.print(f"[cyan]Executing Step {i}: {method}[/cyan]")

            # Special case for installs
            if params.get("task") == "install":
                tool_name = params.get("tool_name")
                version = params.get("version", "latest")

                console.print("[cyan]Contacting MCP server for install...[/cyan]")
                result = mcp_client.tool_action("install", tool_name, version)
                result_data = result.get("result", result)

                if result_data.get("status") == "ambiguous":
                    options = result_data.get("options", [])
                    if options:
                        table = Table(title="Multiple Packages Found", show_lines=True)
                        table.add_column("No.", style="cyan", justify="right")
                        table.add_column("Name", style="bold")
                        table.add_column("ID")
                        table.add_column("Source")
                        for idx, opt in enumerate(options, 1):
                            table.add_row(str(idx), opt["name"], opt["id"], opt["source"])
                        console.print(table)

                        try:
                            choice = int(input("Enter the number of the package you want to install: "))
                            if 1 <= choice <= len(options):
                                selected = options[choice - 1]
                                console.print(f"[green]Installing {selected['name']} (ID: {selected['id']})...[/green]")
                                result2 = mcp_client.call_jsonrpc("tool_action_wrapper", {
                                    "task": "install_by_id",
                                    "tool_name": selected['id'],
                                    "version": version
                                })
                                formatted_result = format_result(result2)
                                display_name = get_display_name(selected['name'])
                                
                                # Check if this is a Mac-specific result with JAVA_HOME path
                                is_mac_java = False
                                java_home_path = None
                                if isinstance(result2, dict) and "result" in result2:
                                    inner_result = result2["result"]
                                    if isinstance(inner_result, dict):
                                        for k, v in inner_result.items():
                                            if isinstance(v, str) and 'JAVA_HOME=' in v and '/opt/homebrew/' in v:
                                                # This is Mac-specific (homebrew path)
                                                is_mac_java = True
                                                import re
                                                match = re.search(r'JAVA_HOME=([^\s\n]+)', v)
                                                if match:
                                                    java_home_path = match.group(1)
                                                break
                                
                                if is_mac_java and java_home_path:
                                    # For Mac Java installs, show clean status and separate commands
                                    status_msg = inner_result.get("status", "success")
                                    main_msg = inner_result.get("message", "")
                                    if main_msg:
                                        clean_status = f"{main_msg.split('Next steps:')[0].strip()}"
                                    else:
                                        clean_status = "Java installation completed successfully"
                                    
                                    console.print(Panel(clean_status, title=f"Step {i}: Install {display_name}", border_style="green"))
                                    
                                    # Automatically update the zshrc file
                                    console.print(f"\n[bold cyan]� Updating shell configuration automatically...[/bold cyan]")
                                    
                                    try:
                                        # Comment out old Java configuration
                                        subprocess.run([
                                            'sed', '-i', '', 
                                            's/^export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/# Java 24 (old) - export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/',
                                            os.path.expanduser('~/.zshrc')
                                        ], check=True, capture_output=True)
                                        
                                        subprocess.run([
                                            'sed', '-i', '',
                                            's/^export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/',
                                            os.path.expanduser('~/.zshrc')
                                        ], check=True, capture_output=True)
                                        
                                        # Add Java configuration with dynamic version detection
                                        with open(os.path.expanduser('~/.zshrc'), 'a') as f:
                                            # Extract version number from java_home_path for labeling
                                            import re
                                            version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                                            version_label = version_match.group(1) if version_match else "current"
                                            
                                            f.write(f'\n# Java {version_label} (current)\n')
                                            f.write(f'export JAVA_HOME={java_home_path}\n')
                                            f.write(f'export PATH="{java_home_path}/bin:$PATH"\n')
                                        
                                        console.print("Shell configuration updated successfully")
                                        console.print(f"\n[bold yellow]Final step - Copy and run this command:[/bold yellow]")
                                        print(f"\033[32msource ~/.zshrc\033[0m")
                                        console.print("")
                                        
                                    except Exception as e:
                                        console.print(f"[red]Error updating shell configuration: {e}[/red]")
                                        console.print(f"\n[bold cyan]Please run these commands manually:[/bold cyan]")
                                        
                                        # Extract version for manual commands
                                        import re
                                        version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                                        version_label = version_match.group(1) if version_match else "current"
                                        
                                        print(f"\033[32m# Comment out old Java configuration\033[0m")
                                        print(f"\033[32msed -i '' 's/^export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/# Java 24 (old) - export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/' ~/.zshrc\033[0m")
                                        print(f"\033[32msed -i '' 's/^export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/' ~/.zshrc\033[0m")
                                        print(f"\033[32m# Add Java {version_label} configuration\033[0m")
                                        print(f"\033[32mecho '# Java {version_label} (current)' >> ~/.zshrc\033[0m")
                                        print(f"\033[32mecho 'export JAVA_HOME={java_home_path}' >> ~/.zshrc\033[0m")
                                        print(f"\033[32mecho 'export PATH=\"{java_home_path}/bin:$PATH\"' >> ~/.zshrc\033[0m")
                                        print(f"\033[32msource ~/.zshrc\033[0m")
                                        console.print("")
                                else:
                                    # Default behavior for non-Mac or non-Java installs
                                    console.print(Panel(formatted_result, title=f"Step {i}: Install {display_name}", border_style="green"))

                            else:
                                console.print("[red]Invalid selection. Aborting.[/red]")
                        except (ValueError, KeyboardInterrupt):
                            console.print("[red]Invalid input or cancelled. Aborting.[/red]")
                    else:
                        console.print("[red]No package options found in ambiguous result.[/red]")
                else:
                    formatted_result = format_result(result)
                    display_name = get_display_name(tool_name)
                    
                    # Check if this is a Mac Java installation (simple detection)
                    is_mac_java = (tool_name in ["java", "default-jdk"] and 
                                 isinstance(result, dict) and "result" in result and
                                 isinstance(result["result"], dict) and
                                 any('/opt/homebrew/' in str(v) for v in result["result"].values()))
                    
                    if is_mac_java:
                        # Extract JAVA_HOME path for Mac
                        java_home_path = None
                        for k, v in result["result"].items():
                            if isinstance(v, str) and '/opt/homebrew/Cellar/openjdk' in v:
                                import re
                                # Extract the full path to openjdk.jdk/Contents/Home
                                match = re.search(r'/opt/homebrew/Cellar/openjdk@?\d*/[^/\s]+/libexec/openjdk\.jdk/Contents/Home', v)
                                if match:
                                    java_home_path = match.group(0)
                                    break
                        
                        if java_home_path:
                            # For Mac Java installs, show clean status and separate commands
                            clean_status = format_result(result, is_mac_java_check=True)
                            console.print(Panel(clean_status, title=f"Step {i}: Install {display_name}", border_style="green"))
                            
                            # Automatically update the zshrc file
                            console.print(f"\n[bold cyan]� Updating shell configuration automatically...[/bold cyan]")
                            
                            try:
                                # Comment out old Java configuration
                                subprocess.run([
                                    'sed', '-i', '', 
                                    's/^export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/# Java 24 (old) - export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/',
                                    os.path.expanduser('~/.zshrc')
                                ], check=True, capture_output=True)
                                
                                subprocess.run([
                                    'sed', '-i', '',
                                    's/^export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/',
                                    os.path.expanduser('~/.zshrc')
                                ], check=True, capture_output=True)
                                
                                # Add Java configuration with dynamic version detection
                                with open(os.path.expanduser('~/.zshrc'), 'a') as f:
                                    # Extract version number from java_home_path for labeling
                                    import re
                                    version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                                    version_label = version_match.group(1) if version_match else "current"
                                    
                                    f.write(f'\n# Java {version_label} (current)\n')
                                    f.write(f'export JAVA_HOME={java_home_path}\n')
                                    f.write(f'export PATH="{java_home_path}/bin:$PATH"\n')
                                
                                console.print("Shell configuration updated successfully")
                                console.print(f"\n[bold yellow]Final step - Copy and run this command:[/bold yellow]")
                                print(f"\033[32msource ~/.zshrc\033[0m")
                                console.print("")
                                
                            except Exception as e:
                                console.print(f"[red]Error updating shell configuration: {e}[/red]")
                                console.print(f"\n[bold cyan]Please run these commands manually:[/bold cyan]")
                                
                                # Extract version for manual commands
                                import re
                                version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                                version_label = version_match.group(1) if version_match else "current"
                                
                                print(f"\033[32m# Comment out old Java configuration\033[0m")
                                print(f"\033[32msed -i '' 's/^export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/# Java 24 (old) - export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/' ~/.zshrc\033[0m")
                                print(f"\033[32msed -i '' 's/^export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/' ~/.zshrc\033[0m")
                                print(f"\033[32m# Add Java {version_label} configuration\033[0m")
                                print(f"\033[32mecho '# Java {version_label} (current)' >> ~/.zshrc\033[0m")
                                print(f"\033[32mecho 'export JAVA_HOME={java_home_path}' >> ~/.zshrc\033[0m")
                                print(f"\033[32mecho 'export PATH=\"{java_home_path}/bin:$PATH\"' >> ~/.zshrc\033[0m")
                                print(f"\033[32msource ~/.zshrc\033[0m")
                                console.print("")
                        else:
                            # Fallback to default display
                            console.print(Panel(formatted_result, title=f"Step {i}: Install {display_name}", border_style="green"))
                    else:
                        # Default behavior for non-Mac or non-Java installs
                        console.print(Panel(formatted_result, title=f"Step {i}: Install {display_name}", border_style="green"))

                continue

            # Code generation case
            if method == "generate_code":
                description = params.get("description", "")
                code = mcp_client.generate_code(description)
                if code and not code.startswith("[Error]"):
                    if output_file:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(code)
                        console.print(f"[green]Code written to {output_file}[/green]")
                    else:
                        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                        console.print(Panel(syntax, title=f"Generated Code (Step {i})", border_style="green"))
                else:
                    console.print(f"[red]Code generation failed: {code}[/red]")
                continue

            # Default for all other tasks
            result = mcp_client.call_jsonrpc(method, params)
            formatted_result = format_result(result)
            
            # Check if this is a Mac Java upgrade/install
            is_mac_java = (isinstance(result, dict) and "result" in result and
                         isinstance(result["result"], dict) and
                         any('/opt/homebrew/' in str(v) and 'openjdk' in str(v) for v in result["result"].values()))
            
            if is_mac_java:
                # Extract JAVA_HOME path for Mac
                java_home_path = None
                for k, v in result["result"].items():
                    if isinstance(v, str) and '/opt/homebrew/Cellar/openjdk' in v:
                        import re
                        # Extract the full path to openjdk.jdk/Contents/Home
                        match = re.search(r'/opt/homebrew/Cellar/openjdk@?\d*/[^/\s]+/libexec/openjdk\.jdk/Contents/Home', v)
                        if match:
                            java_home_path = match.group(0)
                            break
                
                if java_home_path:
                    # For Mac Java operations, show clean status and separate commands
                    clean_status = format_result(result, is_mac_java_check=True)
                    console.print(Panel(clean_status, title=f"Step {i}: {method}", border_style="green"))
                    
                    # Automatically update the zshrc file
                    console.print(f"\n[bold cyan]� Updating shell configuration automatically...[/bold cyan]")
                    
                    try:
                        # Comment out old Java configuration
                        subprocess.run([
                            'sed', '-i', '', 
                            's/^export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/# Java 24 (old) - export JAVA_HOME="\\/opt\\/homebrew\\/opt\\/openjdk"/',
                            os.path.expanduser('~/.zshrc')
                        ], check=True, capture_output=True)
                        
                        subprocess.run([
                            'sed', '-i', '',
                            's/^export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH="\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/',
                            os.path.expanduser('~/.zshrc')
                        ], check=True, capture_output=True)
                        
                        # Add Java configuration with dynamic version detection
                        with open(os.path.expanduser('~/.zshrc'), 'a') as f:
                            # Extract version number from java_home_path for labeling
                            import re
                            version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                            version_label = version_match.group(1) if version_match else "current"
                            
                            f.write(f'\n# Java {version_label} (current)\n')
                            f.write(f'export JAVA_HOME={java_home_path}\n')
                            f.write(f'export PATH="{java_home_path}/bin:$PATH"\n')
                        
                        console.print("Shell configuration updated successfully")
                        console.print(f"\n[bold yellow]Final step - Copy and run this command:[/bold yellow]")
                        print(f"\033[32msource ~/.zshrc\033[0m")
                        console.print("")
                        
                    except Exception as e:
                        console.print(f"[red]Error updating shell configuration: {e}[/red]")
                        console.print(f"\n[bold cyan]Please run these commands manually:[/bold cyan]")
                        
                        # Extract version for manual commands
                        import re
                        version_match = re.search(r'openjdk@?(\d+)', java_home_path)
                        version_label = version_match.group(1) if version_match else "current"
                        
                        print(f"\033[32m# Comment out old Java configuration\033[0m")
                        print(f"\033[32msed -i '' 's/^export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/# Java 24 (old) - export JAVA_HOME=\"\\/opt\\/homebrew\\/opt\\/openjdk\"/' ~/.zshrc\033[0m")
                        print(f"\033[32msed -i '' 's/^export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/# Java 24 (old) - export PATH=\"\\/opt\\/homebrew\\/opt\\/openjdk\\/bin:/' ~/.zshrc\033[0m")
                        print(f"\033[32m# Add Java {version_label} configuration\033[0m")
                        print(f"\033[32mecho '# Java {version_label} (current)' >> ~/.zshrc\033[0m")
                        print(f"\033[32mecho 'export JAVA_HOME={java_home_path}' >> ~/.zshrc\033[0m")
                        print(f"\033[32mecho 'export PATH=\"{java_home_path}/bin:$PATH\"' >> ~/.zshrc\033[0m")
                        print(f"\033[32msource ~/.zshrc\033[0m")
                        print(f"\033[32msource ~/.zshrc\033[0m")
                        console.print("")
                else:
                    # Fallback to default display
                    console.print(Panel(formatted_result, title=f"Step {i}: {method}", border_style="green"))
            else:
                # Default behavior for non-Mac or non-Java operations
                console.print(Panel(formatted_result, title=f"Step {i}: {method}", border_style="green"))


    except Exception as e:
        console.print(f"[red]Error executing command: {str(e)}[/red]")



@app.command()
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="Number of log lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output in real-time"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Show MCP server logs."""
    if not setup_instances():
        return
    try:
        # Check if server is running
        if not ensure_server_running():
            console.print("[red]MCP server is not running. Start it first with a command like 'install docker'.[/red]")
            return
        
        console.print(f"[bold green]Retrieving last {lines} lines of MCP server logs...[/bold green]")
        
        # Get actual server logs
        result = mcp_client.get_server_logs(lines)
        if "error" in result:
            console.print(f"[red]Error retrieving logs: {result['error']}[/red]")
            return
        
        logs_data = result.get("result", {}).get("logs", [])
        if not logs_data:
            console.print("[yellow]No logs available yet. Try running a command first.[/yellow]")
            return
        
        # Display logs in a nice format
        table = Table(title=f"MCP Server Logs (Last {len(logs_data)} entries)", show_lines=True)
        table.add_column("Timestamp", style="cyan")
        table.add_column("Level", style="bold")
        table.add_column("Message", style="white")
        
        for log_entry in logs_data:
            level_style = "green" if log_entry.get("level") == "INFO" else "red"
            table.add_row(
                log_entry.get("timestamp", ""),
                f"[{level_style}]{log_entry.get('level', '')}[/{level_style}]",
                log_entry.get("message", "")
            )
        
        console.print(table)
        
        if follow:
            console.print("[yellow]Follow mode: Press Ctrl+C to stop following logs[/yellow]")
            try:
                last_log_count = len(logs_data)
                while True:
                    time.sleep(2)
                    # Check for new logs
                    new_result = mcp_client.get_server_logs(lines)
                    if "error" not in new_result:
                        new_logs = new_result.get("result", {}).get("logs", [])
                        if len(new_logs) > last_log_count:
                            # Show only new entries
                            new_entries = new_logs[last_log_count:]
                            for entry in new_entries:
                                level_style = "green" if entry.get("level") == "INFO" else "red"
                                console.print(f"[{entry.get('timestamp', '')}] [{level_style}]{entry.get('level', '')}[/{level_style}] {entry.get('message', '')}")
                            last_log_count = len(new_logs)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped following logs[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error accessing logs: {str(e)}[/red]")

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main()

