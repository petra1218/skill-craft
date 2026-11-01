# 发布流水线：从 CHANGELOG 到版本戳验证

**发布 ≠ 推送**：push 只是代码到远端；"发布" = 版本化（CHANGELOG）+ tag + Release 页 + 升级指引，四件套齐才算发完。

## 零、标准执行方式：craft_cli.py（主路径）

```bash
python <技能目录>/scripts/craft_cli.py check  <仓库>                     # 只读体检
python <技能目录>/scripts/craft_cli.py adopt  <仓库> --gitcode <url> --github <url>   # 既有仓库纳入标准
python <技能目录>/scripts/craft_cli.py release <仓库> --version v0.2.0 --notes-file notes.md          # dry-run
python <技能目录>/scripts/craft_cli.py release <仓库> --version v0.2.0 --notes-file notes.md --apply  # 真发
```

脚本把下面全部六步固化成了流水线，并把本文的实证教训做成门禁：令牌扫描（含 `.git/config`
remote URL 内嵌凭据）、CHANGELOG 格式与 compare 链接校验、**正文单一来源双平台同发**、
双平台 API 差异封装、Release 创建后强制回查。默认 dry-run，`--apply` 才动真格。

本文档保留两用：脚本背后的**原理**（知其所以然才能改对），与脚本不可用时的**手动路径**。

> 实证教训（2026-11 六仓核查）：本文档 v0.1.0 就写了"正文同源以主仓为准"，但实际执行中
> reduce-ai 双平台正文 3/4 不同源、其中一版还含错误安装命令——**纯文档不产生标准化效果，
> 执行必须工具化**。以下流水线在双平台（GitCode 首发 + GitHub 镜像）实测走通过
> v0.1.0 → v0.3.0 多轮。

## 一、双平台架构

- 主仓库（权威首发）+ 镜像仓库（面向海外与 skills 生态——`npx skills add` 只认 GitHub，
  且其 Claude agent 名为 `claude-code` 不是 `claude`）。
- `origin` 挂双 pushurl：`git remote set-url --add --push origin <主仓>` 与
  `--add --push origin <镜像>` **各一次**（注意：无显式 pushurl 时第一条 `--add` 会整体
  替换默认 push 目标，必须成对添加——craft_cli 的 adopt 已处理）；之后
  `git push origin main --tags` 一条命令同步双平台，fetch 仍只走主仓。
- **禁止 remote URL 内嵌令牌**（`https://x-access-token:TOKEN@...` 形态）——活凭据躺在
  .git/config 明文里，check 扫描即 FAIL，adopt 可迁移。

## 二、发版流水线六步（标注脚本化状态）

1. **CHANGELOG 定版**【check 校验】：Keep a Changelog 格式，`[x.y.z] - 日期` 条目 + 文末 compare 链接；
2. **门禁**【check 执行】：自定义门禁命令（单测/构建）+ 令牌扫描 0 命中（平台前缀 + remote URL）；
3. **约定式提交** → **附注 tag**（message = 正文首段）→ `git push origin main --tags`【release 执行，弱网自动重试一次】；
4. **双平台 Release API 各创建一页**【release 执行】：**同一份正文文件发两边**（`--notes-file` 单一来源）；
5. **API 回查**【release 执行】确认两边 Release 真实存在（创建响应的 null 字段不代表失败，必须回查）；
6. **本机重装 + 版本自检**【release 打印指引】（doctor 首行 = 新 tag），闭环验证安装器版本戳。

## Release API 差异备忘

| 平台 | 认证方式 | 已知坑 |
|---|---|---|
| GitCode（v5，Gitee 兼容风格） | `PRIVATE-TOKEN` 请求头 | 令牌放 body 报 400 "private-token required"；**用户级枚举端点**（`/users/<u>/repos`）与仓库详情端点**未认证返回 400**，只有 releases 端点未认证可读；响应 id/html_url 为 null 属正常，网页地址按 `https://gitcode.com/{owner}/{repo}/releases/tag/{tag}` 拼 |
| GitHub REST | `Bearer` Authorization 头 | 无 TTY/弱网时偶发断连，重试即可 |

## 三、Release 正文标准（中文为主）

- **中文为主**（仓库创建的语言默认；英文段可选）。正文五件套：`改动内容 / 为什么 /
  实测 / 升级方式 / 契约`——`craft_cli.py release` 的骨架即此结构。
- 行文遵守 `release-copy.md`（去 AI 味规则，机器腔 lint 为警告级）。
- 升级指引要明确：幂等安装器重跑即更新；**用户配置与缓存在技能目录外，升级永不触碰**。

## 四、用户如何知道有新版（如实三渠道，别虚标）

1. 平台 Watch/Star 的 Release 通知；
2. 自检命令首行自报已装版本（版本闭环，用户与最新 tag 对比即知）；
3. README Update 章节。

**无自动检查更新是零遥测的自觉取舍**——如实标注，别假装有；要做就做 opt-in
（如 `doctor --check-update` 显式 GET Release API），绝不默认后台联网。

## 五、发版前检查清单（craft_cli check 已覆盖大部分）

- [ ] CHANGELOG 定版 + compare 链接【check】
- [ ] 门禁命令通过；令牌扫描 0 命中（含 remote URL）【check】
- [ ] Release 正文单一来源、五件套齐、机器腔 lint 过目【check --notes-file】
- [ ] 附注 tag；双 push 成功（两边远端 ref 一致）【release】
- [ ] 双平台 Release 创建 + 回查【release】
- [ ] 本机重装，doctor 版本戳 = 新 tag

## 六、实证教训（2026-11 六仓核查新增）

- **正文分叉必然出错**：reduce-ai v0.1.0 的 GitCode 版正文写了 `npx skills add <gitcode地址>`
  这条错误命令，与自家 v0.1.1 的"skills CLI 不识别 GitCode 地址"声明自相矛盾。每个平台
  各写一遍正文，错误就有机会只藏在一边——单一来源不是风格偏好，是防错机制。
- **手工建 Release 的滞留成本**：ds-search v0.1.0 的 GitHub Release 以草稿滞留 12.6 小时
  才发布；skill-craft v0.1.0 滞留 17 分钟。脚本化后此问题从构造上消失。
- **约定不校验就漂移**：同一作者同期仓库出现三种 remote 挂法、CHANGELOG 三态
  （有英文带链接 / 中文无链接 / 无）、tag 类型混用。方法论文档挡不住漂移，
  约定必须变成 check 门禁。
