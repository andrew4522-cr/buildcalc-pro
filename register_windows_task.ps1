# Windows Task Scheduler registration for BuildCalc Pro Daily Outreach
# Runs at 08:47 and 11:46 every day

$PythonExe = (Get-Command python).Source
$ScriptPath = "C:\Users\Users\.gemini\antigravity\scratch\app-factory\buildcalc-pro\daily_scheduler.py"
$WorkingDir = "C:\Users\Users\.gemini\antigravity\scratch\app-factory\buildcalc-pro"

# Task 1: Morning 08:47
schtasks /Create /SC DAILY /TN "BuildCalcPro_Outreach_0847" /TR "`"$PythonExe`" `"$ScriptPath`" --run-now" /ST 08:47 /F

# Task 2: Midday 11:46
schtasks /Create /SC DAILY /TN "BuildCalcPro_Outreach_1146" /TR "`"$PythonExe`" `"$ScriptPath`" --run-now" /ST 11:46 /F

Write-Host "BuildCalc Pro Windows Scheduled Tasks successfully created for 08:47 and 11:46 daily!"
