# skill-craft

技能开发的实证方法论 + 可执行的双平台标准化发布工具（agentskills.io `SKILL.md` 格式）。
从一个完整走通 E2E 验证与双平台发版的真实项目提炼，不是通用建议。

> 技能是给模型的行为说明书：触发词决定用不用，理由决定听不听，示例决定像不像，验证决定靠不靠谱。
> 发布是一条流水线：纯文档挡不住漂移，约定必须变成工具。

主仓库：`gitcode.com/petra1218/skill-craft`（GitHub 为镜像，面向 `npx skills` 生态）。
英文文档：[README.md](README.md)。

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

用法要点：

- 发布命令默认 dry-run，`--apply` 才执行——先看计划再动手；
- Release 正文单一来源：一份 notes 文件发双平台（GitCode + GitHub）；
- check 的令牌扫描覆盖已跟踪文件与 remote URL 内嵌凭据；
- 仓库创建、README、CHANGELOG、Release 正文默认中文；
- 发版令牌走四层解析链（参数 > 环境变量 > `~/.skill-craft/.env` > 技能目录 `.env`），
  `doctor` 三态自检并给出配置指引。

这些门禁不是拍脑袋定的：2026-11 对 6 个真实仓库的发版实践做过全量核查——remote 挂法三种、
双平台正文分叉出过错误命令、CHANGELOG 三态、remote URL 内嵌明文令牌——每条门禁对应一个
真实翻车（记录在 `references/release.md` 第六节）。

## 安装

需要 Python 3.7+（仅发版工具需要；方法论部分是纯 Markdown）。

```bash
git clone https://gitcode.com/petra1218/skill-craft.git
cd skill-craft
./install.sh --agent=zcode        # Windows PowerShell: .\install.ps1 -Agent zcode; 或 --agent=all
```

`npx skills add petra1218/skill-craft`（GitHub 生态；GitCode 地址不被 skills CLI 识别）。

## 更新

安装器幂等：`git pull` 后重跑安装器即更新；`npx` 渠道用 `npx skills update skill-craft`。
用户令牌放在技能目录外（`~/.skill-craft/.env`），升级不丢。

## 与官方 skill-creator 的关系

互补。官方 skill-creator 讲通用创建流程；skill-craft 提供实证打法 + 可执行发版流水线
（凭据设计、双平台发布、验证方法论）。写技能时两个都加载。

## 许可证

MIT
