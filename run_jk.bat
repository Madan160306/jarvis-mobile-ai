@echo off
cd /d C:\Users\msand\JARVIS-MOBILE-AI
call jarvis-env\Scripts\activate
python -m engine.core.jk_core
pause
