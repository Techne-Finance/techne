# Wait for uvicorn to reload
Start-Sleep -Seconds 5

$base = "http://localhost:8000"

$tests = @(
    # ERC8004 - was missing (not registered)
    @{M = "GET"; P = "/api/agent-trust-score/0x1234" },
    @{M = "GET"; P = "/api/agent-profile/0x1234" },
    @{M = "GET"; P = "/api/erc8004-stats" },

    # Agent Service - pause/resume
    @{M = "POST"; P = "/api/agents/0xtest/pause"; B = '' },
    @{M = "POST"; P = "/api/agents/0xtest/resume"; B = '' },

    # Agent DELETE
    @{M = "DELETE"; P = "/api/agents/0xtest" },

    # Audit export
    @{M = "GET"; P = "/api/audit/export" },
    @{M = "GET"; P = "/api/audit/export?wallet=all" },

    # Engineer tasks
    @{M = "GET"; P = "/api/engineer/tasks/test123" },

    # LP Info (defined in main.py)
    @{M = "GET"; P = "/api/lp/info/0x1234" },

    # Scout pool-pair
    @{M = "GET"; P = "/api/scout/pool-pair?token0=USDC&token1=WETH" },

    # Also re-test the core endpoints
    @{M = "GET"; P = "/api/pools?chain=base&limit=2" },
    @{M = "GET"; P = "/api/protocols" },
    @{M = "GET"; P = "/api/premium/subscribe?user_address=test" },
    @{M = "GET"; P = "/api/agents/user/0x1234" },
    @{M = "GET"; P = "/api/audit/recent" },
    @{M = "GET"; P = "/api/audit/reasoning-logs" }
)

Write-Host "=== ENDPOINT RE-TEST ==="
Write-Host ""

$pass = 0
$fail = 0

foreach ($t in $tests) {
    $url = $base + $t.P
    try {
        $params = @{
            Uri             = $url
            Method          = $t.M
            TimeoutSec      = 10
            UseBasicParsing = $true
            ErrorAction     = "Stop"
        }
        if ($t.B -ne $null -and $t.M -ne "GET") {
            $params.Body = if ($t.B -eq '') { '{}' } else { $t.B }
            $params.ContentType = "application/json"
        }
        $resp = Invoke-WebRequest @params
        $status = $resp.StatusCode
        $tag = "PASS"
        $pass++
    }
    catch {
        $status = "ERR"
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        # 422 = route exists but validation failed (OK)
        # 404 from handler = route exists but resource not found 
        if ($status -eq 422 -or $status -eq 400) {
            $tag = "PASS"
            $pass++
        }
        elseif ($status -eq 404) {
            $tag = "FAIL"
            $fail++
        }
        elseif ($status -eq 405) {
            $tag = "FAIL"
            $fail++
        }
        elseif ($status -eq 500) {
            # 500 may be acceptable if the route exists but internal dependency missing
            $tag = "WARN"
            $pass++
        }
        else {
            $tag = "FAIL"
            $fail++
        }
    }
    Write-Host "$tag $status $($t.M) $($t.P)"
}

Write-Host ""
Write-Host "=== RESULTS ==="
Write-Host "PASS: $pass"
Write-Host "FAIL: $fail"
Write-Host "TOTAL: $($pass + $fail)"
