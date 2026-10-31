# skill-craft

**A battle-tested playbook for authoring, configuring, verifying and releasing agent skills** (agentskills.io `SKILL.md` format). Distilled from real projects taken through full E2E verification and dual-platform release — not generic advice.

> A skill is a behavior manual for the model: the description decides whether it gets used, the reasons decide whether it's followed, the examples decide whether it looks right, the verification decides whether it's trustworthy.

中文文档：[README.zh-CN.md](README.zh-CN.md)

## What's inside

| You are… | Read |
|---|---|
| Writing a new skill / fixing a skill that never triggers | SKILL.md core (trigger design, rule writing, layered structure, engineering patterns, verification discipline) |
| Releasing a version (tag / Release / dual platform) | `references/release.md` |
| Wiring an API key into a skill (script side + user onboarding) | `references/credentials.md` |
| Hitting installer / encoding / platform / network traps | `references/pitfalls.md` |

Highlights (all empirically earned):

- **Trigger is the lifeline**: how to write a description that wins against built-in tools and rival skills; verified via fresh-session 10-question trigger tests (≥9/10 bar).
- **Credentials done right**: portable four-layer token resolution chain + the user-side first-run onboarding four-piece (setup wizard / error-as-guide / three-state doctor / config outside the skill dir). Skills have no secrets API — scripts inherit the agent's environment; the patterns make that work everywhere.
- **Release ≠ push**: the full pipeline from CHANGELOG to version-stamp verification, for GitCode-primary + GitHub-mirror setups.
- **Pitfalls with guards**: PS 5.1 BOM/GBK parsing, `ErrorActionPreference='Stop'` + native stderr redirect crash, GitHub-only tooling vs other forges, weak-network retries.

## Install

Requires: nothing. This is a pure-content skill (Markdown, no scripts, no keys).

```bash
git clone https://gitcode.com/petra1218/skill-craft.git   # or GitHub mirror: https://github.com/petra1218/skill-craft
cd skill-craft
./install.sh --agent=zcode        # Windows PowerShell: .\install.ps1 -Agent zcode; or --agent=all / claude / codex / cursor …
```

Via the skills CLI (GitHub ecosystem): `npx skills add petra1218/skill-craft`

## Update

The installer is idempotent — update by re-running it after `git pull`. `npx`-installed copies: `npx skills update skill-craft`. There is nothing to configure and no secrets involved.

## Relationship to `skill-creator`

Complementary. The official skill-creator covers the generic creation flow; skill-craft is a distilled playbook from shipped-and-verified projects, adding credentials design, the release pipeline, and verification methodology. Load both when authoring.

## License

MIT
