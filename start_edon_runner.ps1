Start-Process powershell -ArgumentList '-NoExit','-Command','.\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload'
Start-Sleep -s 2
Start-Process powershell -ArgumentList '-NoExit','-Command','.\.venv\Scripts\Activate.ps1; python examples\subscribe_state.py ws://localhost:8000/v1/state/live/ws'
Start-Sleep -s 1
Start-Process powershell -ArgumentList '-NoExit','-Command','.\.venv\Scripts\Activate.ps1; python examples\replay_jsonl.py data\sample.jsonl'
