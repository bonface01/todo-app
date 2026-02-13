Add-Type -AssemblyName System.Windows.Forms

# Config
$intervalSeconds = 45       # how often to move
$delta = 1                  # pixels to nudge
$running = $true

Write-Host "Mouse mover starting. Press Ctrl+C to stop."

try {
    while ($running) {
        $pos = [System.Windows.Forms.Cursor]::Position
        # tiny jiggle out and back
        [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($pos.X + $delta, $pos.Y)
        Start-Sleep -Milliseconds 100
        [System.Windows.Forms.Cursor]::Position = $pos
        Start-Sleep -Seconds $intervalSeconds
    }
} catch [System.Exception] {
    Write-Host "Stopped: $($_.Exception.Message)"
}
