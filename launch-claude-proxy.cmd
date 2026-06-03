@echo off
setlocal

set "CLAUDE_PROXY=http://127.0.0.1:7897"
set "CLAUDE_NO_PROXY=localhost,127.0.0.1"
set "CLAUDE_WORKDIR=%~dp0"
set "CLAUDE_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\claude.exe"

if not exist "%CLAUDE_EXE%" set "CLAUDE_EXE=claude"

set "PS_COMMON=$env:HTTP_PROXY='%CLAUDE_PROXY%'; $env:HTTPS_PROXY='%CLAUDE_PROXY%'; $env:NO_PROXY='%CLAUDE_NO_PROXY%'; Remove-Item Env:ANTHROPIC_BASE_URL -ErrorAction SilentlyContinue; Remove-Item Env:ANTHROPIC_CUSTOM_HEADERS -ErrorAction SilentlyContinue; Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue; Remove-Item Env:ANTHROPIC_AUTH_TOKEN -ErrorAction SilentlyContinue; Set-Location -LiteralPath '%CLAUDE_WORKDIR%';"

if /I "%~1"=="--test" (
    powershell.exe -ExecutionPolicy Bypass -Command "%PS_COMMON% Write-Host 'Claude proxy test session ready.' -ForegroundColor Green; Write-Host \"HTTP_PROXY=$env:HTTP_PROXY\"; Write-Host \"HTTPS_PROXY=$env:HTTPS_PROXY\"; Write-Host \"NO_PROXY=$env:NO_PROXY\"; Write-Host \"ANTHROPIC_BASE_URL=$env:ANTHROPIC_BASE_URL\"; Write-Host \"ANTHROPIC_CUSTOM_HEADERS=$env:ANTHROPIC_CUSTOM_HEADERS\"; & '%CLAUDE_EXE%' auth status | Out-String -Width 260"
    exit /b %errorlevel%
)

powershell.exe -NoExit -ExecutionPolicy Bypass -Command "%PS_COMMON% $Host.UI.RawUI.WindowTitle = 'Claude Proxy Shell'; Write-Host 'Claude proxy session ready. Only this window uses the proxy.' -ForegroundColor Green; Write-Host 'Anthropic override env vars are cleared in this window.' -ForegroundColor Green; Write-Host 'Claude starts below. Close this window to drop the proxy.' -ForegroundColor Green; & '%CLAUDE_EXE%'"

endlocal