#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""craft_cli —— skill-craft 的标准化发布 CLI。

能力：init（中文默认脚手架）/ check（发版前体检）/ release（双平台发版流水线）/
adopt（既有仓库纳入标准）/ doctor（自检）。

设计约定（见 references/ 下各文档）：
- 纯标准库单文件，Python 3.7+，零第三方依赖；
- 输出首行带 contract 版本，供下游 Agent 解析；
- 错误输出写给 Agent 读：给出可执行的修复指引，不需要人守着；
- 发布类命令默认 dry-run，--apply 才真执行（发布是外向动作）；
- 令牌永不回显：扫描命中只报文件与行号，不报值。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

CONTRACT = "v1"
SKILL_NAME = "skill-craft"
EXIT_OK = 0      # 全部通过（或仅警告）
EXIT_FAIL = 1    # 体检/发版有硬性失败项
EXIT_USAGE = 2   # 用法/配置错误（Agent 可按指引修复）

GITHUB_API = "https://api.github.com"
GITCODE_API = "https://gitcode.com/api/v5"

TOKEN_ENV = {
    "gitcode": ["GITCODE_TOKEN", "ATOMGIT_TOKEN"],
    "github": ["GITHUB_TOKEN", "GH_TOKEN"],
}


# ---------------------------------------------------------------- 输出

def _safe_stdio():
    # 写侧：编码跟随平台（Windows 管道默认 GBK），只把 errors 设为 replace 防
    # UnicodeEncodeError 崩溃——强制 UTF-8 输出在 GBK 消费端反而全乱码（实测教训，
    # 见 pitfalls.md）；确需 UTF-8 的终端设 PYTHONIOENCODING=utf-8。
    # 读侧（.env / CHANGELOG / 正文）统一 utf-8-sig，BOM 容忍。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def say(msg=""):
    print(msg)


def ok(msg):
    print("[ OK ] " + msg)


def warn(msg):
    print("[WARN] " + msg)


def fail(msg):
    print("[FAIL] " + msg)


def info(msg):
    print("[INFO] " + msg)


def die(msg, code=EXIT_USAGE):
    print("[FAIL] " + msg)
    sys.exit(code)


# ---------------------------------------------------------------- 配置与令牌

