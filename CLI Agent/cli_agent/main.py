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
            if "message" in inner_result:
                return inner_result["message"]
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
        mcp_client = HTTPMCPClient()

@app.command()
def run(
    command: str = typer.Argument(..., help="Your request in natural language, e.g. 'get me docker', 'remove node', 'what's the python version?', 'set up a dev environment for react'"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file path for code generation (optional)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Run any dev environment or tool management request in natural language."""
    setup_instances()
    with console.status("[bold green]Processing your request..."):
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
            elif action == "install":
                result = mcp_client.tool_action(action, tool_name, version)
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
                        choice = typer.prompt("Enter the number of the package you want to install", type=int)
                        if 1 <= choice <= len(options):
                            selected = options[choice-1]
                            console.print(f"[green]Installing {selected['name']} (ID: {selected['id']})...[/green]")
                            # Only use the ID for the next call!
                            result2 = mcp_client.tool_action(action, selected['id'], version)
                            result2_data = result2.get("result", result2)
                            if result2_data.get("status") == "ambiguous":
                                console.print("[red]Still ambiguous after selecting a package. Please specify a more unique package ID or install manually.[/red]")
                                console.print(f"Raw output: {result2_data.get('raw', 'No raw output available')}")
                                return
                            formatted_result = format_result(result2)
                            console.print(Panel(formatted_result, title=f"{action.capitalize()} {selected['name']}", border_style="green"))
                        else:
                            console.print("[red]Invalid selection. Aborting.[/red]")
                            return
                    else:
                        console.print("[red]No package options found in ambiguous result.[/red]")
                        console.print(f"Raw output: {result_data.get('raw', 'No raw output available')}")
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
def server(
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Start the MCP server."""
    console.print(f"[bold green]Starting MCP server on {host}:{port}...[/bold green]")
    try:
        subprocess.run(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            check=True
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting server: {str(e)}[/red]")

def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main() 
