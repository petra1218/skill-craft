# skill-craft

**做技能的实证方法论**——覆盖 agentskills 标准（SKILL.md 目录）技能的**创作、凭据、验证、发布**全生命周期。从真实跑通 E2E 验证与双平台发布的项目里提炼，不是泛泛建议。

> 技能是给模型的行为说明书：触发词决定用不用，理由决定听不听，示例决定像不像，验证决定靠不靠谱。

English docs: [README.md](README.md)

## 内容地图

| 你正在… | 读 |
|---|---|
| 写新技能 / 修一个从不触发的技能 | SKILL.md 主体（触发设计、规则写法、分层结构、工程配套、验证纪律） |
| 发版本（tag / Release / 双平台） | `references/release.md` |
| 给技能接 API key（脚本侧 + 用户侧配置引导） | `references/credentials.md` |
| 踩安装器/编码/平台/网络的坑 | `references/pitfalls.md` |

要点（全部实证换来）：

- **触发是生死线**：description 怎么写才能在与内置工具、竞品技能的竞争中赢下触发；用全新会话 10 问触发测试验证（≥9/10 门槛）。
- **凭据设计**：可移植的四层令牌解析链 + 用户侧首次配置四件套（setup 向导 / 错误即引导 / doctor 三态 / 配置外置）。技能没有密钥库 API——脚本继承 Agent 进程环境，这套模式让它在任何环境都工作。
- **发布 ≠ 推送**：从 CHANGELOG 到版本戳验证的完整流水线，适配 GitCode 首发 + GitHub 镜像的双平台架构。
- **带守护的陷阱清单**：PS 5.1 BOM/GBK 解析、EAP-Stop 下原生命令 stderr 崩溃、GitHub-only 工具 × 其它代码平台的错配、弱网重试。

## 安装

零依赖：纯内容技能（Markdown，无脚本、无密钥）。

```bash
git clone https://gitcode.com/petra1218/skill-craft.git   # 或 GitHub 镜像：https://github.com/petra1218/skill-craft
cd skill-craft
./install.sh --agent=zcode        # Windows PowerShell: .\install.ps1 -Agent zcode；或 --agent=all / claude / codex / cursor …
```

经 skills CLI（GitHub 生态）：`npx skills add petra1218/skill-craft`

## 更新

安装器幂等——`git pull` 后重跑即更新；`npx` 安装的副本用 `npx skills update skill-craft`。本技能无需任何配置，不涉及密钥。

## 与官方 skill-creator 的关系

互补。官方 skill-creator 讲通用创建流程；skill-craft 是从发布并验证过的项目里提炼的打法，额外覆盖凭据设计、发布流水线与验证方法论。做技能时两个都加载。

## 许可证

MIT
