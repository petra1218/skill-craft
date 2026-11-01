# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-01

### Added

- `scripts/craft_cli.py`：可执行的标准化发布 CLI（Python 3.7+ 纯标准库单文件），五个子命令：
  - `init` —— 仓库脚手架，中文默认（README 按 readme-docs 文体、CHANGELOG 带 compare 链接占位、
    LICENSE、.gitignore、幂等安装器模板；skill 型另生成 SKILL.md 骨架 + runtime.conf）；
  - `check` —— 发版前只读体检：CHANGELOG 格式与链接、令牌扫描（已跟踪文件 + remote URL 内嵌凭据）、
    remote 双平台姿态、tag 现状、Release 正文机器腔 lint（警告级）、`--gate` 自定义门禁命令；
  - `release` —— 发版流水线（默认 dry-run，`--apply` 执行）：门禁 → 正文单一来源双平台同发 →
    附注 tag + 独立发版提交 → 双推（弱网重试）→ 双平台 Release API + 强制回查 → skill 型重装指引；
  - `adopt` —— 既有仓库纳入标准：幂等挂双 pushurl、迁移内嵌令牌 remote 到 SSH/干净 URL、
    补 .gitignore 与 CHANGELOG（从 tag 历史自动生成 compare 链接）；
  - `doctor` —— 版本闭环自检 + 双平台令牌三态（未配置→三步指路 / 无效 / 有效附实测延迟）。
- `references/release-copy.md`：发布文案写法（自 reduce-ai-zh 提炼的发布场景子集——硬约束、
  README 排版与语气、行文规则、正文五件套、裁决句）。
- `references/vocabulary.md`：机器腔词表精选（营销形容词、空泛开场、万能动词、排比触发器、点题说教），
  供 lint 与人工审校参考。
- `tests/`：52 项单测（BOM 不变量、令牌扫描与脱敏、机器腔 lint、CHANGELOG/正文纯函数、
  发版计划纯函数、init 脚手架端到端）。

### Changed

- SKILL.md 重构为四分支路由（写技能 / 发版执行 / 发布文案 / 凭据），description 触发词扩至
  创建仓库、发版、双平台发布、文案去 AI 味等场景；方法论五节保留。
- `references/release.md`：脚本为主路径，手动流程降为原理；新增 2026-11 六仓核查的实证教训
  （正文分叉致错误命令、首版 Release 草稿滞留 12.6 小时、GitCode 用户级端点需 token）。
- `references/pitfalls.md` 新增两条：remote URL 内嵌令牌（check/adopt 守护）、
  Windows 管道 GBK 解码干扰 JSON 比对。
- `references/credentials.md` 补 skill-craft 发版令牌（GITCODE_TOKEN/GITHUB_TOKEN）链路示例。
- 安装器：复制 scripts/、runtime.conf 打戳写绝对路径 Command 行、装后 `py_compile` 校验。
- 语言标准：仓库创建与发布文案默认中文（英文可选）。

### Notes

- 本版本的门禁清单来自对 6 个真实仓库（规范 skill / 漂移 skill / 无实践 app 三种形态）发版
  实践的全量核查；`check` 已用这 6 个仓库验证检出能力。
- 非目标：Release 附件上传（应用仓自有流水线可经 `--gate` 钩子接入）。

## [0.1.0] - 2026-10-31

### Added

- `skill-craft` skill — a battle-tested playbook for authoring, configuring, verifying and releasing agent skills (agentskills.io SKILL.md format), distilled from two real projects taken through full E2E verification and release:
  - SKILL.md core: trigger-first description design (incl. winning trigger competition against built-in tools), rule writing (reason + self-check + example), layered structure (hard constraints > principles > habits > references, progressive disclosure), tool-skill engineering patterns (agent-readable errors, version closure, frozen output contract), verification discipline (fresh-session trigger tests, happy-path AND fallback-path interpreter runs).
  - `references/credentials.md` — the portable four-layer token resolution chain (param > env > user-level .env > skill-dir .env, BOM-tolerant), per-environment gotchas (Windows setx lag, macOS GUI env gap), and the user-side first-run onboarding four-piece (setup wizard, error-as-guide, three-state doctor, config outside the skill dir).
  - `references/release.md` — dual-platform release pipeline (CHANGELOG → gates → tag → dual push → Release APIs → verify → reinstall), "release ≠ push", release-notes formula, honest update-notification channels.
  - `references/pitfalls.md` — engineering traps with guards: PS 5.1 BOM/GBK parsing, EAP-Stop stderr redirect crash, installer encoding invariants, platform mismatch (GitHub-only tooling vs GitCode-hosted repos), weak-network retry patterns.
- Idempotent installers (`install.sh` / `install.ps1`) with version stamping into `runtime.conf` (git describe, `dev` fallback); the PowerShell installer ships UTF-8-with-BOM and the EAP-safe git probe from day one (the lessons are applied, not just documented).
- Bilingual README (en / zh-CN) with honest compatibility matrix.

### Notes

- Primary repo: GitCode (gitcode.com/petra1218/skill-craft); GitHub mirror for the `npx skills` ecosystem.
- Complements — does not replace — the official `skill-creator` skill: that one covers the generic creation flow; this one is a distilled playbook including credentials design, release pipeline, and verification methodology.

[Unreleased]: https://gitcode.com/petra1218/skill-craft/compare/v0.2.0...main
[0.2.0]: https://gitcode.com/petra1218/skill-craft/compare/v0.1.0...v0.2.0
[0.1.0]: https://gitcode.com/petra1218/skill-craft/releases/tag/v0.1.0
