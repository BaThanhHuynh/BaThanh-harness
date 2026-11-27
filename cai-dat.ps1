# Cài harness lên máy mới (chạy lại nhiều lần vô hại: cái gì có rồi thì bỏ qua).
#   git clone https://github.com/BaThanhHuynh/BaThanh-harness.git D:\codevstdio\BaThanh-harness
#   powershell -ExecutionPolicy Bypass -File D:\codevstdio\BaThanh-harness\cai-dat.ps1
param(
    [string]$HopDong = "D:\codevstdio",        # thư mục gốc chứa các dự án; khác mặc định thì sửa HOP_DONG trong harness.py
    [string]$ClaudeDir = "$HOME\.claude"
)
$ErrorActionPreference = "Stop"
$Repo = $PSScriptRoot

function Noi($duong, $dich) {
    if (Test-Path $duong) { Write-Host "  bỏ qua (đã có): $duong"; return }
    New-Item -ItemType Directory -Force (Split-Path $duong) | Out-Null
    New-Item -ItemType Junction -Path $duong -Target $dich | Out-Null
    Write-Host "  nối: $duong -> $dich"
}

Write-Host "1. Junction"
Noi "$ClaudeDir\harness" $Repo
Noi "$HopDong\.claude\rules" "$Repo\codevstdio\.claude\rules"

Write-Host "2. Hợp đồng CLAUDE.md"
if (Test-Path "$HopDong\CLAUDE.md") { Write-Host "  bỏ qua (đã có)" }
else { Copy-Item "$Repo\codevstdio\CLAUDE.md" "$HopDong\CLAUDE.md"; Write-Host "  chép xong" }

Write-Host "3. Git hook đồng bộ"
git -C $Repo config core.hooksPath githooks
# Repo dự án: hook quét bí mật khi commit. Repo clone/init sau này tự nhận qua init.templateDir;
# repo đã có thì `git init` lại chỉ thêm hook còn thiếu, không ghi đè hook sẵn có.
if (-not (git config --global --get init.templateDir)) {
    git config --global init.templateDir (("$ClaudeDir\harness\git-template") -replace '\\', '/')
}
Write-Host "  init.templateDir = $(git config --global --get init.templateDir)"
foreach ($d in Get-ChildItem "$HopDong\repo" -Directory -ErrorAction SilentlyContinue) {
    if (Test-Path "$($d.FullName)\.git") { git -C $d.FullName init -q; Write-Host "  hook: $($d.Name)" }
}

Write-Host "4. Skill tự cài"
New-Item -ItemType Directory -Force "$ClaudeDir\skills" | Out-Null
foreach ($s in Get-ChildItem "$Repo\dot-claude\skills" -Directory) {
    if (Test-Path "$ClaudeDir\skills\$($s.Name)") { Write-Host "  bỏ qua (đã có): $($s.Name)" }
    else { Copy-Item $s.FullName "$ClaudeDir\skills" -Recurse; Write-Host "  chép: $($s.Name)" }
}

Write-Host "5. settings.json"
$caiDat = "$ClaudeDir\settings.json"
if (Test-Path $caiDat) {
    Write-Host "  đã có -> gộp tay khối hooks/permissions từ $Repo\dot-claude\settings.json"
} else {
    # đường dẫn trong bản chép là của máy gốc -> đổi sang HOME của máy này; ghi UTF-8 không BOM
    $nd = (Get-Content "$Repo\dot-claude\settings.json" -Raw -Encoding UTF8) -replace 'C:/Users/dell', ($HOME -replace '\\', '/')
    [IO.File]::WriteAllText($caiDat, $nd, (New-Object Text.UTF8Encoding $false))
    Write-Host "  chép xong (đã đổi đường dẫn sang $HOME)"
}

Write-Host "6. Plugin - chạy trong Claude Code:"
$cho = Get-Content "$Repo\dot-claude\plugins\known_marketplaces.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($m in $cho.PSObject.Properties) { Write-Host "  /plugin marketplace add $($m.Value.source.repo)" }
$pl = Get-Content "$Repo\dot-claude\plugins\installed_plugins.json" -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $pl.plugins.PSObject.Properties) { Write-Host "  /plugin install $($p.Name)" }

Write-Host "7. MCP: thêm bằng 'claude mcp add' theo $Repo\dot-claude\mcp-servers.json (điền lại giá trị <dien-tay>)"

Write-Host "8. Tự kiểm"
python "$Repo\harness.py" tu-kiem-bat-buoc