def skill_root():
    """技能根目录 = 本脚本所在 scripts/ 的上一级。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_env_file(path):
    """BOM 容忍的 .env 解析（utf-8-sig）。返回 dict，坏行跳过。"""
    data = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip("'\"")
                if key:
                    data[key] = val
    except OSError:
        pass
    return data


def read_runtime_conf(root=None):
    conf = {}
    path = os.path.join(root or skill_root(), "runtime.conf")
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for line in fh:
                if ":" in line:
                    key, _, val = line.partition(":")
                    conf[key.strip()] = val.strip()
    except OSError:
        pass
    return conf


def resolve_token(platform, explicit=None):
    """四层解析链：显式参数 > 进程环境变量 > 用户级 ~/.skill-craft/.env > 技能目录 .env。

    返回 (token or None, 来源说明 or None)。令牌值不进任何日志。
    """
    if explicit:
        return explicit, "--token 参数"
    candidates = TOKEN_ENV.get(platform, [])
    for name in candidates:
        val = os.environ.get(name)
        if val:
            return val, "环境变量 " + name
    for env_path in (
        os.path.join(os.path.expanduser("~"), "." + SKILL_NAME, ".env"),
        os.path.join(skill_root(), ".env"),
    ):
        data = read_env_file(env_path)
        for name in candidates:
            if data.get(name):
                return data[name], "%s 的 %s" % (env_path, name)
    return None, None


def token_guide(platform):
    """未配置令牌时的三步指引（给 Agent 读，Agent 可直接带用户走完）。"""
    where = os.path.join(os.path.expanduser("~"), "." + SKILL_NAME, ".env")
    env_names = " 或 ".join(TOKEN_ENV.get(platform, []))
    if platform == "gitcode":
        step1 = "1) 打开 https://gitcode.com → 个人设置 → 访问令牌，生成一枚令牌（勾选 projects/API 权限）"
    else:
        step1 = "1) 打开 https://github.com/settings/tokens 生成一枚 token（勾选 repo 权限）"
    return (
        "未找到 %s 平台令牌。配置三步：\n%s\n"
        "2) 写入用户级配置（推荐，升级技能不丢）：echo \"%s=你的令牌\" > \"%s\"\n"
        "   （或临时用环境变量 %s；Windows setx 对已运行的 Agent 进程不可见，需重启 Agent，.env 文件更稳）\n"
        "3) 重新运行本命令验证。" % (platform, step1, TOKEN_ENV[platform][0], where, env_names)
    )


# ---------------------------------------------------------------- git 薄封装

def git(repo, *args):
    """跑 git，返回 (rc, stdout, stderr)。输出按 UTF-8 解码（防 GBK 管道坑）。"""
    proc = subprocess.run(
        ["git", "-C", repo] + list(args), capture_output=True
    )
    out = proc.stdout.decode("utf-8", "replace") if proc.stdout else ""
    err = proc.stderr.decode("utf-8", "replace") if proc.stderr else ""
    return proc.returncode, out, err


def git_available():
    return subprocess.run(["git", "--version"], capture_output=True).returncode == 0


def tag_dates(repo):
    """{tag: yyyy-mm-dd}，按打 tag 日期。"""
    rc, out, _ = git(repo, "for-each-ref", "refs/tags",
                     "--sort=creatordate",
                     "--format=%(refname:short) %(creatordate:short)")
    dates = {}
    if rc == 0:
        for line in out.splitlines():
            parts = line.strip().split(" ")
            if len(parts) == 2:
                dates[parts[0]] = parts[1]
    return dates


def tag_is_annotated(repo, tag):
    rc, out, _ = git(repo, "cat-file", "-t", tag)
    return rc == 0 and out.strip() == "tag"


def repo_state(repo):
    """收集仓库状态（只读）。"""
    st = {"repo": os.path.abspath(repo), "is_git": False}
    rc, out, _ = git(repo, "rev-parse", "--is-inside-work-tree")
    st["is_git"] = rc == 0 and out.strip() == "true"
    if not st["is_git"]:
        return st
    rc, out, _ = git(repo, "status", "--porcelain")
    st["dirty_files"] = [l.strip() for l in out.splitlines() if l.strip()]
    rc, out, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    st["branch"] = out.strip() if rc == 0 and out.strip() else None
    _, out, _ = git(repo, "tag", "-l")
    st["tags"] = sorted(
        [t.strip() for t in out.splitlines() if t.strip()], key=ver_key
    )
    # remotes：fetch url + pushurls（含所有具名 remote）
    _, out, _ = git(repo, "config", "--get-regexp", r"^remote\..*\.(url|pushurl)$")
    remotes = {}
    for line in out.splitlines():
        m = re.match(r"^remote\.([^.]+)\.(url|pushurl)\s+(.+)$", line.strip())
        if not m:
            continue
        name, kind, url = m.group(1), m.group(2), m.group(3).strip()
        entry = remotes.setdefault(name, {"url": None, "pushurls": []})
        if kind == "url":
            entry["url"] = url
        else:
            entry["pushurls"].append(url)
    st["remotes"] = remotes
    origin = remotes.get("origin")
    st["origin"] = origin
    if origin:
        push_targets = list(origin["pushurls"]) or ([origin["url"]] if origin["url"] else [])
        st["push_platforms"] = sorted(
            {p for p in (detect_platform(u) for u in push_targets) if p}
        )
    else:
        st["push_platforms"] = []
    st["type"] = "skill" if os.path.isfile(
        os.path.join(st["repo"], "skills", "SKILL.md")
    ) or _has_skills_dir(st["repo"]) else "app"
    return st


def _has_skills_dir(repo):
    skills_dir = os.path.join(repo, "skills")
    if not os.path.isdir(skills_dir):
        return False
    for name in os.listdir(skills_dir):
        if os.path.isfile(os.path.join(skills_dir, name, "SKILL.md")):
            return True
    return False


# ---------------------------------------------------------------- 版本号

def parse_ver(v):
    s = str(v).strip().lstrip("vV")
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.\-]+))?$", s)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))


def ver_key(v):
    pv = parse_ver(v)
    if pv is None:
        return (0, 0, 0, False, "")
    # 同版本号下，正式版 > 预发布版（pre 为 None 时该元素为 True，排序更高）
    return (pv[0], pv[1], pv[2], pv[3] is None, pv[3] or "")


def is_newer(new, old):
    return ver_key(new) > ver_key(old)


def dirty_only_changelog(dirty):
    """porcelain 状态行列表是否全部只涉及 CHANGELOG.md（可并入发版提交）。"""
    def path_of(line):
        return line.split(None, 1)[-1] if line.split() else ""
    return bool(dirty) and all(path_of(d) == "CHANGELOG.md" for d in dirty)


def bump_version(latest, part):
    if latest is None:
        return "v0.1.0"
    pv = parse_ver(latest)
    if pv is None:
        return "v0.1.0"
    ma, mi, pa = pv[0], pv[1], pv[2]
    if part == "major":
        ma, mi, pa = ma + 1, 0, 0
    elif part == "minor":
        mi, pa = mi + 1, 0
    else:
        pa += 1
    return "v%d.%d.%d" % (ma, mi, pa)


# ---------------------------------------------------------------- 令牌扫描（纯函数）

TOKEN_PATTERNS = [
    ("DeepSeek API key（sk- 前缀）", re.compile(r"sk-[a-fA-F0-9]{16,}")),
    ("GitHub PAT（ghp_ 前缀）", re.compile(r"ghp_[A-Za-z0-9]{16,}")),
    ("GitHub fine-grained PAT", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("GitLab token（glpat- 前缀）", re.compile(r"glpat-[A-Za-z0-9\-_]{16,}")),
    ("URL 内嵌凭据", re.compile(r"https?://[^/@\s]+:[A-Za-z0-9_\-]{8,}@")),
]


def redact_line(text):
    """把命中的令牌/凭据替换为 <已隐藏>，永不回显值。"""
    for _, rx in TOKEN_PATTERNS:
        text = rx.sub("<已隐藏>", text)
    return text


def scan_text_for_tokens(text):
    """返回 [(行号, 模式名)]。"""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx in TOKEN_PATTERNS:
            if rx.search(line):
                hits.append((lineno, name))
                break
    return hits


# 口令部分须形如真实凭据（≥8 位凭据字符集）——文档里的 x-access-token:TOKEN 这类
# 短占位示例不会被误报（实证教训：自己的扫描器先扫到了自己的文档示例）。
URL_CRED_RX = re.compile(r"https?://[^/@\s]+:[A-Za-z0-9_\-]{8,}@")


def scan_remote_urls(remotes):
    """扫描 remote URL 内嵌凭据。返回 [(remote名, 用途, 脱敏URL)]。"""
    findings = []
    for name, entry in remotes.items():
        for kind, urls in (("fetch url", [entry["url"]] if entry["url"] else []),
                           ("pushurl", entry["pushurls"])):
            for url in urls:
                if URL_CRED_RX.search(url):
                    findings.append((name, kind, redact_url(url)))
    return findings


def redact_url(url):
    return URL_CRED_RX.sub(lambda m: re.sub(r"(://[^:/@\s]+:)[^@/\s]+(@)", r"\1***\2", m.group(0)), url)


def detect_platform(url):
    if not url:
        return None
    if "gitcode.com" in url:
        return "gitcode"
    if "github.com" in url:
        return "github"
    return None


def parse_slug(url):
    """从 remote URL 提取 (owner, repo)。支持 git@host:o/r.git 与 https://host/o/r。"""
    m = re.search(r"[:/]([^/:@]+?)/([^/:@]+?)(?:\.git)?/?$", url or "")
    if not m:
        return None
    return m.group(1), m.group(2)


def to_ssh_url(url):
    """https URL（含内嵌凭据的）转 SSH 形态：git@host:owner/repo.git。"""
    u = url or ""
    m = re.search(r"https?://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?/?$", u)
    if m:
        host = re.sub(r"^[^/@]+@", "", m.group(1))  # 剥掉 user:token@ 前缀
    else:
        m = re.search(r"git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?/?$", u)
        if not m:
            return None
        host = m.group(1)
    return "git@%s:%s/%s.git" % (host, m.group(2), m.group(3))


# ---------------------------------------------------------------- 机器腔 lint（纯函数，警告级）

LINT_RULES = [
    ("营销形容词", re.compile(
        r"强大|高效|优雅|轻松(实现|上手|搞定)?|惊人|卓越|一站式|全方位|端到端|赋能|抓手|深度融合|有机结合")),
    ("空泛开场", re.compile(
        r"随着[^\n，。]{0,12}的(快速|迅速)发展|众所周知|不言而喻|值得注意的是|需要指出的是")),
    ("万能动词框架", re.compile(
        r"进行了[^\n，。]{0,6}(分析|研究|探讨|优化|实现|测试)|实现了[^\n，。]{0,10}的提升"
        r"|奠定了[^\n，。]{0,6}基础|提供了有力支撑")),
    ("排比触发器", re.compile(r"不仅[^。\n]{1,20}而且|既[^。\n]{1,12}又[^。\n]{1,12}更")),
    ("四字连排", re.compile(r"[\u4e00-\u9fa5]{4}(?:、[\u4e00-\u9fa5]{4}){2,}")),
    ("点题说教", re.compile(
        r"这(充分)?(标志|说明|意味着)[^\n。]{0,24}(新阶段|新纪元|里程碑)|由此可见|综上所述")),
]

EMOJI_RX = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]")


def lint_copy(text):
    """机器腔提示（警告级，不阻断）。返回 [(行号, 类别, 片段)]。词表：references/vocabulary.md。"""
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#") and EMOJI_RX.search(stripped):
            hits.append((lineno, "标题带 emoji", stripped[:20]))
        for name, rx in LINT_RULES:
            m = rx.search(line)
            if m:
                hits.append((lineno, name, m.group(0)[:20]))
    return hits


