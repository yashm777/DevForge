# CLI Agent

Hey there! This is a command-line tool that helps you set up and manage your development environment. Think of it as your friendly assistant that handles all the software installation and updates for you.

## What We're Working On

Right now, we're focusing on the first part of the project: making it easy to install, update and check software tools. You can use it to:
- Install new tools (like "Hey, install Node.js for me")
- Update existing tools to newer versions
- Check what versions of tools you have installed

## How It Works

1. You tell the tool what you want to install or update
2. The server figures out what needs to be done
3. The installation tool does the heavy lifting
4. You get a friendly message telling you what happened

For example, if you want to install Docker, the tool will:
- Figure out if you're on Windows, Mac, or Linux
- Use the right package manager (winget, brew, or apt)
- Install it for you
- Let you know when it's done

## Where We Are Now

- The server part is nearly ready It can handle all your installation requests
- It'll work on Windows, Mac, and Linux


## What We Need
- UV - run **uv pip sync requirements.txt**
- fastmcp: The framework that makes our server work

## Supported Systems

This tool works on:
- Windows 10 and 11
- macOS
- Linux (like Ubuntu, Debian, etc.)


Resources used:
1. https://medium.com/@shmilysyg/fastmcp-the-fastway-to-build-mcp-servers-aa14f88536d2
2. https://docs.astral.sh/uv/pip/environments/
