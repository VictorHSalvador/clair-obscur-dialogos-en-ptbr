@echo off
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Controle-Legendas.ps1" -Acao Desativar
if errorlevel 1 echo Nao foi possivel concluir. Leia a mensagem acima.
pause
