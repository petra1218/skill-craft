# 凭据设计：脚本怎么读，用户怎么配

技能没有标准的"密钥库"API——agentskills.io 规范的 frontmatter 只有 `name/description/license/compatibility/metadata/allowed-tools`。底层机制很简单：**技能脚本由 Agent 起 shell 子进程执行，继承 Agent 进程的环境变量**。环境可见性完全取决于 Agent 进程怎么被启动。因此凭据设计 = 脚本侧解析链 + 用户侧配置引导，两半都要。

## 一、脚本侧：四层解析链（可移植核心）

```
显式参数（-k/--api-key） > 进程环境变量 > 用户级配置 ~/.<工具名>/.env > 技能目录 .env
```

- **`.env` 文件是跨环境均衡器**：不管 Agent 怎么启动都在。解析必须 **BOM 容忍**（Windows 记事本存的 .env 带 BOM，`utf-8-sig` 读取；与 install.ps1 必须带 BOM 是同一个 Windows 病的两面）。
- **用户级配置放技能目录外**（`~/.<工具名>/.env`）：升级 = 覆盖技能目录，key 永不丢；技能目录 `.env` 只是兜底层。
- frontmatter 若要提示凭据，用规范的 `metadata:` map 或正文说明——**不要发明私有字段**（宽容解析器不报错，但非标准）。
- **skill-craft 自身的发版令牌即此链的活例**：`GITCODE_TOKEN`（回退 `ATOMGIT_TOKEN`）与
  `GITHUB_TOKEN`，推荐写用户级 `~/.skill-craft/.env`；`craft_cli.py doctor` 就是三态自检
  （未配置→三步指路 / 无效→去平台核对 / 有效→附实测延迟）。

### 各运行环境差异表

| 环境 | 现象 | 对策 |
|---|---|---|
| Windows `setx` | 只写注册表 HKCU\Environment，**已运行的 Agent 进程要重启才能看到** | 检测"配了但读不到"时补读用户级：PowerShell `GetEnvironmentVariable(name,'User')`，Python `winreg` 读 HKCU\Environment；这是平台附加项，不是基础链的一环 |
| macOS GUI 启动的 Agent | 不读 .zshrc，shell 环境缺失 | .env 文件兜底是唯一可靠路径 |
| 终端启动的 Agent | 继承 shell rc 的 export | 基础链即可 |
| 令牌被用户改名 | 环境变量名对不上 | 读不到时先枚举配置源里含 TOKEN 的变量再定位 |

### 安全不变式

.env 进 .gitignore；令牌值不进回显、日志、错误信息、记忆文件——代码里只引用变量名；聊天记录里明文出现过的令牌，建议用户在平台控制台轮换。

## 二、用户侧：首次配置引导四件套

用户"拿到链接 → 安装 → 配好"的体验由四个机制闭环，**技能负责"发现没配→指路→验证"，用户只负责"去平台拿一次 key"**：

1. **setup 向导**：一条交互命令完成"打印取 key 地址 → 接收粘贴 → 写入配置文件（chmod 600）→ **当场发一次最小真实调用验证** → 回显结果"。不验证的 setup 等于没配。
2. **错误即引导**：没配 key 时第一次调用，报错输出本身就是三步指引（取 key → 放哪 → 重试）。用户哪怕跳过 README 直接用，Agent 读到报错也能带他配完——配置方法因此能被自动传播。
3. **doctor 三态自检**：`未配置`（去 setup）/ `无效`（去平台核对）/ `有效`（附实测延迟），任何时刻可复查，输出直接给下一步动作。首行带版本号（配合版本闭环）。
4. **配置外置**：key 永远活在技能目录外，升级零丢失；README 写明这一点，用户才敢放心升级。

### 用户视角的三步（README 里照此写）

```
1. 安装：git clone <repo> && ./install.sh --agent=<x>
2. 配置（三选一）：
   A. python <skill_dir>/scripts/cli.py setup        # 交互向导（推荐）
   B. echo "API_KEY=xxx" > ~/.<工具名>/.env           # 手动
   C. setx API_KEY xxx                                # 环境变量
3. 验证：python <skill_dir>/scripts/cli.py doctor    # → 三态输出
```

## 三、检查清单（新技能接入凭据时逐条过）

- [ ] 四层解析链实现且顺序文档化
- [ ] .env 解析 BOM 容忍
- [ ] 无 key 报错 = 三步指引（给 Agent 读）
- [ ] setup 含真实调用验证
- [ ] doctor 三态 + 首行版本
- [ ] 用户级配置在技能目录外
- [ ] .gitignore 覆盖 .env；全仓 grep 令牌模式为 0
- [ ] remote URL 不内嵌令牌（`craft_cli.py check` 扫描守护）
- [ ] README 有配置三步 + Update 章节（声明 key 不受升级影响）
