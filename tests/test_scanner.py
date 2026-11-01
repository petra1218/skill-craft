# -*- coding: utf-8 -*-
"""令牌扫描器：内容扫描、remote URL 内嵌凭据、脱敏、URL/版本解析。

注意：本文件里的假令牌全部用字符串拼接构造（"ghp_" + "A"*30），
避免仓库自己的 `craft_cli.py check` 扫到自己的测试 fixtures。
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402


class TestContentScan(unittest.TestCase):
    def test_github_pat_detected(self):
        token = "ghp_" + "A" * 30
        hits = craft_cli.scan_text_for_tokens("配置：" + token)
        self.assertEqual(len(hits), 1)
        self.assertIn("ghp_", hits[0][1])

    def test_deepseek_key_detected(self):
        token = "sk-" + "0123456789abcdef"
        self.assertEqual(craft_cli.scan_text_for_tokens(token), [(1, craft_cli.TOKEN_PATTERNS[0][0])])

    def test_short_placeholder_not_flagged(self):
        # 文档示例 x-access-token:TOKEN@（短占位）不误报——自己的扫描器
        # 曾扫到自己的文档示例（见 craft_cli 注释）。
        text = "错误形态示例：https://x-access-token:TOKEN@github.com/a/b.git 请勿这样写"
        self.assertEqual(craft_cli.scan_text_for_tokens(text), [])

    def test_clean_text_passes(self):
        text = "安装：pip install requests\n更新：git pull 后重跑安装器"
        self.assertEqual(craft_cli.scan_text_for_tokens(text), [])

    def test_redact_never_exposes_value(self):
        token = "ghp_" + "B" * 30
        line = "export KEY=" + token
        redacted = craft_cli.redact_line(line)
        self.assertNotIn(token, redacted)
        self.assertIn("<已隐藏>", redacted)


class TestRemoteUrlScan(unittest.TestCase):
    def test_embedded_credential_detected_and_redacted(self):
        secret = "C" * 40
        remotes = {
            "origin": {"url": "https://x-access-token:ghp_" + secret + "@github.com/u/r.git",
                       "pushurls": []},
        }
        findings = craft_cli.scan_remote_urls(remotes)
        self.assertEqual(len(findings), 1)
        name, kind, url = findings[0]
        self.assertEqual(name, "origin")
        self.assertNotIn(secret, url)

    def test_ssh_urls_clean(self):
        remotes = {"origin": {"url": "git@gitcode.com:u/r.git", "pushurls": ["git@github.com:u/r.git"]}}
        self.assertEqual(craft_cli.scan_remote_urls(remotes), [])

    def test_pushurl_scanned_too(self):
        remotes = {"origin": {"url": "git@gitcode.com:u/r.git",
                              "pushurls": ["https://oauth2:" + "D" * 32 + "@gitcode.com/u/r.git"]}}
        self.assertEqual(len(craft_cli.scan_remote_urls(remotes)), 1)


class TestUrlParsing(unittest.TestCase):
    def test_parse_slug_ssh_and_https(self):
        self.assertEqual(craft_cli.parse_slug("git@gitcode.com:petra1218/ds-search.git"),
                         ("petra1218", "ds-search"))
        self.assertEqual(craft_cli.parse_slug("https://github.com/petra1218/reduce-ai"),
                         ("petra1218", "reduce-ai"))

    def test_detect_platform(self):
        self.assertEqual(craft_cli.detect_platform("git@gitcode.com:a/b.git"), "gitcode")
        self.assertEqual(craft_cli.detect_platform("https://github.com/a/b.git"), "github")
        self.assertIsNone(craft_cli.detect_platform("https://gitee.com/a/b"))

    def test_to_ssh_url(self):
        self.assertEqual(craft_cli.to_ssh_url("https://github.com/u/r.git"),
                         "git@github.com:u/r.git")


class TestVersionHelpers(unittest.TestCase):
    def test_is_newer(self):
        self.assertTrue(craft_cli.is_newer("v0.2.0", "v0.1.3"))
        self.assertFalse(craft_cli.is_newer("v0.1.3", "v0.2.0"))
        self.assertFalse(craft_cli.is_newer("v0.2.0", "v0.2.0"))

    def test_prerelease_orders_below_release(self):
        self.assertTrue(craft_cli.is_newer("v0.3.0", "v0.3.0-pre.2"))
        self.assertTrue(craft_cli.is_newer("v0.3.0-pre.2", "v0.2.9"))

    def test_bump(self):
        self.assertEqual(craft_cli.bump_version("v0.2.3", "patch"), "v0.2.4")
        self.assertEqual(craft_cli.bump_version("v0.2.3", "minor"), "v0.3.0")
        self.assertEqual(craft_cli.bump_version("v0.2.3", "major"), "v1.0.0")
        self.assertEqual(craft_cli.bump_version(None, "patch"), "v0.1.0")


if __name__ == "__main__":
    unittest.main()
