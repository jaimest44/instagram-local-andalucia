@echo off
rem Rellena la cola hasta 30 dias y la sube a GitHub. Lo lanza el Programador de tareas cada lunes.
rem Renueva el token de Instagram (caduca a los 60 dias si no se renueva)
cd /d "%~dp0publicador"
python instagram_login.py renovar >> "%~dp0salidactualizar_cola.log" 2>&1
cd /d "%~dp0generador"
set PYTHONIOENCODING=utf-8
python generar_cola.py --dias 30 --subir >> "%~dp0salida\actualizar_cola.log" 2>&1
