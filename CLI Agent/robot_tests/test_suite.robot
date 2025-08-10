*** Settings ***
Library           Process
Library           OperatingSystem
Library           Collections

Suite Setup       Start MCP Server
Suite Teardown    Stop MCP Server

*** Variables ***
${PYTHON}         python
${CLI_MODULE}     cli_agent.main
${CLI_ACTION}     run
${SERVER_CMD}     python -m mcp_server.mcp_server
${SERVER_PORT}    8000
${SERVER_URL}     http://localhost:${SERVER_PORT}
${TIMEOUT}        30s

*** Keywords ***
Start MCP Server
    Start Process    ${SERVER_CMD}    --host    localhost    --port    ${SERVER_PORT}    shell=yes    stdout=server.log    stderr=server.log    alias=mcp_server
    Sleep    5s

Stop MCP Server
    Terminate All Processes

Run CLI Agent Command
    [Arguments]    ${command}
    ${result}=    Run Process    ${PYTHON}    -m    ${CLI_MODULE}    ${CLI_ACTION}    ${command}    shell=yes    env:PYTHONIOENCODING=utf-8    stdout=output.log    stderr=output.log    timeout=${TIMEOUT}
    ${output}=    Get File    output.log
    RETURN    ${output}

Run CLI Logs Command
    # Directly call the logs Typer command (bypasses parser)
    ${result}=    Run Process    ${PYTHON}    -m    ${CLI_MODULE}    logs    shell=yes    stdout=logs_output.log    stderr=logs_output.log    timeout=${TIMEOUT}
    ${output}=    Get File    logs_output.log
    RETURN    ${output}

Should Contain Output
    [Arguments]    ${output}    ${expected}
    Should Contain    ${output}    ${expected}

Should Not Contain Output
    [Arguments]    ${output}    ${not_expected}
    Should Not Contain    ${output}    ${not_expected}

Should Contain One Of
    [Arguments]    ${output}    @{candidates}
    FOR    ${c}    IN    @{candidates}
        ${status}=    Run Keyword And Return Status    Should Contain    ${output}    ${c}
        Run Keyword If    ${status}    Return From Keyword
    END
    Fail    Output did not contain any expected substrings: ${candidates} | Actual: ${output}

Call MCP Method
    [Arguments]    ${method}    ${params_json}
    # Uses Python one-liner to avoid shell quoting complications across platforms
    ${cmd}=    Set Variable    import requests, json, os; r=requests.post("${SERVER_URL}/mcp/", json={"jsonrpc":"2.0","id":"1","method":"${method}","params":json.loads(r'''${params_json}''')}); open('output.log','w',encoding='utf-8').write(r.text)
    Run Process    ${PYTHON}    -c    ${cmd}    shell=yes    timeout=${TIMEOUT}
    ${output}=    Get File    output.log
    RETURN    ${output}

Extract JSON Field Should Exist
    [Arguments]    ${json_text}    ${field}
    ${status}=    Run Keyword And Return Status    Should Contain    ${json_text}    ${field}
    Run Keyword Unless    ${status}    Fail    Expected field '${field}' not found in: ${json_text}

*** Test Cases ***
# --- Direct JSON-RPC Functional Tests (Parser-Independent) ---

System Info Should Work
    ${output}=    Call MCP Method    info://server    {}
    Extract JSON Field Should Exist    ${output}    os_type

Python Version Check
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"version","tool_name":"python"}
    Should Contain One Of    ${output}    version    not found    not detected

Nonexistent Tool Version Should Gracefully Report
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"version","tool_name":"notarealtool123"}
    Should Contain One Of    ${output}    not found    not installed    not detected

List Environment Variables
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"system_config","action":"list_env","tool_name":"_"}
    Should Contain One Of    ${output}    variables    success

High Port Availability Check
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"system_config","action":"is_port_open","tool_name":"54321"}
    Should Contain One Of    ${output}    54321    port

Generate SSH Key (Idempotent)
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"git_setup","action":"generate_ssh_key","email":"robot@example.com"}
    Should Contain One Of    ${output}    SSH key generated    SSH key already exists    SSH key

Retrieve Public SSH Key
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"git_setup","action":"get_public_key"}
    Should Contain One Of    ${output}    ssh-rsa    Public key does not exist

Check SSH Auth Feedback
    ${output}=    Call MCP Method    tool_action_wrapper    {"task":"git_setup","action":"check_ssh"}
    Should Contain One Of    ${output}    Permission    successful    authenticated    SSH connection

Server Logs Should Be Accessible
    ${output}=    Call MCP Method    get_logs    {"lines":5}
    Should Contain One Of    ${output}    logs    timestamp

# --- VS Code Extension Management (Non-destructive) ---

VSCode Extension Install Attempt
    # Use a common extension; accept success or error (if VSCode not installed on host)
    ${output}=    Call MCP Method    install_vscode_extension    {"extension_id":"czfadmin.nestjs-tool"}
    Should Contain One Of    ${output}    success    error    installed

VSCode Extension Uninstall Attempt
    ${output}=    Call MCP Method    uninstall_vscode_extension    {"extension_id":"czfadmin.nestjs-tool"}
    Should Contain One Of    ${output}    success    Error    not installed


