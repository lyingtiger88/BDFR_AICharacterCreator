# Run once from PowerShell at the repository root.
# Uses Python 3.11/3.10 external to Autodesk Maya.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) {
  $exe = & py -3.11 -c "import sys;print(sys.executable)" 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $exe) {
    $exe = & py -3.10 -c "import sys;print(sys.executable)" 2>$null
  }
} else {
  $exe = $null
}
if (-not $exe) { throw "Install Python 3.11 or 3.10 from python.org, then rerun." }
& $exe -m venv ".venv_smplx"
if ($LASTEXITCODE -ne 0) { throw "Unable to create venv" }
$p = Join-Path $PSScriptRoot ".venv_smplx\Scripts\python.exe"
& $p -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $p -m pip install torch smplx numpy
if ($LASTEXITCODE -ne 0) { throw "SMPL-X dependency installation failed" }
& $p -c "import torch, smplx; print('SMPL-X Python ready; torch',torch.__version__)"
if ($LASTEXITCODE -ne 0) { throw "SMPL-X dependency verification failed" }
Write-Host "BDFR SMPL-X ready: $p"
Write-Host "Model weights stay private in models\smplx; never commit them to GitHub."
