# Start Streamlit with project root on PYTHONPATH (PowerShell)
$projectRoot = (Get-Location).Path
$venvPy = Join-Path $projectRoot ".venv\Scripts\python.exe"
Write-Host "Checking that 'src' package is importable in the virtualenv..."
try {
	& $venvPy -c "import importlib; importlib.import_module('src')" 2>$null
	Write-Host "'src' is importable."
} catch {
	Write-Host "'src' not importable — installing editable package (pip install -e .)"
	& $venvPy -m pip install -e $projectRoot
}

Write-Host "Launching Streamlit from project root..."
$env:PYTHONPATH = $projectRoot
& $venvPy -m streamlit run src/dashboard/app.py
