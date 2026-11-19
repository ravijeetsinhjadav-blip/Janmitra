@echo off
title JanMitra Assist - Local Database & Storage Viewer
echo ===================================================================
echo             JANMITRA ASSIST - LOCAL DATA VIEWER
echo ===================================================================
echo.
cd /d %~dp0backend
venv\Scripts\python view_data.py
echo.
pause

