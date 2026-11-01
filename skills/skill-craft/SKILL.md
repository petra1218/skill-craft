---
name: skill-craft
description: >-
  做技能与标准化发布的实证方法论 + 可执行工具。当用户要"写个技能/做个 skill/封装成技能/
  改进 SKILL.md/技能不触发"时使用；当用户要"创建仓库/初始化项目/发布新版本/打 tag/
  发 Release/双平台发布/发到 GitCode 和 GitHub/把仓库纳入标准/回查 Release/写 README、
  发布说明、CHANGELOG/减少文案 AI 味/给技能配 key 加凭据"时也使用。执行发版用自带
  scripts/craft_cli.py（init/check/release/adopt/doctor，中文默认、dry-run 保护、
  双平台同源正文）。做任何 agentskills 标准（SKILL.md 目录）的技能开发都应加载。
  与官方 skill-creator 的分工：那个讲通用创建流程，本技能提供实证打法 + 完整发布
  生命周期（含凭据设计与双平台流水线），两者可叠加。(Battle-tested playbook plus an
  executable CLI for authoring, verifying and dual-platform releasing agent skills.)
---

# skill-craft：做技能与标准化发布的实证打法

一套从真实项目完整走通提炼的方法论 + 把它固化成的可执行工具。核心信念：**技能是给模型的
行为说明书——触发词决定用不用，理由决定听不听，示例决定像不像，验证决定靠不靠谱；
发布是一条流水线而不是一个动作——纯文档挡不住漂移，约定必须变成工具。**

## 先定标：按任务读对应内容

| 你正在做的事 | 读什么 / 用什么 |
|---|---|
| 写新技能 / 改 SKILL.md / 排查触发问题 | 本文方法论五节 |
| **创建仓库 / 发布新版本 / 打 tag / 发 Release / 双平台发布 / 仓库纳入标准 / 回查** | `scripts/craft_cli.py`（速查见下），原理加读 `references/release.md` |
| **写 README / Release 正文 / CHANGELOG 文案**（含减少 AI 味） | `references/release-copy.md`（词表 `references/vocabulary.md`） |
| 技能要配 API key / 凭据 | `references/credentials.md` |
| 写安装器 / 遇编码、平台、网络坑 | `references/pitfalls.md` |

读完定标再动手。

## craft_cli.py 命令速查（发版的执行载体）

```
python <技能目录>/scripts/craft_cli.py init   <目录> --name X --type skill|app --gitcode <url> --github <url>
python <技能目录>/scripts/craft_cli.py check  <仓库> [--notes-file 正文] [--gate "npm test"]
python <技能目录>/scripts/craft_cli.py adopt  <仓库> --gitcode <url> --github <url>
python <技能目录>/scripts/craft_cli.py release <仓库> --version v0.2.0 --notes-file 正文 [--apply]
python <技能目录>/scripts/craft_cli.py doctor
```

四条铁律：

1. **默认 dry-run**，`--apply` 才真执行——发布是外向动作，先看计划再动手；
2. **Release 正文单一来源**：一份 `--notes-file` 发双平台，从构造上杜绝"每平台各写一遍"
   的漂移（实证教训：reduce-ai 双平台正文分叉曾把错误安装命令只藏在一边）；
3. **中文为主**：创建仓库、README、CHANGELOG、Release 正文默认中文（`--lang en` 可切）；
   行文遵守 `references/release-copy.md`，lint 是警告级不阻断；
4. **令牌永不回显**：check 扫描命中只报文件行号；令牌走四层解析链（见 credentials.md），
   doctor 三态自检（未配置→指路 / 无效→核对 / 有效→附延迟）。

发版动作的完整原理、平台 API 差异与手动回退路径见 `references/release.md`。

## 一、触发是第一生死线

- frontmatter `description` 是唯一常驻上下文的触发信号，必须**主动、带钩子**：做什么 +
  何时触发 + 用户会说的原话变体（口语、方言、错别字："搜一下/查查/瞅瞅/latest"）。模型天然
  **漏触发**而非误触发，宁过勿缺。
- **工具竞争环境要明写优先级**：环境里存在内置工具（WebSearch/WebFetch）或同类竞品技能时，
  description 必须直接声明"优先用本技能，因为……（省 token/带编号引用/更可控）"。实证：
  没有这句时内置搜索抢走触发，加上后 10/10。
