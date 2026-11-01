# -*- coding: utf-8 -*-
"""发版计划构造（纯函数，不碰 git/网络）。"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402


def make_state(**kw):
    state = {
        "repo": "/fake/repo", "is_git": True, "dirty_files": [], "branch": "main",
        "tags": ["v0.1.0", "v0.1.3"], "remotes": {}, "origin": {"url": "git@gitcode.com:u/r.git", "pushurls": []},
        "push_platforms": ["gitcode", "github"], "type": "skill",
    }
    state.update(kw)
    return state


class TestReleasePlanErrors(unittest.TestCase):
    def test_non_git(self):
        errors, _ = craft_cli.build_release_plan(make_state(is_git=False), "v0.2.0", None, False)
        self.assertTrue(any("不是 git 仓库" in e for e in errors))

    def test_dirty_non_changelog_blocks(self):
        st = make_state(dirty_files=[" M src/a.py", "?? notes.md"])
        errors, _ = craft_cli.build_release_plan(st, "v0.2.0", None, False)
        self.assertTrue(any("非 CHANGELOG" in e for e in errors))

    def test_dirty_only_changelog_yields_commit_step(self):
        st = make_state(dirty_files=[" M CHANGELOG.md"])
        errors, steps = craft_cli.build_release_plan(st, "v0.2.0", None, False)
        self.assertEqual(errors, [])
        self.assertTrue(any("chore: release v0.2.0" in s for s in steps))

    def test_existing_tag_blocks(self):
        errors, _ = craft_cli.build_release_plan(make_state(), "v0.1.3", None, False)
        self.assertTrue(any("已存在" in e for e in errors))

    def test_not_newer_blocks(self):
        errors, _ = craft_cli.build_release_plan(make_state(), "v0.1.2", None, False)
        self.assertTrue(any("不高于" in e for e in errors))

    def test_no_platform_blocks_with_guide(self):
        st = make_state(push_platforms=[], origin=None)
        errors, _ = craft_cli.build_release_plan(st, "v0.2.0", None, False)
        self.assertTrue(any("adopt" in e for e in errors))

    def test_unborn_branch_blocks(self):
        errors, _ = craft_cli.build_release_plan(make_state(branch=None), "v0.2.0", None, False)
        self.assertTrue(any("分支" in e for e in errors))


class TestReleasePlanSteps(unittest.TestCase):
    def test_happy_path_skill(self):
        errors, steps = craft_cli.build_release_plan(make_state(), "v0.2.0", "notes.md", True)
        self.assertEqual(errors, [])
        self.assertTrue(any("附注 tag" in s for s in steps))
        self.assertTrue(any("push origin main --tags" in s for s in steps))
        self.assertEqual(sum(1 for s in steps if "创建" in s and "Release" in s), 2)
        self.assertEqual(sum(1 for s in steps if "回查" in s), 2)
        self.assertTrue(any("版本戳" in s for s in steps))

    def test_app_type_no_reinstall_step(self):
        errors, steps = craft_cli.build_release_plan(make_state(type="app"), "v0.2.0", None, True)
        self.assertEqual(errors, [])
        self.assertFalse(any("版本戳" in s for s in steps))

    def test_single_platform_releases_once(self):
        st = make_state(push_platforms=["gitcode"])
        _, steps = craft_cli.build_release_plan(st, "v0.2.0", None, True)
        self.assertEqual(sum(1 for s in steps if "回查" in s), 1)


if __name__ == "__main__":
    unittest.main()