# ---------------------------------------------------------------- CHANGELOG 解析（纯函数）

def parse_changelog(text):
    """返回 (条目列表, {版本: 链接})。条目 = {version, date, body}。"""
    entries, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^##\s*\[([^\]]+)\](?:\s*[-–—]\s*(.+))?\s*$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {"version": m.group(1).strip(), "date": (m.group(2) or "").strip(), "body": []}
            continue
        if re.match(r"^#\s", line):
            if cur is not None:
                entries.append(cur)
            cur = None
            continue
        if cur is not None:
            cur["body"].append(line)
    if cur is not None:
        entries.append(cur)
    for e in entries:
        # 去掉尾部空行与误收入正文的链接定义行
        while e["body"] and (not e["body"][-1].strip()
                             or re.match(r"^\[[^\]]+\]:\s*\S+", e["body"][-1])):
            e["body"].pop()
    links = dict(
        (m.group(1), m.group(2))
        for m in re.finditer(r"^\[([^\]]+)\]:\s*(\S+)", text, re.M)
    )
    return entries, links


def changelog_entry(text, version):
    entries, _ = parse_changelog(text)
    want = str(version).lstrip("vV")
    for e in entries:
        if e["version"].lstrip("vV") == want:
            return e
    return None


def check_changelog_gates(text):
    """CHANGELOG 门禁（纯函数）。返回 (失败列表, 警告列表)。"""
    fails, warns = [], []
    if not text.strip():
        return (["CHANGELOG.md 不存在或为空。修复：新仓库用 `craft_cli.py init`，既有仓库用 `craft_cli.py adopt` 补齐。"], [])
    entries, links = parse_changelog(text)
    versions = [e["version"] for e in entries]
    if "Unreleased" not in versions:
        fails.append("CHANGELOG.md 缺少 `## [Unreleased]` 小节（Keep a Changelog 格式）。")
    if not entries:
        fails.append("CHANGELOG.md 没有任何版本条目。")
    if not any("/compare/" in u or "/releases/tag/" in u for u in links.values()):
        warns.append("CHANGELOG.md 文末缺少版本 compare 链接。修复：`craft_cli.py adopt` 可从 tag 历史自动生成。")
    return fails, warns


# ---------------------------------------------------------------- Release 正文（纯函数）

def build_notes_skeleton(version, changelog_section=None):
    """从 CHANGELOG 小节生成中文正文骨架；缺口用（待补：…）标注，apply 前必须填完。"""
    body = (changelog_section or "").strip() or "（待补：本版改动列表）"
    today = datetime.date.today().isoformat()
    return (
        "## {v} · （待补：一句话标题）\n"
        "\n"
        "{date} 发布。\n"
        "\n"
        "### 改动内容\n"
        "\n"
        "{body}\n"
        "\n"
        "### 为什么\n"
        "\n"
        "（待补：根因或动机，一两句）\n"
        "\n"
        "### 实测\n"
        "\n"
        "（待补：跑了什么验证、结果如何；没实测的不写）\n"
        "\n"
        "### 升级方式\n"
        "\n"
        "（待补：按安装渠道分别写，如 git pull + 重跑安装器 / npx skills update / 下载新版）\n"
        "\n"
        "### 契约\n"
        "\n"
        "（待补：输出契约是否变更；破坏性变更升主版本号）\n"
    ).format(v=version, date=today, body=body)


def validate_notes(notes):
    """apply 前的正文硬校验。返回失败列表。"""
    fails = []
    if not notes or not notes.strip():
        return ["Release 正文为空。"]
    if "待补" in notes:
        fails.append("正文仍有（待补：…）占位——填完再 --apply。")
    if not re.search(r"升级|Update|更新", notes, re.I):
        fails.append("正文缺『升级方式』内容——用户靠它升级。")
    return fails


def notes_title(notes, fallback):
    m = re.search(r"^#{1,3}\s+(.+)$", notes, re.M)
    return m.group(1).strip() if m else fallback


# ---------------------------------------------------------------- 发版计划（纯函数）

def build_release_plan(state, version, notes_path, has_notes_file):
    """构造发版步骤与前置错误（纯函数，可测）。"""
    errors, steps = [], []
    if not state.get("is_git"):
        errors.append("目标目录不是 git 仓库。")
        return errors, steps
    dirty = state.get("dirty_files") or []
    only_changelog = dirty_only_changelog(dirty)
    if dirty and not only_changelog:
        errors.append("工作树有未提交变更（%d 处，含非 CHANGELOG 文件）。先提交或暂存。" % len(dirty))
    if version in (state.get("tags") or []):
        errors.append("tag %s 已存在，版本号必须更新。" % version)
    latest = (state.get("tags") or [None])[-1]
    if latest and not is_newer(version, latest):
        errors.append("版本 %s 不高于最新 tag %s。" % (version, latest))
    if not state.get("branch"):
        errors.append("当前分支未知（可能是空仓库），无可推送内容。")
    platforms = state.get("push_platforms") or []
    if not platforms:
        errors.append("origin 没有可用的推送目标。修复：`craft_cli.py adopt <repo> --gitcode <url> --github <url>`。")
    if only_changelog:
        steps.append("提交发版提交：git add CHANGELOG.md && git commit -m \"chore: release %s\"" % version)
    steps.append("打附注 tag：git tag -a %s -m <正文首段>" % version)
    steps.append("双平台推送：git push origin %s --tags" % state.get("branch"))
    for p in platforms:
        steps.append("创建 %s Release（与另一平台同一份正文）" % p)
        steps.append("回查 %s Release 存在" % p)
    if state.get("type") == "skill":
        steps.append("打印本机重装 + 版本戳验证指引")
    return errors, steps


# ---------------------------------------------------------------- HTTP

def http_json(method, url, headers=None, payload=None, timeout=20, retries=3):
    """带重试的 JSON 请求。返回 (status, data_or_None, 错误说明_or_None)。4xx 不重试。"""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Accept", "application/json")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, (json.loads(raw) if raw.strip() else None), None
                except ValueError:
                    return resp.status, None, "响应不是合法 JSON"
        except urllib.error.HTTPError as e:
            raw = ""
            try:
                raw = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            if e.code >= 500 and attempt < retries - 1:
                last_err = "HTTP %d" % e.code
                time.sleep(2)
                continue
            return e.code, None, (raw[:200] or ("HTTP %d" % e.code))
        except Exception as e:  # 网络抖动/超时：退避重试（pitfalls.md）
            last_err = "%s: %s" % (type(e).__name__, e)
            if attempt < retries - 1:
                time.sleep(2)
    return None, None, "网络错误（已重试 %d 次）：%s" % (retries, last_err)


# ---------------------------------------------------------------- 模板渲染（init 用，纯函数）

