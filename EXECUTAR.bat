@echo off
chcp 65001 >nul
title Coletor de links de grupos de WhatsApp
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python nao encontrado.
  echo  Baixe em https://www.python.org/downloads/  e marque a caixa
  echo  "Add Python to PATH" durante a instalacao.
  echo.
  pause
  exit /b
)

python -c "import requests" >nul 2>nul
if errorlevel 1 (
  echo Instalando a biblioteca necessaria, aguarde...
  python -m pip install requests --quiet
)

python coletor_grupos.py
