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

Should Contain Output
    [Arguments]    ${output}    ${expected}
    Should Contain    ${output}    ${expected}

Should Not Contain Output
    [Arguments]    ${output}    ${not_expected}
    Should Not Contain    ${output}    ${not_expected}

*** Test Cases ***
# --- Basic Functionality ---

System Info Should Work
    ${output}=    Run CLI Agent Command    system info
    Should Contain Output    ${output}    OS

Install Should Succeed
    ${output}=    Run CLI Agent Command    install audacity
    Should Contain Output    ${output}    success

Check Python Version
    ${output}=    Run CLI Agent Command    audacity version
    Should Contain Output    ${output}    audacity

Uninstall Should Succeed
    ${output}=    Run CLI Agent Command    uninstall audacity
    Should Contain Output    ${output}    success

# --- Edge Cases & Error Handling ---

Install Nonexistent Tool Should Fail
    ${output}=    Run CLI Agent Command    install notarealtool123
    Should Contain Output    ${output}    error

Uninstall Nonexistent Tool Should Fail
    ${output}=    Run CLI Agent Command    uninstall notarealtool123
    Should Contain Output    ${output}    error

Ambiguous Install Should Prompt
    ${output}=    Run CLI Agent Command    install java
    Should Contain Output    ${output}    Multiple Packages Found

Install With Version Should Work
    ${output}=    Run CLI Agent Command    install audacity
    Should Contain Output    ${output}    success

Update Tool Should Succeed
    ${output}=    Run CLI Agent Command    update audacity
    Should Contain Output    ${output}    success

Check Version For Nonexistent Tool
    ${output}=    Run CLI Agent Command    notarealtool123 version
    Should Contain Output    ${output}    not installed

# --- Code Generation ---

Generate Code Should Work
    ${output}=    Run CLI Agent Command    generate code for a hello world function
    Should Contain Output    ${output}    def hello_world

# --- Server/Client Robustness ---

Server Logs Should Be Accessible
    ${output}=    Run CLI Agent Command    logs
    Should Contain Output    ${output}    MCP Server Logs

Server Should Handle Invalid Command
    ${output}=    Run CLI Agent Command    do something impossible
    Should Contain Output    ${output}    error

# --- Environment/Config Edge Cases ---

Missing API Key Should Error
    Set Environment Variable    OPENAI_API_KEY    dummy
    ${output}=    Run CLI Agent Command    install audacity
    Should Contain Output    ${output}    API key not set