def render_readme(ctx):
    lines = [
        "# " + ctx["name"],
        "",
        "（待补：一两句话——这个仓库是什么、给谁解决什么问题。不写营销词。）",
        "",
    ]
    if ctx["type"] == "skill":
        lines += [
            "## 安装",
            "",
            "```bash",
            "git clone <仓库地址>",
            "cd " + ctx["name"],
            "./install.sh --agent=zcode     # Windows: .\\install.ps1 -Agent zcode",
            "```",
            "",
            "安装器幂等：更新 = `git pull` 后重跑安装器。",
            "",
        ]
    else:
        lines += [
            "## 下载",
            "",
            "各版本产物见 Releases 页面：`<GitCode 仓库地址>/releases`。",
            "",
        ]
    lines += [
        "## 更新",
        "",
        "（待补：按安装渠道分别写。声明用户配置是否受升级影响。）",
        "",
        "## 许可证",
        "",
        "MIT",
        "",
    ]
    return "\n".join(lines)


def render_changelog(ctx):
    base = ctx.get("base_url") or "https://gitcode.com/<owner>/" + ctx["name"]
    return (
        "# 变更日志\n"
        "\n"
        "格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，"
        "版本号遵循语义化版本。\n"
        "\n"
        "## [Unreleased]\n"
        "\n"
        "---\n"
        "\n"
        "[Unreleased]: {base}/compare/HEAD\n"
        "\n"
        "> 首个版本发布时：把 Unreleased 改写为 `## [0.1.0] - 日期`，"
        "并在文末按 `{base}/releases/tag/vX.Y.Z` 补 compare/发布链接。\n"
    ).format(base=base)


def render_skill_md(ctx):
    return (
        "---\n"
        "name: {name}\n"
        "description: >-\n"
        "  （待补：做什么 + 何时触发 + 用户会说的原话变体。这是唯一常驻上下文的触发信号，\n"
        "  必须主动、带钩子；宁过勿缺。参考 skills/skill-craft/SKILL.md 第一节。）\n"
        "---\n"
        "\n"
        "# {name}\n"
        "\n"
        "（待补：给模型读的行为说明。规则带理由、配示例；细节按情境放 references/。）\n"
    ).format(name=ctx["name"])


def render_runtime_conf():
    return "Runtime: Markdown\nVersion: dev\n"


def render_gitignore():
    return (
        "# 密钥与环境\n"
        ".env\n"
        "*.env\n"
        "!.env.example\n"
        "\n"
        "# Python\n"
        "__pycache__/\n"
        "*.pyc\n"
        "\n"
        "# 系统杂项\n"
        ".DS_Store\n"
        "Thumbs.db\n"
    )


def render_license(ctx):
    year = datetime.date.today().year
    return (
        "MIT License\n"
        "\n"
        "Copyright (c) %d %s\n"
        "\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n"
        "\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n"
        "\n"
        "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
        "SOFTWARE.\n"
    ) % (year, ctx.get("author") or ctx["name"])


def render_install_sh(ctx):
    # 与本仓库 install.sh 同模式：幂等、多 Agent 落位、git describe 版本戳。
    return """#!/usr/bin/env bash
# {name} 安装器：把 skills/{name}/ 复制到各 Agent 技能目录。幂等：重跑即覆盖更新。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
SRC="$SCRIPT_DIR/skills/{name}"
SKILL_NAME="{name}"
VERSION="$(git -C "$SCRIPT_DIR" describe --tags 2>/dev/null || echo dev)"

target_dir() {{
  case "$1" in
    zcode)     echo "$HOME/.agents/skills/$SKILL_NAME" ;;
    claude)    echo "$HOME/.claude/skills/$SKILL_NAME" ;;
    codex)     echo "$HOME/.codex/skills/$SKILL_NAME" ;;
    cursor)    echo "$HOME/.claude/skills/$SKILL_NAME" ;;
    codebuddy) echo "$HOME/.codebuddy/skills/$SKILL_NAME" ;;
    workbuddy) echo "$HOME/.workbuddy/skills/$SKILL_NAME" ;;
    reasonx)   echo "$HOME/.reasonx/skills/$SKILL_NAME" ;;
    *) return 1 ;;
  esac
}}

install_to() {{
  local agent="$1" dest="$2"
  [ -d "$dest" ] && echo "[$agent] 覆盖安装: $dest" || echo "[$agent] 全新安装: $dest"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -r "$SRC" "$dest"
  printf 'Runtime: Markdown\\nVersion: %s\\n' "$VERSION" > "$dest/runtime.conf"
  [ -f "$dest/SKILL.md" ] || {{ echo "[$agent] 错误: 安装不完整" >&2; exit 1; }}
  echo "[$agent] 完成（版本 $VERSION）"
}}

[ -f "$SRC/SKILL.md" ] || {{ echo "错误: 未找到 $SRC（请在仓库根目录运行）" >&2; exit 1; }}

case "${{1:-}}" in
  --agent=zcode|--agent=claude|--agent=codex|--agent=cursor|--agent=codebuddy|--agent=workbuddy|--agent=reasonx)
    a="${{1#--agent=}}"; install_to "$a" "$(target_dir "$a")" ;;
  --agent=all)
    for a in zcode claude codex cursor codebuddy workbuddy reasonx; do install_to "$a" "$(target_dir "$a")"; done ;;
  *) echo "用法: ./install.sh --agent=<zcode|claude|codex|cursor|codebuddy|workbuddy|reasonx|all>"; exit 1 ;;
esac
""".format(name=ctx["name"])


def render_install_ps1(ctx):
    # 注意：返回值首字符是 BOM（\ufeff）——Windows PowerShell 5.1 对无 BOM 的
    # 含中文 .ps1 按 GBK 解析会语法报错（pitfalls.md）。调用方须以带 BOM 的 UTF-8 写盘。
    return """\ufeff# {name} 安装器（Windows PowerShell）。幂等：重跑即覆盖更新。
# 用法: .\\install.ps1 -Agent zcode   （zcode|claude|codex|cursor|codebuddy|workbuddy|reasonx|all）
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("zcode", "claude", "codex", "cursor", "codebuddy", "workbuddy", "reasonx", "all")]
  [string]$Agent
)

$ErrorActionPreference = "Stop"
$Src = Join-Path $PSScriptRoot "skills\\{name}"
$SkillName = "{name}"

# PS 5.1 下 EAP=Stop 时原生命令 stderr 重定向会抛终止性错误，探测 git 期间临时放宽。
$Version = "dev"
if (Get-Command git -ErrorAction SilentlyContinue) {{
  $ErrorActionPreference = "Continue"
  $Version = git -C $PSScriptRoot describe --tags 2>$null
  $ErrorActionPreference = "Stop"
  if (-not $Version) {{ $Version = "dev" }}
}}

if (-not (Test-Path (Join-Path $Src "SKILL.md"))) {{
  Write-Error "错误: 未找到 $Src（请在仓库根目录运行）"
}}

function Get-TargetDir([string]$Name) {{
  switch ($Name) {{
    "zcode"     {{ Join-Path $HOME ".agents\\skills\\$SkillName" }}
    "claude"    {{ Join-Path $HOME ".claude\\skills\\$SkillName" }}
    "codex"     {{ Join-Path $HOME ".codex\\skills\\$SkillName" }}
    "cursor"    {{ Join-Path $HOME ".claude\\skills\\$SkillName" }}
    "codebuddy" {{ Join-Path $HOME ".codebuddy\\skills\\$SkillName" }}
    "workbuddy" {{ Join-Path $HOME ".workbuddy\\skills\\$SkillName" }}
    "reasonx"   {{ Join-Path $HOME ".reasonx\\skills\\$SkillName" }}
  }}
}}

$Targets = if ($Agent -eq "all") {{ @("zcode","claude","codex","cursor","codebuddy","workbuddy","reasonx") }} else {{ @($Agent) }}

foreach ($t in $Targets) {{
  $Dest = Get-TargetDir $t
  if (Test-Path $Dest) {{ Write-Host "[$t] 覆盖安装: $Dest" }} else {{ Write-Host "[$t] 全新安装: $Dest" }}
  New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
  Remove-Item -Recurse -Force $Dest -ErrorAction SilentlyContinue
  Copy-Item -Recurse -Force $Src $Dest
  [System.IO.File]::WriteAllText((Join-Path $Dest "runtime.conf"), "Runtime: Markdown`nVersion: $Version")
  if (-not (Test-Path (Join-Path $Dest "SKILL.md"))) {{ Write-Error "[$t] 错误: 安装不完整" }}
  Write-Host "[$t] 完成（版本 $Version）"
}}
""".format(name=ctx["name"])


