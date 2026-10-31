# 发布流水线：从 CHANGELOG 到版本戳验证

**发布 ≠ 推送**：push 只是代码到远端；"发布" = 版本化（CHANGELOG）+ tag + Release 页 + 升级指引，四件套齐才算发完。以下流水线在双平台（GitCode 首发 + GitHub 镜像）实测走通过三轮（v0.1.0 → v0.1.3）。

## 一、双平台架构

- 主仓库（权威首发）+ 镜像仓库（面向海外与 skills 生态——`npx skills add` 只认 GitHub，且其 Claude agent 名为 `claude-code` 不是 `claude`）。
- `origin` 挂双 pushurl：`git remote set-url --add --push origin <主仓>` 与 `--add --push origin <镜像>` 各一次；之后 `git push origin main --tags` 一条命令同步双平台，fetch 仍只走主仓。

## 二、发版流水线（每次版本固定动作）

1. **CHANGELOG 定版**：Keep a Changelog 格式，新增 `[x.y.z] - 日期` 条目 + 各版本 compare 链接；
2. **门禁**：单测全绿 + 令牌扫描 0 命中（模式覆盖自家平台前缀，如 `sk-`、`ghp_`）；
3. **约定式提交** → 打 tag → `git push origin main --tags`（双平台一次推）；
4. **双平台 Release API 各创建一页**，正文同源（以主仓版为准复制到镜像）；
5. **API 回查**确认两边 Release 真实存在（创建响应的 null 字段不代表失败，必须回查）；
6. **本机重装 + 版本自检**（doctor 首行 = 新 tag），闭环验证安装器版本戳。

### Release API 差异备忘

| 平台 | 认证方式 | 已知坑 |
|---|---|---|
| GitCode（v5，Gitee 兼容风格） | `PRIVATE-TOKEN` 请求头 | 令牌放 body 报 400 "private-token required"；响应 id/html_url 为 null 属正常，网页地址按 `https://gitcode.com/{owner}/{repo}/releases/tag/{tag}` 拼 |
| GitHub REST | `Bearer` Authorization 头 | 无 TTY/弱网时偶发断连，重试即可 |

## 三、Release notes 内容公式（双语）

```
改了什么 / 为什么（含根因一句话）/ 实测了什么 / 升级方式（git pull + 重跑安装器）/ 契约是否变更
```

升级指引要明确：幂等安装器重跑即更新；**用户配置与缓存在技能目录外，升级永不触碰**。

## 四、用户如何知道有新版（如实三渠道，别虚标）

1. 平台 Watch/Star 的 Release 通知；
2. 自检命令首行自报已装版本（版本闭环，用户与最新 tag 对比即知）；
3. README Update 章节。

**无自动检查更新是零遥测的自觉取舍**——如实标注，别假装有；要做就做 opt-in（如 `doctor --check-update` 显式 GET Release API），绝不默认后台联网。

## 五、发版前检查清单

- [ ] CHANGELOG 定版 + compare 链接
- [ ] 单测全绿；令牌扫描 0 命中
- [ ] README 命令全部本机实证过（未实证的要么删要么标"未验证"）
- [ ] tag 已打；双 push 成功（两边远端 ref 一致）
- [ ] 双平台 Release 创建 + 回查
- [ ] 本机重装，doctor 版本戳 = 新 tag
