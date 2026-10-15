@echo off
rem Lo lanza el Programador de tareas cada lunes:
rem   1. renueva el token de Instagram (caduca a los 60 dias si no se renueva)
rem   2. rellena la cola hasta 30 dias y la sube a GitHub
set PYTHONIOENCODING=utf-8
cd /d "%~dp0publicador"
python instagram_login.py renovar >> "%~dp0salida\actualizar_cola.log" 2>&1
cd /d "%~dp0generador"
python generar_cola.py --dias 30 --subir >> "%~dp0salida\actualizar_cola.log" 2>&1
