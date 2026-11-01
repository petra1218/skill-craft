#!/usr/bin/env bash
# skill-craft 安装器：把 skills/skill-craft/ 复制到各 Agent 技能目录。
# 幂等：重复安装覆盖旧版并提示。仅分发 skills/skill-craft/ 一个自包含目录。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/skills/skill-craft"
SKILL_NAME="skill-craft"
# 版本戳：安装时取自 git tag，写入 runtime.conf（无 git 环境退 dev）
VERSION="$(git -C "$SCRIPT_DIR" describe --tags 2>/dev/null || echo dev)"

usage() {
  cat <<'EOF'
用法: install.sh --agent=<target>
  <target> ∈ zcode|claude|codex|cursor|codebuddy|workbuddy|reasonx|all
示例:
  ./install.sh --agent=zcode
  ./install.sh --agent=all
EOF
}

target_dir() {
  case "$1" in
    zcode)     echo "$HOME/.agents/skills/$SKILL_NAME" ;;
    claude)    echo "$HOME/.claude/skills/$SKILL_NAME" ;;
    codex)     echo "$HOME/.codex/skills/$SKILL_NAME" ;;
    cursor)    echo "$HOME/.claude/skills/$SKILL_NAME" ;;  # Cursor 兼容读取 .claude 技能目录
    codebuddy) echo "$HOME/.codebuddy/skills/$SKILL_NAME" ;; # 未亲测路径，默认约定
    workbuddy) echo "$HOME/.workbuddy/skills/$SKILL_NAME" ;; # 未亲测路径，默认约定
    reasonx)   echo "$HOME/.reasonx/skills/$SKILL_NAME" ;;   # 未亲测路径，默认约定
    *) return 1 ;;
  esac
}

install_to() {
  local agent="$1" dest="$2"
  if [ -d "$dest" ]; then
    echo "[$agent] 检测到旧版本，覆盖安装: $dest"
    rm -rf "$dest"
  else
    echo "[$agent] 全新安装: $dest"
  fi
  mkdir -p "$(dirname "$dest")"
  cp -r "$SRC" "$dest"
  printf 'Runtime: Python\nVersion: %s\nCommand: python %s/scripts/craft_cli.py\n' "$VERSION" "$dest" > "$dest/runtime.conf"
  if [ ! -f "$dest/SKILL.md" ] || [ ! -d "$dest/references" ] || [ ! -f "$dest/scripts/craft_cli.py" ]; then
    echo "[$agent] 错误: 安装不完整（缺 SKILL.md / references/ / scripts/）" >&2
    exit 1
  fi
  if command -v python >/dev/null 2>&1; then
    python -m py_compile "$dest/scripts/craft_cli.py" || {
      echo "[$agent] 错误: craft_cli.py 语法检查未通过" >&2; exit 1; }
    rm -rf "$dest/scripts/__pycache__"
  else
    echo "[$agent] 警告: 未找到 python，跳过语法检查（使用本技能需要 Python 3.7+）" >&2
  fi
  echo "[$agent] 完成（SKILL.md + references/ + scripts/ + runtime.conf $VERSION）"
}

[ -f "$SRC/SKILL.md" ] || { echo "错误: 未找到 $SRC（请在仓库根目录运行）" >&2; exit 1; }

case "${1:-}" in
  --agent=zcode)     install_to zcode     "$(target_dir zcode)" ;;
  --agent=claude)    install_to claude    "$(target_dir claude)" ;;
  --agent=codex)     install_to codex     "$(target_dir codex)" ;;
  --agent=cursor)    install_to cursor    "$(target_dir cursor)" ;;
  --agent=codebuddy) install_to codebuddy "$(target_dir codebuddy)" ;;
  --agent=workbuddy) install_to workbuddy "$(target_dir workbuddy)" ;;
  --agent=reasonx)   install_to reasonx   "$(target_dir reasonx)" ;;
  --agent=all)
    for a in zcode claude codex cursor codebuddy workbuddy reasonx; do
      install_to "$a" "$(target_dir "$a")"
    done
    ;;
  *) usage; exit 1 ;;
esac
