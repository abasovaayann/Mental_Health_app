@echo off
REM Delete cache directories
echo Cleaning up cache directories...
if exist ".claude" rmdir /s /q ".claude"
if exist ".codex-run-logs" rmdir /s /q ".codex-run-logs"
echo Done.
