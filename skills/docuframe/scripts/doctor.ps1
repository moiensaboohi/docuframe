# Check this machine for docuframe. Windows PowerShell.  Usage: powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1 [--fix]
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) { & py -3 "$dir\docuframe.py" doctor @args; exit $LASTEXITCODE }
$py = (Get-Command python -ErrorAction SilentlyContinue)
if ($py -and -not ($py.Source -like "*WindowsApps*")) { & python "$dir\docuframe.py" doctor @args; exit $LASTEXITCODE }
Write-Host "Python 3.10+ is not installed."
Write-Host "  Install it with:  winget install Python.Python.3.12   (then open a new PowerShell window)"
exit 1
