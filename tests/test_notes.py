# -*- coding: utf-8 -*-
"""CHANGELOG 解析、Release 正文骨架与校验（纯函数）。"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402

SAMPLE = """# 变更日志

格式基于 Keep a Changelog。

## [Unreleased]

## [0.2.0] - 2026-11-01

### Added

- craft_cli.py 五个子命令

### 升级方式

- git pull 后重跑安装器

## [0.1.0] - 2026-10-31

- 首个发布

[Unreleased]: https://gitcode.com/u/r/compare/v0.2.0...HEAD
[0.2.0]: https://gitcode.com/u/r/compare/v0.1.0...v0.2.0
[0.1.0]: https://gitcode.com/u/r/releases/tag/v0.1.0
"""


class TestChangelogParsing(unittest.TestCase):
    def test_entries_and_links(self):
        entries, links = craft_cli.parse_changelog(SAMPLE)
        self.assertEqual([e["version"] for e in entries], ["Unreleased", "0.2.0", "0.1.0"])
        self.assertEqual(entries[1]["date"], "2026-11-01")
        self.assertIn("0.2.0", links)

    def test_entry_extraction(self):
        entry = craft_cli.changelog_entry(SAMPLE, "v0.2.0")
        self.assertIsNotNone(entry)
        self.assertIn("craft_cli.py", "\n".join(entry["body"]))
        self.assertIsNone(craft_cli.changelog_entry(SAMPLE, "v9.9.9"))

    def test_gates_on_sample(self):
        text = SAMPLE
        fails, warns = craft_cli.check_changelog_gates(text)
        self.assertEqual((fails, warns), ([], []))

    def test_gate_missing_unreleased(self):
        fails, _ = craft_cli.check_changelog_gates("## [0.1.0] - 2026-01-01\n\n- 首版\n")
        self.assertTrue(any("Unreleased" in m for m in fails))

    def test_gate_missing_links_warns(self):
        text = "## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n\n- 首版\n"
        _, warns = craft_cli.check_changelog_gates(text)
        self.assertTrue(any("compare" in m for m in warns))

    def test_gate_missing_file_fails(self):
        fails, _ = craft_cli.check_changelog_gates("")
        self.assertEqual(len(fails), 1)


class TestNotesSkeletonAndValidation(unittest.TestCase):
    def test_skeleton_marks_gaps(self):
        skel = craft_cli.build_notes_skeleton("v0.2.0", "- 新增 X")
        self.assertIn("待补", skel)
        self.assertIn("### 改动内容", skel)
        self.assertIn("### 升级方式", skel)
        self.assertIn("- 新增 X", skel)

    def test_validate_blocks_placeholder(self):
        fails = craft_cli.validate_notes(craft_cli.build_notes_skeleton("v0.2.0"))
        self.assertTrue(any("待补" in m for m in fails))

    def test_validate_blocks_missing_upgrade(self):
        fails = craft_cli.validate_notes("## v0.2.0\n改动若干，已实测。")
        self.assertTrue(any("升级" in m for m in fails))

    def test_validate_accepts_complete_notes(self):
        notes = "## v0.2.0 · 标题\n改动：X。\n升级方式：git pull。\n契约：v1 不变。"
        self.assertEqual(craft_cli.validate_notes(notes), [])

    def test_notes_title(self):
        self.assertEqual(craft_cli.notes_title("## v0.2.0 · 标题\n正文", "fb"), "v0.2.0 · 标题")
        self.assertEqual(craft_cli.notes_title("无标题正文", "fb"), "fb")


if __name__ == "__main__":
    unittest.main()
