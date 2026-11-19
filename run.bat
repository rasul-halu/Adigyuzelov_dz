@echo off
rem Запуск транслятора в Windows: run.bat < examples\web_server.conf
chcp 65001 > nul
set PYTHONPATH=%~dp0src
python -m confjson %*
