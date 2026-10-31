# 工程陷阱清单：每条都是实测翻车换来的

写入 SKILL.md/README 的教训先于荣誉。以下每条坑都有对应的守护手段，新项目按清单预防。

## 一、Windows 编码与 PowerShell

| 坑 | 现象 | 规则 |
|---|---|---|
| .ps1 无 BOM + 含中文 | Windows PowerShell 5.1 按 ANSI/GBK 解析，直接语法报错（"字符串缺少终止符"） | .ps1 含非 ASCII 必须 UTF-8 **带 BOM**；.sh 绝不能带 BOM（破坏 shebang）。写成单测守护 |
| `$ErrorActionPreference='Stop'` + 原生命令 stderr 重定向 | `git ... 2>$null` 在 PS 5.1 抛终止性错误，非 git 副本（zip 安装）下安装器直接崩 | 原生命令探测期间临时放宽 EAP 为 Continue，完毕恢复；失败分支回退默认值 |
| PS 5.1 的 `Set-Content -Encoding utf8` | 写出带 BOM 的文件（PS 7 无 BOM），与 sh 版安装器产物格式不一致 | 用 `[System.IO.File]::WriteAllText()`，两代 PS 行为一致（无 BOM） |
| 记事本存的 .env 带 BOM | 脚本读取首个 key 名变 `\ufeffAPI_KEY` | 解析统一 `utf-8-sig` |

## 二、分发渠道与平台错配

| 坑 | 现象 | 规则 |
|---|---|---|
| 工具生态假设 ≠ 仓库托管地 | `npx skills add owner/repo` 只认 GitHub，仓库在其它平台时解析失败 | 渠道命令先本机实证再进 README；平台不同源时给 GitHub 镜像或换渠道 |
| skills CLI 的 agent 命名 | Claude 的 agent 名是 `claude-code` 不是 `claude` | 用其报错里列出的合法名单，别猜 |
| `npx skills add/update` 的清单机制 | update 靠 `skills-lock.json` 回源比对，只管 npx 装的副本 | README 按安装渠道分别写更新方式 |

## 三、网络现实（弱网环境）

- HTTPS 到 GitHub 偶发断流/超时而 SSH 22 可用：git 失败先重试；临时 HTTPS→SSH 重写用 `GIT_CONFIG_GLOBAL` 指向一次性配置文件（`[url "git@github.com:"] insteadOf = https://github.com/`），**不改全局 git 配置**。
- API POST 偶发 RemoteDisconnected：重试 2-3 次，间隔几秒。
- 长任务（clone）设 timeout，别让脚本无限挂起。

## 四、验证方法论

- **happy path 和回退路径都要测**：安装器要测"无 git 副本""目标目录已存在""非法参数"三条回退路径，不能只测干净环境。
- 目标解释器真跑：.ps1 用 `powershell.exe`（5.1）真执行，不是 `pwsh` 也不是"看起来对"。
- 子代理 = 全新会话等价物（技能发现在会话启动时固定），触发测试必须借它；注意供应商并发上限（约 3）与用量上限，大批量分批。
- 引用类输出对照缓存溯源（防幻觉 URL）；关键事实用第二个工具交叉核对。

## 五、令牌卫生

- 令牌值不进仓库、记忆、回显、日志、fixtures——代码只引用变量名。
- 提交前 grep 令牌模式（覆盖各平台前缀）。
- 聊天记录里明文出现过的令牌，正式对外前在平台控制台轮换。
