# --- config ---
\ = "ws://localhost:8000/v1/state/live/ws"
\ = ".\.venv\Scripts\Activate.ps1"
# 1) API server as a background job
Start-Job -Name edon_api -ScriptBlock {
  param(\)
  & \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList \ | Out-Null
Start-Sleep -Seconds 2
# 2) WebSocket subscriber as a background job
Start-Job -Name edon_sub -ScriptBlock {
  param(\, \)
  & \
  python examples\subscribe_state.py \
} -ArgumentList \, \ | Out-Null
Start-Sleep -Seconds 1
# 3) One-shot replay in the foreground so you see a response immediately
& \
python examples\replay_jsonl.py data\sample.jsonl
Write-Host "
--- Jobs running ---"
Get-Job
Write-Host "
Tips:"
Write-Host "  Receive-Job -Name edon_api -Keep   # tail server logs"
Write-Host "  Receive-Job -Name edon_sub -Keep   # tail websocket messages"
Write-Host "  Stop-Job edon_api, edon_sub        # stop"
Write-Host "  Remove-Job edon_api, edon_sub      # clean up"