# ---------------------------------------------------------------- 子命令：init

def cmd_init(args):
    target = os.path.abspath(args.dir)
    if os.path.exists(target) and os.listdir(target):
        die("目标目录非空：%s" % target)
    os.makedirs(target, exist_ok=True)

    gitcode = to_ssh_url(args.gitcode) if args.gitcode else None
    github = to_ssh_url(args.github) if args.github else None
    base_url = ("https://gitcode.com/%s/%s" % parse_slug(gitcode)) if gitcode else None
    author = None
    if git_available():
        _, out, _ = git(target if os.path.isdir(target) else ".", "config", "--get", "user.name")
        author = out.strip() or None
    ctx = {
        "name": args.name,
        "type": args.type,
        "base_url": base_url,
        "author": author or args.name,
    }

    writes = {
        "README.md": render_readme(ctx),
        "CHANGELOG.md": render_changelog(ctx),
        "LICENSE": render_license(ctx),
        ".gitignore": render_gitignore(),
    }
    if args.type == "skill":
        skill_dir = os.path.join("skills", args.name)
        writes[os.path.join(skill_dir, "SKILL.md")] = render_skill_md(ctx)
        writes[os.path.join(skill_dir, "runtime.conf")] = render_runtime_conf()
        writes["install.sh"] = render_install_sh(ctx)
        writes["install.ps1"] = render_install_ps1(ctx)
    for rel, content in writes.items():
        path = os.path.join(target, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if rel.endswith(".ps1"):
            with open(path, "wb") as fh:  # ps1 必须带 BOM（pitfalls.md）
                fh.write(content.encode("utf-8"))
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
        info("生成 %s" % rel)

    if git_available() and not os.path.isdir(os.path.join(target, ".git")):
        git(target, "init")
        info("git init 完成")
    if gitcode:
        git(target, "remote", "add", "origin", gitcode)
        git(target, "remote", "set-url", "--add", "--push", "origin", gitcode)
        if github:
            git(target, "remote", "set-url", "--add", "--push", "origin", github)
        info("remote 已挂载：origin fetch=%s，push×%d" % (gitcode, 2 if github else 1))

    say()
    ok("脚手架完成：%s（类型 %s，语言中文默认）" % (target, args.type))
    lint = lint_copy(writes["README.md"])
    if lint:
        for lineno, cat, _ in lint:
            warn("README 第 %d 行命中机器腔词表（%s）——模板占位文案请按 references/release-copy.md 改写" % (lineno, cat))
    say("下一步：填充内容 → 首次发版 `python craft_cli.py release %s --version v0.1.0`（默认 dry-run）" % target)
    return EXIT_OK


# ---------------------------------------------------------------- 子命令：check

def _fmt_gate_counters(counters):
    return "—— 体检结果：失败 %d / 警告 %d / 通过 %d" % (
        counters["fail"], counters["warn"], counters["ok"])


def run_check(repo, notes=None, gates=None, strict_dirty=False):
    """执行全部门禁，返回退出码。notes 为待 lint 的正文文本，gates 为用户命令列表。"""
    counters = {"ok": 0, "warn": 0, "fail": 0}
    state = repo_state(repo)
    if not state.get("is_git"):
        fail("不是 git 仓库：%s。修复：git init，或确认路径。" % state.get("repo", repo))
        return EXIT_FAIL
    say("仓库：%s（类型 %s）" % (state["repo"], state["type"]))

    # 工作树
    dirty = state.get("dirty_files") or []
    if not dirty:
        ok("工作树干净")
        counters["ok"] += 1
    else:
        msg = "工作树有未提交变更 %d 处" % len(dirty)
        if strict_dirty:
            fail(msg + "（发版要求干净，或仅 CHANGELOG.md 待提交）")
            counters["fail"] += 1
        else:
            warn(msg)
            counters["warn"] += 1

    # CHANGELOG
    cl_path = os.path.join(state["repo"], "CHANGELOG.md")
    cl_text = ""
    if os.path.isfile(cl_path):
        with open(cl_path, "r", encoding="utf-8-sig") as fh:
            cl_text = fh.read()
    cl_fails, cl_warns = check_changelog_gates(cl_text)
    for m in cl_fails:
        fail("CHANGELOG：" + m)
        counters["fail"] += 1
    for m in cl_warns:
        warn("CHANGELOG：" + m)
        counters["warn"] += 1
    if not cl_fails and not cl_warns:
        ok("CHANGELOG 格式与链接齐备")
        counters["ok"] += 1

    # 令牌扫描：已跟踪文件
    rc, out, _ = git(repo, "grep", "-nI", "-E",
                     *sum((["-e", p.pattern] for _, p in TOKEN_PATTERNS), []),
                     "--", ".")
    if rc == 0:
        files = sorted({redact_line(l).split(":", 1)[0] for l in out.splitlines() if l.strip()})
        fail("令牌扫描命中 %d 处（值已隐藏）：涉及 %s" % (len(out.splitlines()), ", ".join(files)))
        counters["fail"] += 1
    elif rc == 1:
        ok("已跟踪文件令牌扫描 0 命中")
        counters["ok"] += 1
    else:
        warn("令牌扫描未执行（空仓库或 git grep 不可用）")
        counters["warn"] += 1

    # 令牌扫描：remote URL 内嵌凭据
    cred_findings = scan_remote_urls(state.get("remotes") or {})
    if cred_findings:
        for name, kind, url in cred_findings:
            fail("remote [%s] 的 %s 内嵌凭据：%s" % (name, kind, url))
        say("       修复：`craft_cli.py adopt %s --gitcode <url> --github <url>` 可迁移到 SSH/环境变量方案；" % repo)
        say("       已暴露的令牌请在平台控制台轮换。")
        counters["fail"] += 1
    else:
        ok("remote URL 无内嵌凭据")
        counters["ok"] += 1

    # remote 姿态
    platforms = state.get("push_platforms") or []
    if not state.get("origin"):
        fail("缺少 origin remote。修复：`craft_cli.py adopt %s --gitcode <url> --github <url>`。" % repo)
        counters["fail"] += 1
    elif len(platforms) >= 2:
        ok("双平台推送就绪（%s）" % "+".join(platforms))
        counters["ok"] += 1
    else:
        warn("单平台推送（%s）。如需双平台：`craft_cli.py adopt`。" % ("、".join(platforms) or "无"))
        counters["warn"] += 1

    # tag 现状（信息项）
    tags = state.get("tags") or []
    if tags:
        latest = tags[-1]
        kind = "附注" if tag_is_annotated(repo, latest) else "轻量"
        info("最新 tag：%s（%s）" % (latest, kind))
    else:
        info("尚无 tag（首次发版用 --version v0.1.0）")

    # 正文机器腔 lint（警告级）
    if notes is not None:
        lint = lint_copy(notes)
        if lint:
            warn("Release 正文命中机器腔词表 %d 处（警告级，不阻断；词表 references/vocabulary.md）：" % len(lint))
            for lineno, cat, snip in lint[:10]:
                say("       第 %d 行 [%s] %s…" % (lineno, cat, snip))
            counters["warn"] += 1
        else:
            ok("Release 正文未命中机器腔词表")
            counters["ok"] += 1

    # 用户门禁命令
    for cmd in gates or []:
        info("执行门禁命令：%s" % cmd)
        proc = subprocess.run(cmd, shell=True, capture_output=True, cwd=state["repo"])
        if proc.returncode == 0:
            ok("门禁通过：%s" % cmd)
            counters["ok"] += 1
        else:
            err_tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or ["（无输出）"]
            fail("门禁失败（退出码 %d）：%s — %s" % (proc.returncode, cmd, err_tail[0][:120]))
            counters["fail"] += 1

    say(_fmt_gate_counters(counters))
    return EXIT_FAIL if counters["fail"] else EXIT_OK


def cmd_check(args):
    notes = None
    if args.notes_file:
        if not os.path.isfile(args.notes_file):
            die("notes 文件不存在：%s" % args.notes_file)
        with open(args.notes_file, "r", encoding="utf-8-sig") as fh:
            notes = fh.read()
    return run_check(args.repo, notes=notes, gates=args.gate)


# ---------------------------------------------------------------- 子命令：release

def create_release(platform, slug, tag, name, body, token):
    owner, repo_name = slug
    if platform == "gitcode":
        url = "%s/repos/%s/%s/releases" % (GITCODE_API, owner, repo_name)
        headers = {"PRIVATE-TOKEN": token}
    else:
        url = "%s/repos/%s/%s/releases" % (GITHUB_API, owner, repo_name)
        headers = {"Authorization": "Bearer " + token}
    status, data, err = http_json(
        "POST", url, headers=headers,
        payload={"tag_name": tag, "name": name, "body": body},
    )
    return status, data, err


def verify_release(platform, slug, tag, token):
    owner, repo_name = slug
    if platform == "gitcode":
        url = "%s/repos/%s/%s/releases/tags/%s" % (GITCODE_API, owner, repo_name, tag)
        headers = {"PRIVATE-TOKEN": token}
    else:
        url = "%s/repos/%s/%s/releases/tags/%s" % (GITHUB_API, owner, repo_name, tag)
        headers = {"Authorization": "Bearer " + token}
    status, data, err = http_json("GET", url, headers=headers)
    return status == 200, err


def release_web_url(platform, slug, tag):
    owner, repo_name = slug
    return "https://%s/%s/%s/releases/tag/%s" % (
        "gitcode.com" if platform == "gitcode" else "github.com", owner, repo_name, tag)


def cmd_release(args):
    repo = args.repo
    state = repo_state(repo)
    if not state["is_git"]:
        die("目标目录不是 git 仓库：%s" % repo)

    # 版本号
    latest = (state.get("tags") or [None])[-1]
    if args.version:
        version = args.version if args.version.startswith("v") else "v" + args.version
    elif args.bump:
        version = bump_version(latest, args.bump)
    else:
        die("请用 --version v0.x.y 或 --bump patch|minor|major 指定版本。")

    # 正文
    notes = None
    if args.notes_file:
        if not os.path.isfile(args.notes_file):
            die("notes 文件不存在：%s" % args.notes_file)
        with open(args.notes_file, "r", encoding="utf-8-sig") as fh:
            notes = fh.read()

    # 门禁（strict：脏树即失败，除非只动了 CHANGELOG）
    say("contract: %s · release %s · 模式 %s" % (CONTRACT, version, "APPLY" if args.apply else "DRY-RUN"))
    say()
    rc = run_check(repo, notes=notes, gates=args.gate, strict_dirty=True)
    say()

    plan_errors, steps = build_release_plan(state, version, args.notes_file, notes is not None)
    errors = list(plan_errors)
    if rc != EXIT_OK:
        errors.append("门禁存在失败项，见上。")
    if notes is None:
        cl_path = os.path.join(state["repo"], "CHANGELOG.md")
        section = None
        if os.path.isfile(cl_path):
            with open(cl_path, "r", encoding="utf-8-sig") as fh:
                entry = changelog_entry(fh.read(), version)
                if entry:
                    section = "\n".join(entry["body"])
        say("—— Release 正文骨架（从 CHANGELOG 生成，缺口已标（待补：…））：")
        say()
        say(build_notes_skeleton(version, section))
        say()
        if args.apply:
            errors.append("缺少 --notes-file：把上面的骨架补完存成文件，再带 --notes-file --apply 重跑。")
    else:
        for m in validate_notes(notes):
            errors.append("正文校验：" + m)
        entry_note = None
        cl_path = os.path.join(state["repo"], "CHANGELOG.md")
        if os.path.isfile(cl_path):
            with open(cl_path, "r", encoding="utf-8-sig") as fh:
                entry_note = changelog_entry(fh.read(), version)
        if entry_note is None:
            errors.append(
                "CHANGELOG.md 缺少 [%s] 条目。先把 `## [%s] - 日期` 写入 CHANGELOG 再发版。"
                % (version.lstrip("v"), version.lstrip("v"))
            )

    if errors:
        for m in errors:
            fail(m)
        return EXIT_FAIL

    say("—— 发版计划：")
    for i, s in enumerate(steps, 1):
        say("  %d. %s" % (i, s))
    say()

    if not args.apply:
        ok("dry-run 通过。确认无误后加 --apply 执行（将打 tag、推送并创建双平台 Release）。")
        return EXIT_OK

    # ---- apply ----
    dirty = state.get("dirty_files") or []
    only_changelog = dirty_only_changelog(dirty)
    if only_changelog:
        git(repo, "add", "CHANGELOG.md")
        rc_, _, err = git(repo, "commit", "-m", "chore: release %s" % version)
        if rc_ != 0:
            die("发版提交失败：" + err.strip()[:200])
        ok("发版提交完成")

    first_para = notes.strip().splitlines()[0] if notes else version
    rc_, _, err = git(repo, "tag", "-a", version, "-m", first_para)
    if rc_ != 0:
        die("打 tag 失败：" + err.strip()[:200])
    ok("附注 tag 完成：%s" % version)

    branch = state.get("branch") or "HEAD"
    rc_, _, err = git(repo, "push", "origin", branch, "--tags")
    if rc_ != 0:
        warn("推送失败，3 秒后重试一次（弱网预案）：%s" % err.strip()[:120])
        time.sleep(3)
        rc_, _, err = git(repo, "push", "origin", branch, "--tags")
        if rc_ != 0:
            die("推送失败（已重试）：" + err.strip()[:200])
    ok("推送完成（origin 双 pushurl 同步）")

    origin = state.get("origin") or {}
    push_urls = list(origin.get("pushurls") or []) or ([origin["url"]] if origin.get("url") else [])
    name = notes_title(notes, version)
    released, broken = [], []
    for url in push_urls:
        platform = detect_platform(url)
        slug = parse_slug(url)
        if not platform or not slug:
            warn("跳过无法识别的推送目标：%s" % redact_url(url))
            continue
        token, src = resolve_token(platform, args.gitcode_token if platform == "gitcode" else args.github_token)
        if not token:
            fail(platform + " 平台令牌未配置，Release 未创建。")
            say(token_guide(platform))
            broken.append(platform)
            continue
        status, data, err = create_release(platform, slug, version, name, notes, token)
        if status in (200, 201):
            ok("%s Release 创建成功（%s，令牌来源：%s）" % (platform, release_web_url(platform, slug, version), src))
            exists, err = verify_release(platform, slug, version, token)
            if exists:
                ok("%s 回查通过：%s" % (platform, release_web_url(platform, slug, version)))
                released.append(platform)
            else:
                fail("%s 回查未通过：%s（GitCode 响应 id/html_url 为 null 属正常，以回查为准）" % (platform, err))
                broken.append(platform)
        else:
            fail("%s Release 创建失败（HTTP %s）：%s" % (platform, status, err))
            broken.append(platform)

    if state.get("type") == "skill":
        say()
        info("skill 型仓库发版后：本机重装并验证版本戳——")
        say("       cd <本仓库> && ./install.sh --agent=zcode（或 .\\install.ps1 -Agent zcode）")
        say("       python <技能目录>/scripts/craft_cli.py doctor  ← 首行应显示 %s" % version)

    if broken:
        fail("发版未全部完成：%s 未建成 Release（tag 与代码已推送）。修复令牌后可手工补建，或重跑本命令（tag 已存在会拦截，需先处理）。" % "、".join(broken))
        return EXIT_FAIL
    ok("发版完成：%s @ %s" % (version, "+".join(released)))
    return EXIT_OK


# ---------------------------------------------------------------- 子命令：adopt

def cmd_adopt(args):
    repo = args.repo
    state = repo_state(repo)
    if not state["is_git"]:
        die("目标目录不是 git 仓库：%s" % repo)
    if not args.gitcode or not args.github:
        die("需要 --gitcode <url> 与 --github <url>（主仓 + 镜像）。")

    gitcode = to_ssh_url(args.gitcode) or args.gitcode
    github = to_ssh_url(args.github) or args.github
    remotes = state.get("remotes") or {}
    ops = []

    # 1) origin 收敛：fetch 指向主仓，双 pushurl
    origin = remotes.get("origin")
    if origin is None:
        ops.append("git remote add origin " + gitcode)
    elif (origin.get("url") or "") != gitcode:
        ops.append("git remote set-url origin " + gitcode + "   # 原 " + redact_url(origin.get("url") or ""))
    explicit_push = list(origin.get("pushurls") or []) if origin else []
    if explicit_push:
        for u in (gitcode, github):
            if u not in set(explicit_push):
                ops.append("git remote set-url --add --push origin " + u)
    else:
        # 无显式 pushurl 时，第一条 --add 会整体替换默认 push 目标，必须成对添加
        ops.append("git remote set-url --add --push origin " + gitcode)
        ops.append("git remote set-url --add --push origin " + github)
    redundant = sorted(set(explicit_push) - {gitcode, github})
    for u in redundant:
        ops.append("# 提示：存在多余 pushurl %s（如不再需要请手动移除）" % redact_url(u))

    # 2) 内嵌凭据迁移：除 origin 外的所有 remote（origin 已在第 1 步整体重构，
    #    按旧快照再迁移一次会覆盖 fetch 指向——实测计划冲突）
    for name, entry in remotes.items():
        if name == "origin":
            continue
        for kind, urls in (("url", [entry["url"]] if entry["url"] else []),
                           ("pushurl", entry["pushurls"])):
            for url in urls:
                if URL_CRED_RX.search(url):
                    clean = to_ssh_url(url) or URL_CRED_RX.sub(
                        lambda m: re.sub(r"(://[^:/@\s]+:)[^@/\s]+(@)", r"\1\2", m.group(0)), url)
                    ops.append("git remote set-url %s %s   # 迁移内嵌凭据（原 %s）" % (name, clean, redact_url(url)))
                    say("[安全] remote [%s] %s 内嵌了明文凭据——迁移为 SSH/干净 URL。" % (name, kind))
                    say("       该令牌已暴露在 .git/config 中，请在平台控制台轮换。")

    # 3) .gitignore 补 .env
    gi_path = os.path.join(state["repo"], ".gitignore")
    gi_text = ""
    if os.path.isfile(gi_path):
        with open(gi_path, "r", encoding="utf-8-sig") as fh:
            gi_text = fh.read()
    if not re.search(r"(^|\n)\s*\.env", gi_text):
        ops.append("向 .gitignore 追加 .env / *.env / !.env.example")

    # 4) CHANGELOG 补齐（含 tag 历史 + compare 链接）
    cl_path = os.path.join(state["repo"], "CHANGELOG.md")
    if not os.path.isfile(cl_path):
        ops.append("生成 CHANGELOG.md（Keep a Changelog 中文骨架 + tag 历史 + compare 链接）")

    say("contract: %s · adopt · 模式 %s" % (CONTRACT, "APPLY" if args.apply else "DRY-RUN"))
    say()
    say("—— 将执行的操作：")
    for op in ops:
        say("  " + op)
    if not ops:
        ok("仓库已符合标准，无需改动。")
        return EXIT_OK
    if not args.apply:
        say()
        ok("dry-run 完成。确认后加 --apply 执行。")
        return EXIT_OK

    # apply
    for op in ops:
        if op.startswith("#"):
            say(op)
            continue
        parts = op.split("   #")[0].strip().split(" ")
        # ops 里的 git 命令统一形如 "git remote <subcmd> ..."；.gitignore/CHANGELOG 单独处理
        if parts[0] == "git" and parts[1] == "remote":
            rc_, _, err = git(repo, *(parts[1:]))
            if rc_ != 0:
                die("执行失败：%s — %s" % (op, err.strip()[:150]))
            info("已执行：%s" % op.split("   #")[0])
        else:
            info("待处理：%s" % op)
    if any(".gitignore 追加" in op for op in ops):
        block = "\n# craft_cli 追加：环境与密钥\n.env\n*.env\n!.env.example\n"
        with open(gi_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(block if gi_text.endswith("\n") or not gi_text else "\n" + block)
        info("已追加 .gitignore")
    if any("生成 CHANGELOG.md" in op for op in ops):
        tags = state.get("tags") or []
        dates = tag_dates(repo)
        slug = parse_slug(gitcode) or ("<owner>", "<repo>")
        base = "https://gitcode.com/%s/%s" % slug
        lines = ["# 变更日志", "",
                 "格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。", "",
                 "## [Unreleased]", ""]
        prev = None
        for t in tags:
            lines += ["## [%s] - %s" % (t.lstrip("vV"), dates.get(t, "待补")), "",
                      "（历史版本，说明待补：见 tag 对应提交。）", ""]
            prev = t
        lines += ["---", ""]
        if tags:
            lines.append("[%s]: %s/compare/%s...HEAD" % ("Unreleased", base, tags[-1]))
            for i, t in enumerate(tags):
                link = ("%s/compare/%s...%s" % (base, tags[i - 1], t)) if i else ("%s/releases/tag/%s" % (base, t))
                lines.append("[%s]: %s" % (t.lstrip("vV"), link))
        else:
            lines.append("[Unreleased]: %s/compare/HEAD" % base)
        with open(cl_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        info("已生成 CHANGELOG.md（%d 个历史 tag 已登记）" % len(tags))
    say()
    ok("adopt 完成。下一步：`python craft_cli.py check %s` 复查。" % repo)
    return EXIT_OK


# ---------------------------------------------------------------- 子命令：doctor

def cmd_doctor(args):
    version = read_runtime_conf().get("Version", "dev")
    say("skill-craft %s（contract %s）" % (version, CONTRACT))

    problems = 0
    py = sys.version_info
    if py >= (3, 7):
        ok("Python %d.%d.%d" % (py.major, py.minor, py.micro))
    else:
        fail("Python %d.%d 过旧，需 3.7+" % (py.major, py.minor))
        problems += 1

    if git_available():
        ok("git 可用")
    else:
        fail("git 不可用——发版功能依赖 git。")
        problems += 1

    root = skill_root()
    missing = [p for p in ("SKILL.md", "references", "scripts") if not os.path.exists(os.path.join(root, p))]
    if missing:
        fail("技能目录不完整，缺：%s。修复：重跑安装器。" % "、".join(missing))
        problems += 1
    else:
        ok("技能目录完整（SKILL.md + references/ + scripts/）")

    config_missing = False
    for platform in ("gitcode", "github"):
        token, src = resolve_token(platform)
        label = "%s 令牌" % platform
        if not token:
            warn(label + "未配置（发版到该平台前需要）。")
            say(token_guide(platform))
            config_missing = True
            continue
        if platform == "gitcode":
            url, headers = GITCODE_API + "/user", {"PRIVATE-TOKEN": token}
        else:
            url, headers = GITHUB_API + "/user", {"Authorization": "Bearer " + token}
        t0 = time.time()
        status, data, err = http_json("GET", url, headers=headers, timeout=10, retries=1)
        latency = int((time.time() - t0) * 1000)
        if status == 200:
            login = (data or {}).get("login", "?") if isinstance(data, dict) else "?"
            ok("%s 有效（账号 %s，实测 %dms，来源：%s）" % (label, login, latency, src))
        elif status in (401, 403):
            fail("%s 无效（HTTP %d）。处理：到平台核对或重新生成，更新 %s。" % (label, status, "~/.skill-craft/.env"))
            problems += 1
        else:
            warn("%s 无法验证（HTTP %s / %s）——网络问题，令牌本身未必有错。" % (label, status, err))
    if problems:
        return EXIT_FAIL
    if config_missing:
        return EXIT_USAGE
    ok("自检全部通过。")
    return EXIT_OK


# ---------------------------------------------------------------- main

def main(argv=None):
    _safe_stdio()
    ap = argparse.ArgumentParser(
        prog="craft_cli",
        description="skill-craft 标准化发布 CLI：init / check / release / adopt / doctor。默认 dry-run，--apply 才真执行。",
    )
    ap.add_argument("--version", action="version", version="craft_cli " + read_runtime_conf().get("Version", "dev"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="生成标准仓库脚手架（中文默认）")
    p.add_argument("dir", help="目标目录（须不存在或为空）")
    p.add_argument("--name", required=True, help="项目/技能名（如 my-skill）")
    p.add_argument("--type", choices=["skill", "app"], default="skill", help="仓库形态，默认 skill")
    p.add_argument("--gitcode", help="GitCode 主仓 URL（提供则自动 git init + 挂 remote）")
    p.add_argument("--github", help="GitHub 镜像 URL")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("check", help="发版前体检（只读）")
    p.add_argument("repo", nargs="?", default=".", help="仓库路径，默认当前目录")
    p.add_argument("--notes-file", help="待检查的 Release 正文文件（做机器腔 lint）")
    p.add_argument("--gate", action="append", help="自定义门禁命令，可多次（如 --gate \"npm test\"）")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("release", help="发版流水线（默认 dry-run，--apply 执行）")
    p.add_argument("repo", nargs="?", default=".", help="仓库路径")
    p.add_argument("--version", help="目标版本，如 v0.2.0")
    p.add_argument("--bump", choices=["patch", "minor", "major"], help="基于最新 tag 递增")
    p.add_argument("--notes-file", help="Release 正文文件（双平台同一份；apply 必需）")
    p.add_argument("--gate", action="append", help="发版前必须通过的门禁命令，可多次")
    p.add_argument("--apply", action="store_true", help="真执行（打 tag/推送/建 Release）")
    p.add_argument("--gitcode-token", help="显式指定 GitCode 令牌（也可走环境变量/.env，见 doctor）")
    p.add_argument("--github-token", help="显式指定 GitHub 令牌")
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("adopt", help="把既有仓库纳入标准（remote/凭据/CHANGELOG）")
    p.add_argument("repo", nargs="?", default=".", help="仓库路径")
    p.add_argument("--gitcode", required=True, help="GitCode 主仓 URL")
    p.add_argument("--github", required=True, help="GitHub 镜像 URL")
    p.add_argument("--apply", action="store_true", help="真执行（默认 dry-run）")
    p.set_defaults(func=cmd_adopt)

    p = sub.add_parser("doctor", help="技能自检：版本 / 令牌 / 网络")
    p.set_defaults(func=cmd_doctor)

    args = ap.parse_args(argv)
    try:
        return args.func(args) or EXIT_OK
    except SystemExit:
        raise
    except KeyboardInterrupt:
        die("已中断。", EXIT_FAIL)


if __name__ == "__main__":
    sys.exit(main())
