<#
    一次搞定：暂存 → 提交 → 推送（带自动重试）

    用法：
        .\commit.ps1 "实验 1-2：完成联网搜索 Agent，观察到模型自己决定搜索轮数"

    为什么要带重试：国内网络到 github.com 时通时不通，
    一次 push 失败很正常，多试几次就行。
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Message
)

$maxAttempts = 6
$waitSeconds = 4

Write-Host "1/2  提交" -ForegroundColor Cyan
git add .
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
    Write-Host "   没有改动可提交，或提交失败。继续尝试推送。" -ForegroundColor Yellow
}

Write-Host "2/2  推送（最多 $maxAttempts 次）" -ForegroundColor Cyan
for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host "    第 $i 次..." -ForegroundColor DarkGray
    git push
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    推送成功 ✅" -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Seconds $waitSeconds
}

Write-Host "    $maxAttempts 次都没成功。检查网络，或稍后再试。" -ForegroundColor Red
exit 1
