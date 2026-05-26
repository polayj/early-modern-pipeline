@echo off
REM Batch OCR Evaluation - Windows Batch File
REM Double-click this file to run evaluation on all OCR systems

echo ================================================================================
echo BATCH OCR EVALUATION
echo ================================================================================
echo.

cd /d "Z:\OCR Evaluation"

python evaluate_all_ocr_systems.py

echo.
echo Press any key to exit...
pause >nul
