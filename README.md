# skill-craft

**技能开发的实证方法论 + 可执行的双平台标准化发布工具**（agentskills.io `SKILL.md` 格式）。
从一个完整走通 E2E 验证与双平台发版的真实项目提炼，不是通用建议。

> 技能是给模型的行为说明书：触发词决定用不用，理由决定听不听，示例决定像不像，验证决定靠不靠谱。
> 发布是一条流水线：纯文档挡不住漂移，约定必须变成工具。

中文文档：[README.zh-CN.md](README.zh-CN.md)。主仓库 GitCode（`gitcode.com/petra1218/skill-craft`），本仓库为其 GitHub 镜像（面向 `npx skills` 生态）。

## 能力一览

| 你正在做的事 | 用什么 |
|---|---|
| 写新技能 / 修一个不触发的技能 | SKILL.md 方法论五节（触发设计、规则写法、分层结构、工程配套、验证纪律） |
| 创建仓库 / 发版 / 打 tag / 双平台 Release / 回查 / 仓库纳入标准 | `scripts/craft_cli.py`（下表） |
| 写 README / Release 正文 / CHANGELOG，减少机器腔 | `references/release-copy.md` + `references/vocabulary.md` |
| 技能接 API key（脚本侧解析链 + 用户侧引导） | `references/credentials.md` |
| 安装器 / 编码 / 平台 / 网络坑 | `references/pitfalls.md` |

### craft_cli.py（Python 3.7+，零依赖单文件）

```
init    <目录> --name X --type skill|app --gitcode <url> --github <url>   # 中文默认脚手架
check   <仓库> [--notes-file 正文] [--gate "npm test"]                    # 只读体检
adopt   <仓库> --gitcode <url> --github <url>                             # 既有仓库纳入标准
release <仓库> --version v0.2.0 --notes-file 正文 [--apply]               # 发版流水线
doctor                                                                    # 版本/令牌三态自检
```

发布命令默认 dry-run，`--apply` 才执行；Release 正文单一来源、双平台同一份；
令牌扫描覆盖已跟踪文件与 remote URL 内嵌凭据；中文为默认语言，行文过机器腔警告级 lint。

所有门禁都来自实证教训（2026-11 对 6 个真实仓库发版实践的核查，详见 `references/release.md` 第六节）。

## 安装

需要 Python 3.7+（仅发版工具需要；方法论部分是纯 Markdown）。

```bash
git clone https://gitcode.com/petra1218/skill-craft.git   # 或 GitHub 镜像
cd skill-craft
./install.sh --agent=zcode        # Windows PowerShell: .\install.ps1 -Agent zcode; 或 --agent=all
```

`npx skills add petra1218/skill-craft`（GitHub 生态）。

## 更新

安装器幂等：`git pull` 后重跑安装器即更新；`npx` 渠道用 `npx skills update skill-craft`。
发版令牌（可选，仅 `release`/`doctor` 需要）配置见 `python <技能目录>/scripts/craft_cli.py doctor` 的指引。

## 与 skill-creator 的关系

互补。官方 skill-creator 讲通用创建流程；skill-craft 提供实证打法 + 可执行发版流水线
（凭据设计、双平台发布、验证方法论）。写技能时两个都加载。

## 许可证

MIT
