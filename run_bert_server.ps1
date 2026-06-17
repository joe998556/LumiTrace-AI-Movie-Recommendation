# LumiTrace BERT Semantic Recommendation Server
# Run this script to start the BERT service on port 5001

Set-Location -Path $PSScriptRoot

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Start BERT service
Write-Host "Starting LumiTrace BERT service on port 5001..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

python ai_engine\bert_service.py --host 0.0.0.0 --port 5001 --device cuda --vectors movie_vectors.json
