import sys
import subprocess
import time
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

def format_result(result: Dict[str, Any]) -> str:
    """Format the result object, but passthrough git_setup messages as-is."""
    if isinstance(result, dict):
        # Only passthrough for git-related actions
        git_actions = {"generate_ssh_key", "add_ssh_key", "clone", "check_ssh_key_auth"}
        if result.get("action") in git_actions:
            # Prefer details.message if present
            if "details" in result and isinstance(result["details"], dict):
                msg = result["details"].get("message")
                if msg:
                    return msg
            # Fallback to result.message if present
            if "result" in result and isinstance(result["result"], dict):
                msg = result["result"].get("message")
                if msg:
                    return msg
            # Fallback to top-level message
            msg = result.get("message")
            if msg:
                return msg
            # If nothing found, show a generic message for git actions
            return "No message returned from git operation."
        # --- Default formatting for all other tools ---
        status = result.get("status")
        message = result.get("message", "")
        if status == "success":
            return f"✓ {message}" if message else "✓ Operation completed successfully"
        elif status == "error":
            return f"✗ {message}" if message else "✗ Operation failed"
        elif status == "warning":
            return f"! {message}" if message else "! Warning"
        else:
            return message or str(result)
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
                console.print("[green]✓ MCP server is running[/green]")
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
        parsed = parse_user_command(command)

        if isinstance(parsed, dict) and "error" in parsed:
            console.print(f"[red]Error parsing command: {parsed['error']}[/red]")
            return
            
        # Handle special case when parser returns a manual URL
        if isinstance(parsed, dict) and "manual_url" in parsed and not parsed.get("method"):
            url = parsed["manual_url"]
            console.print(f"[yellow]The tool '{command.split()[1] if len(command.split()) > 1 else command}' requires manual installation.[/yellow]")
            console.print(f"[blue]Please download from: {url}[/blue]")
            return

        if isinstance(parsed, dict):
            parsed = [parsed]

        for i, action_item in enumerate(parsed, start=1):
            method = action_item.get("method")
            params = action_item.get("params", {})

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
                                console.print(Panel(formatted_result, title=f"Install {selected['name']}", border_style="green"))
                            else:
                                console.print("[red]Invalid selection. Aborting.[/red]")
                        except (ValueError, KeyboardInterrupt):
                            console.print("[red]Invalid input or cancelled. Aborting.[/red]")
                    else:
                        console.print("[red]No package options found in ambiguous result.[/red]")
                else:
                    formatted_result = format_result(result)
                    console.print(Panel(formatted_result, title=f"Install {tool_name}", border_style="green"))
                continue
            
            if method == "install_vscode_extension":
                extension_id = params.get("extension_id") or params.get("tool_name")
                result = mcp_client.call_jsonrpc("tool_action_wrapper", {
                    "task": "install_vscode_extension",
                    "extension_id": extension_id
                })
                formatted_result = format_result(result)
                console.print(Panel(formatted_result, title=f"Install VSCode Extension", border_style="green"))
                continue
                
            if method == "uninstall_vscode_extension":
                extension_id = params.get("extension_id") or params.get("tool_name")
                result = mcp_client.call_jsonrpc("uninstall_vscode_extension", {
                    "extension_id": extension_id
                })
                formatted_result = format_result(result)
                console.print(Panel(formatted_result, title=f"Uninstall VSCode Extension", border_style="green"))
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