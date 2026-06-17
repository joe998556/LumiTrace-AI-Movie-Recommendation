@echo off
setlocal

if "%LUMITRACE_ALLOWED_PROXY_IP%"=="" (
  echo Please set LUMITRACE_ALLOWED_PROXY_IP to the reverse proxy IP before running.
  echo Example: set LUMITRACE_ALLOWED_PROXY_IP=YOUR_PROXY_IP
  exit /b 1
)

netsh advfirewall firewall add rule name="LumiTrace BERT" protocol=TCP dir=in localport=5001 action=allow remoteip=%LUMITRACE_ALLOWED_PROXY_IP% profile=any
