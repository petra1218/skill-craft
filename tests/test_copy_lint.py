# -*- coding: utf-8 -*-
"""机器腔 lint（警告级）：命中提示、不误伤干净文本。词表见 references/vocabulary.md。"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402


class TestLintHits(unittest.TestCase):
    def test_marketing_words(self):
        hits = craft_cli.lint_copy("这是一个强大的工具，能让安装变得轻松。")
        cats = {h[1] for h in hits}
        self.assertIn("营销形容词", cats)

    def test_four_char_run(self):
        hits = craft_cli.lint_copy("该方案稳定可靠、快速响应、易于维护、扩展性强。")
        cats = {h[1] for h in hits}
        self.assertIn("四字连排", cats)

    def test_emoji_heading(self):
        hits = craft_cli.lint_copy("# 🚀 快速开始")
        self.assertEqual(hits[0][1], "标题带 emoji")

    def test_moralizing_close(self):
        hits = craft_cli.lint_copy("综上所述，本次更新奠定了坚实基础。")
        cats = {h[1] for h in hits}
        self.assertIn("点题说教", cats)

    def test_empty_opening(self):
        hits = craft_cli.lint_copy("随着大模型的快速发展，工具层出不穷。众所周知配置很麻烦。")
        cats = {h[1] for h in hits}
        self.assertIn("空泛开场", cats)

    def test_progressive_parallel(self):
        hits = craft_cli.lint_copy("本版本不仅修复了问题，而且提升了性能。")
        cats = {h[1] for h in hits}
        self.assertIn("排比触发器", cats)


class TestLintClean(unittest.TestCase):
    def test_factual_notes_pass(self):
        notes = "\n".join([
            "## v0.2.0 · 发版流水线脚本化",
            "",
            "### 改动内容",
            "- 新增 scripts/craft_cli.py：init/check/release/adopt/doctor 五个子命令",
            "- release 正文从单一 notes 文件双平台同发",
            "",
            "### 实测",
            "- 单测 24 项全绿（unittest，离线 fixtures）",
            "- 用 6 个真实仓库跑 check，问题清单与人工核查一一对应",
            "",
            "### 升级方式",
            "git pull 后重跑安装器；npx 渠道用 npx skills update skill-craft",
            "",
            "### 契约",
            "contract: v1 不变",
        ])
        self.assertEqual(craft_cli.lint_copy(notes), [])

    def test_generated_readme_template_passes(self):
        ctx = {"name": "demo-skill", "type": "skill", "base_url": None, "author": "a"}
        self.assertEqual(craft_cli.lint_copy(craft_cli.render_readme(ctx)), [])


if __name__ == "__main__":
    unittest.main()
