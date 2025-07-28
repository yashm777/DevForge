#!/usr/bin/env python3

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
    """Format the result object into a clean, readable string or table"""
    if isinstance(result, dict):
        # Extract the actual message from the result
        if "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            # If it's a plain info dict (like system info), pretty print as table
            if all(isinstance(v, (str, int, float)) for v in inner_result.values()):
                table = Table(show_header=False, box=None)
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
                    return f"✓ {message}" if message else "✓ Operation completed successfully"
                elif status == "error":
                    return f"✗ {message}" if message else "✗ Operation failed"
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
                return f"✓ {message}" if message else "✓ Operation completed successfully"
            elif status == "error":
                return f"✗ {message}" if message else "✗ Operation failed"
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
        try:
            with console.status("[bold yellow]Checking MCP server status..."):
                started, error_message = ensure_server_running()
                if not started:
                    console.print("[red]Failed to start MCP server.[/red]")
                    if error_message:
                        console.print(f"[red]Server error details:[/red]\n{error_message}")
                    return False
                else:
                    console.print("[green]✓ MCP server is running[/green]")
            mcp_client = HTTPMCPClient()
        except Exception as e:
            import traceback
            console.print("[red]Exception while starting MCP server:[/red]")
            console.print(traceback.format_exc())
            return False
    return True


@app.command()
def run(
    command: str = typer.Argument(..., help="Your request in natural language, e.g. 'get me docker', 'remove node', 'what's the python version?', 'set up a dev environment for react'"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file path for code generation (optional)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Run any dev environment or tool management request in natural language."""
    if not setup_instances():
        return
    try:
        parsed = parse_user_command(command)
        if verbose:
            console.print(f"[yellow]Parsed result: {parsed}[/yellow]")
        if "error" in parsed:
            console.print(f"[red]Error parsing command: {parsed['error']}[/red]")
            if "fallback" in parsed:
                console.print(f"[yellow]Suggestion: {parsed['fallback']}[/yellow]")
            return
        action = parsed.get("action") or parsed.get("params", {}).get("task")
        tool_name = parsed.get("tool_name") or parsed.get("params", {}).get("tool_name")
        version = parsed.get("version", "latest") if "version" in parsed else parsed.get("params", {}).get("version", "latest")
        # Handle code generation
        if parsed.get("method") == "generate_code":
            description = parsed["params"].get("description", "")
            code = mcp_client.generate_code(description)
            if code and not code.startswith("[Error]"):
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(code)
                    console.print(f"[green]Code written to {output_file}[/green]")
                else:
                    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                    console.print(Panel(syntax, title="Generated Code", border_style="green"))
            else:
                console.print(f"[red]Code generation failed: {code}[/red]")
            return
        elif action == "install":
            console.print("[cyan]Contacting MCP server for install...[/cyan]")
            result = mcp_client.tool_action(action, tool_name, version)
            result_data = result.get("result", result)
            if verbose:
                console.print(f"[yellow]Debug - Result: {result}[/yellow]")
                console.print(f"[yellow]Debug - Result data: {result_data}[/yellow]")
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
                    console.print("[yellow]Waiting for your selection...[/yellow]")
                    try:
                        choice = int(input("Enter the number of the package you want to install: "))
                        console.print(f"[green]You selected: {choice}[/green]")
                    except (ValueError, KeyboardInterrupt):
                        console.print("[red]Invalid input or cancelled. Aborting.[/red]")
                        return
                    if 1 <= choice <= len(options):
                        selected = options[choice-1]
                        console.print(f"[green]Installing {selected['name']} (ID: {selected['id']})...[/green]")
                        result2 = mcp_client.call_jsonrpc("tool_action_wrapper", {
                            "task": "install_by_id",
                            "tool_name": selected['id'],
                            "version": version
                        })
                        result2_data = result2.get("result", result2)
                        formatted_result = format_result(result2)
                        console.print(Panel(formatted_result, title=f"{action.capitalize()} {selected['name']}", border_style="green"))
                    else:
                        console.print("[red]Invalid selection. Aborting.[/red]")
                        return
                else:
                    console.print("[red]No package options found in ambiguous result.[/red]")
                    return
            else:
                formatted_result = format_result(result)
                console.print(Panel(formatted_result, title=f"{action.capitalize()} {tool_name}", border_style="green"))
        elif action in ("uninstall", "update", "version"):
            result = mcp_client.tool_action(action, tool_name, version)
            formatted_result = format_result(result)
            console.print(Panel(formatted_result, title=f"{action.capitalize()} {tool_name}", border_style="green"))
        elif parsed.get("method") and parsed.get("params") is not None:
            result = mcp_client.call_jsonrpc(parsed["method"], parsed["params"])
            formatted_result = format_result(result)
            console.print(Panel(formatted_result, title=f"{parsed['method']}", border_style="green"))
        else:
            console.print(f"[red]Unknown or unsupported action: {action}[/red]")
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
