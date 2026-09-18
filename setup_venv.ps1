# Create virtual environment if it doesn't exist
if (-not (Test-Path .venv)) {
    Write-Host "Creating virtual environment .venv..." -ForegroundColor Green
    python -m venv .venv
} else {
    Write-Host ".venv already exists." -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install requirements
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Green
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "`nSetup complete! You can now run:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  alembic upgrade head" -ForegroundColor Yellow
Write-Host "  python -m app.cli seed" -ForegroundColor Yellow
Write-Host "  uvicorn app.main:app --reload" -ForegroundColor Yellow
