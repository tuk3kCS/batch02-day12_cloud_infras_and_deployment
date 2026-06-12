# Start all Legal Multi-Agent System services
# Registry must be first, then leaf agents, then orchestrators

$ErrorActionPreference = "Stop"

Write-Host "Starting Registry service on port 10000..."
$registry = Start-Process -FilePath "python" -ArgumentList "-m registry" -PassThru -NoNewWindow

Start-Sleep -Seconds 2

Write-Host "Starting Tax Agent on port 10102..."
$tax = Start-Process -FilePath "python" -ArgumentList "-m tax_agent" -PassThru -NoNewWindow

Write-Host "Starting Compliance Agent on port 10103..."
$compliance = Start-Process -FilePath "python" -ArgumentList "-m compliance_agent" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

Write-Host "Starting Law Agent on port 10101..."
$law = Start-Process -FilePath "python" -ArgumentList "-m law_agent" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

Write-Host "Starting Customer Agent on port 10100..."
$customer = Start-Process -FilePath "python" -ArgumentList "-m customer_agent" -PassThru -NoNewWindow

Write-Host ""
Write-Host "All services started:"
Write-Host "  Registry:         http://localhost:10000"
Write-Host "  Customer Agent:   http://localhost:10100"
Write-Host "  Law Agent:        http://localhost:10101"
Write-Host "  Tax Agent:        http://localhost:10102"
Write-Host "  Compliance Agent: http://localhost:10103"
Write-Host ""
Write-Host "Run test_client.py to send a query:"
Write-Host "  python test_client.py"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services."

# Wait and keep running until Ctrl+C
$allProcs = @($registry, $tax, $compliance, $law, $customer)
try {
    while ($true) {
        Start-Sleep -Seconds 2
        foreach ($proc in $allProcs) {
            if ($proc.HasExited -and $proc.ExitCode -ne 0) {
                Write-Host "WARNING: Process $($proc.Id) exited with code $($proc.ExitCode)" -ForegroundColor Yellow
            }
        }
    }
} finally {
    Write-Host ""
    Write-Host "Stopping all services..."
    foreach ($proc in $allProcs) {
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "All services stopped."
}
