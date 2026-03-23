@echo off

REM -----------------------------
REM  SET YOUR ACTUAL PATHS HERE
REM -----------------------------
SET PROJECT_PATH=C:\Bhavish\license_tracker
SET PYTHON_PATH=C:\Bhavish\license_tracker\venv\Scripts\python.exe

REM -----------------------------
REM  GO TO PROJECT FOLDER
REM -----------------------------
cd /d "%PROJECT_PATH%"

REM -----------------------------
REM  OPTIONAL: SET ENV VARS (UNCOMMENT IF NEEDED)
REM -----------------------------
REM set EMAIL_HOST_USER=yourgmail@gmail.com
REM set EMAIL_HOST_PASSWORD=your_app_password

REM -----------------------------
REM  RUN REMINDER COMMAND USING VENV PYTHON
REM -----------------------------
"%PYTHON_PATH%" manage.py send_reminders --days 7

REM -----------------------------
REM  LOG RESULT (for debugging)
REM -----------------------------
echo %DATE% %TIME% - send_reminders ran >> "%PROJECT_PATH%\reminder_logs.txt"
