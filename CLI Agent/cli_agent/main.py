#!/usr/bin/env python3

import sys
import subprocess
from typing import Dict, Any
from typing import Optional


import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from llm_parser.parser import parse_user_command
from mcp_client.client import HTTPMCPClient

# Initialize Rich console
console = Console()

app = typer.Typer(
    name="cli-agent",
    help="AI-powered development assistant with MCP integration. Just type what you want!",
    add_completion=False
)

# Global HTTP MCP client
mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

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
            # Support multiple actions from LLM by handling both dict and list
            if isinstance(parsed, dict):
                parsed = [parsed]

            for i, command in enumerate(parsed, start=1):
                method = command.get("method")
                params = command.get("params", {})

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
                            console.print(Panel(syntax, title="Generated Code", border_style="green"))
                    else:
                        console.print(f"[red]Code generation failed: {code}[/red]")
                else:
                    result = mcp_client.call_jsonrpc(method, params)
                    formatted_result = format_result(result)
                    console.print(Panel(formatted_result, title=f"Step {i}: {method}", border_style="green"))
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


@app.command()
def check(var: str):
    """
    Check if an environment variable is set.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")
    
    result = mcp_client.system_config(action="check", tool_name=var)
    console.print(Panel(str(result), title="System Config: Check"))


@app.command()
def path_add(path: str):
    """
    Append a directory to the user's PATH.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")
    
    result = mcp_client.system_config(action="append_to_path", tool_name=path)
    console.print(Panel(str(result), title="System Config: PATH Update"))

@app.command()
def check_port(port: int):
    """
    Check if a specific port is open or in use.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="is_port_open", tool_name=str(port))
    console.print(Panel(str(result), title=f"System Config: Port {port}"))


@app.command()
def check_service(service: str):
    """
    Check if a given Windows service is running.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="is_service_running", tool_name=service)
    console.print(Panel(str(result), title=f"System Config: Service '{service}'"))

@app.command()
def set_env(var: str, value: str):
    """
    Set a persistent environment variable on Windows.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="set", tool_name=var, value=value)
    console.print(Panel(str(result), title=f"System Config: Set {var}"))

@app.command()
def remove_env(var: str):
    """
    Remove a persistent environment variable.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="remove_env", tool_name=var)
    console.print(Panel(str(result), title=f"System Config: Remove {var}"))

@app.command()
def list_env():
    """
    List all environment variables.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="list_env", tool_name="")
    console.print(Panel(str(result), title="System Config: All Environment Variables"))

@app.command()
def remove_path(path: str):
    """
    Remove a directory from the PATH variable.
    """
    global mcp_client
    if mcp_client is None:
        mcp_client = HTTPMCPClient(base_url="http://localhost:8000")

    result = mcp_client.system_config(action="remove_from_path", tool_name=path)
    console.print(Panel(str(result), title="System Config: Remove PATH"))





def main():
    """Main entry point"""
    app()

if __name__ == "__main__":
    main() 