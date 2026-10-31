# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://gitcode.com/petra1218/skill-craft/compare/v0.1.0...main
[0.1.0]: https://gitcode.com/petra1218/skill-craft/releases/tag/v0.1.0
