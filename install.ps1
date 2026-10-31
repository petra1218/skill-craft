# skill-craft 安装器（Windows PowerShell）：把 skills/skill-craft/ 复制到各 Agent 技能目录。
# 幂等：重复安装覆盖旧版并提示。仅分发 skills/skill-craft/ 一个自包含目录。
# 用法: .\install.ps1 -Agent zcode   （可选值 zcode|claude|codex|cursor|codebuddy|workbuddy|reasonx|all）
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("zcode", "claude", "codex", "cursor", "codebuddy", "workbuddy", "reasonx", "all")]
  [string]$Agent
)

$ErrorActionPreference = "Stop"
$Src = Join-Path $PSScriptRoot "skills\skill-craft"
$SkillName = "skill-craft"

# 版本戳：安装时取自 git tag，写入 runtime.conf（无 git 环境退 dev）。
# 注意：PS 5.1 下 EAP=Stop 时原生命令 stderr 重定向（2>$null）会抛终止性错误，
# 故探测 git 期间临时放宽为 Continue，探测完恢复。
$Version = "dev"
if (Get-Command git -ErrorAction SilentlyContinue) {
  $ErrorActionPreference = "Continue"
  $Version = git -C $PSScriptRoot describe --tags 2>$null
  $ErrorActionPreference = "Stop"
  if (-not $Version) { $Version = "dev" }
}

if (-not (Test-Path (Join-Path $Src "SKILL.md"))) {
  Write-Error "错误: 未找到 $Src（请在仓库根目录运行）"
}

function Get-TargetDir([string]$Name) {
  switch ($Name) {
    "zcode"     { Join-Path $HOME ".agents\skills\$SkillName" }
    "claude"    { Join-Path $HOME ".claude\skills\$SkillName" }
    "codex"     { Join-Path $HOME ".codex\skills\$SkillName" }
    "cursor"    { Join-Path $HOME ".claude\skills\$SkillName" }   # Cursor 兼容读取 .claude 技能目录
    "codebuddy" { Join-Path $HOME ".codebuddy\skills\$SkillName" } # 未亲测路径，默认约定
    "workbuddy" { Join-Path $HOME ".workbuddy\skills\$SkillName" } # 未亲测路径，默认约定
    "reasonx"   { Join-Path $HOME ".reasonx\skills\$SkillName" }   # 未亲测路径，默认约定
  }
}

function Install-To([string]$Name, [string]$Dest) {
  if (Test-Path $Dest) {
    Write-Host "[$Name] 检测到旧版本，覆盖安装: $Dest"
    Remove-Item -Recurse -Force $Dest
  } else {
    Write-Host "[$Name] 全新安装: $Dest"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
  Copy-Item -Recurse -Force $Src $Dest
  # runtime.conf 记录版本（WriteAllText 默认 UTF-8 无 BOM，PS 5.1/7 行为一致）
  [System.IO.File]::WriteAllText((Join-Path $Dest "runtime.conf"), "Runtime: Markdown`nVersion: $Version")
  if (-not (Test-Path (Join-Path $Dest "SKILL.md")) -or
      -not (Test-Path (Join-Path $Dest "references"))) {
    Write-Error "[$Name] 错误: 安装不完整（缺 SKILL.md 或 references/）"
  }
  Write-Host "[$Name] 完成（SKILL.md + references/ + runtime.conf）"
}

$Targets = if ($Agent -eq "all") {
  @("zcode", "claude", "codex", "cursor", "codebuddy", "workbuddy", "reasonx")
} else {
  @($Agent)
}

foreach ($t in $Targets) {
  Install-To $t (Get-TargetDir $t)
}