- 覆盖"用户没明说"的场景："即使没提到 X 也要加载"。
- **验证触发必须开全新会话测**（技能发现是会话启动时固定的）；标准动作是 10 问口语化/
  错别字触发测试，门槛 ≥9/10。

## 二、规则写法：理由 + 自检 + 示例，不写命令清单

- 每条规则带 **why**，尤其反直觉的（例："术语轮换是机器腔，行内人不换词"）——模型理解了
  原因，才会在规则没覆盖的边界情况做对。
- 每条规则给**可操作的自检**："把连接词删掉，逻辑变模糊就留，只是语气变平就删"；
  "整段能原样搬进任何领域就说明太空，重写"。
- **示例胜过规则**：SKILL.md 里放一段真实输出样例，比十条格式规定都管用；每条规则配前/后对照。
- 末尾放一条**裁决句**处理规则冲突："行内人会怎么做？冲突时以这句话为准。"

## 三、分层结构

- **硬约束层**（不可被任何配置推翻）> **原则层** > **习惯层** > **参考层**。
- **渐进披露**：metadata 精简；SKILL.md 主体 <500 行；细节按情境放 `references/` 并在正文
  写明何时读（按文体/学科/任务分文件都是好范式）。
- **文风型技能用"生成时约束"定位**：动笔前加载、产出即终稿，明确不做"先写后润"；
  并诚实声明非目标。
- **工具型技能用"阶梯"控制成本**：先低成本的（如 search，摘要层够 90% 场景），真正需要才
  高成本的（如 fetch 整页）——教模型"少做"和教它"做"一样重要。
- 双语技能做成**镜像孪生**（同骨架、各自本地化示例），不是机翻。

## 四、工程配套（工具型）

- 包结构：`SKILL.md + scripts/（零依赖单文件）+ references/ + runtime.conf`，自包含、
  无仓库外依赖。skill-craft 自身即此结构（craft_cli.py 为范本）。
- **错误信息写给 Agent 读**：无 key 报错 = 三步指引（取 key → 放哪 → 重试），Agent 读到
  就能引导用户，不需要人守着。详细设计见 `references/credentials.md`。
- **版本闭环**：安装器落位时打版本戳进 runtime.conf（`git describe --tags`，无 git 退
  `dev`），自检命令首行回显版本；更新 = 幂等重跑安装器；README 必须有 Update 章节。
- 输出带冻结契约号（如 `contract: v1`），破坏性变更升版本——下游 Agent 可放心解析。

## 五、验证纪律（最贵的一节，全是翻车换的）

- **写进 README/发布说明的命令必须本机实证**，或明确标注"未验证"。警惕平台错配：工具的
  生态假设（GitHub）与仓库实际托管（GitCode）不同源时，`owner/repo` 类简写命令默认不可用。
- **安装器/脚本必须用目标解释器真跑**，且 happy path 和回退路径都要测。典型坑见
  `references/pitfalls.md`（PS 5.1 无 BOM 按 GBK 解析报语法错；`$ErrorActionPreference='Stop'`
  下原生命令 stderr 重定向抛终止性错误）。此类不变量写成单测守护（.ps1 含非 ASCII 必须带
  BOM、.sh 绝不带 BOM）。
- **E2E 测模型行为决策而非仅功能**：低预算截断时模型会不会正确权衡？报错时会不会引导用户？
  引用要对照缓存溯源防幻觉 URL；关键事实用第二个工具交叉核对。
- 子代理 = 全新会话等价物，可测触发；注意供应商并发上限与用量上限，大批量分批 + 要求简答。
- **门禁工具自己要先过自己的门禁**：check/lint 类工具发布前用真实仓库验一遍——
  skill-craft v0.2.0 曾用 6 个真实仓库（三种形态：规范 skill / 漂移 skill / 无实践 app）
  验证 check 的检出能力。

## 元教训

技能的每句话都在争夺模型的注意力与执行意愿。发布是流水线而非动作——**方法论进了文档
只是第一步，落进工具才算落地**：同一作者六个仓库的 remote 挂法、CHANGELOG 纪律、正文
同源性全部漂移过，纯文档零约束力（实证见 `references/release.md` 第六节）。发布文案的
机器腔同理——lint 只提醒，行内人的手感来自 `references/release-copy.md` 的规则加练习。
