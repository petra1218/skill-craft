# -*- coding: utf-8 -*-
"""init 脚手架：文件齐全、编码纪律、模板文案过自己的 lint、remote 挂载。"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402

GIT_OK = subprocess.run(["git", "--version"], capture_output=True).returncode == 0


def run_init(tmp, name, type_, gitcode=None, github=None):
    args = argparse.Namespace(dir=tmp, name=name, type=type_,
                              gitcode=gitcode, github=github)
    rc = craft_cli.cmd_init(args)
    return rc


class TestInitSkill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="craft_init_")
        self.proj = os.path.join(self.tmp, "demo-skill")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(GIT_OK, "git 不可用")
    def test_skill_scaffold(self):
        rc = run_init(self.proj, "demo-skill", "skill",
                      gitcode="https://gitcode.com/u/demo-skill",
                      github="https://github.com/u/demo-skill")
        self.assertEqual(rc, 0)
        for rel in ("README.md", "CHANGELOG.md", "LICENSE", ".gitignore",
                    "install.sh", "install.ps1",
                    os.path.join("skills", "demo-skill", "SKILL.md"),
                    os.path.join("skills", "demo-skill", "runtime.conf")):
            self.assertTrue(os.path.isfile(os.path.join(self.proj, rel)), "缺 " + rel)
        # BOM 纪律
        with open(os.path.join(self.proj, "install.ps1"), "rb") as fh:
            self.assertEqual(fh.read(3), b"\xef\xbb\xbf")
        with open(os.path.join(self.proj, "install.sh"), "rb") as fh:
            self.assertNotEqual(fh.read(3), b"\xef\xbb\xbf")
        # 模板文案过自己的机器腔 lint
        with open(os.path.join(self.proj, "README.md"), encoding="utf-8") as fh:
            self.assertEqual(craft_cli.lint_copy(fh.read()), [])
        # CHANGELOG 有 Unreleased
        with open(os.path.join(self.proj, "CHANGELOG.md"), encoding="utf-8") as fh:
            fails, warns = craft_cli.check_changelog_gates(fh.read())
        self.assertEqual((fails, warns), ([], []))
        # remote：fetch 走主仓，双 pushurl 成对挂载
        _, out, _ = craft_cli.git(self.proj, "config", "--get-all", "remote.origin.pushurl")
        pushurls = [u.strip() for u in out.splitlines() if u.strip()]
        self.assertEqual(len(pushurls), 2)
        self.assertTrue(any("gitcode.com" in u for u in pushurls))
        self.assertTrue(any("github.com" in u for u in pushurls))

    def test_app_scaffold(self):
        rc = run_init(os.path.join(self.tmp, "demo-app"), "demo-app", "app")
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(
            os.path.join(self.tmp, "demo-app", "skills")))
        with open(os.path.join(self.tmp, "demo-app", "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("Releases", readme)

    def test_refuses_nonempty_dir(self):
        os.makedirs(self.proj, exist_ok=True)
        with open(os.path.join(self.proj, "x.txt"), "w") as fh:
            fh.write("x")
        with self.assertRaises(SystemExit):
            run_init(self.proj, "demo-skill", "skill")


if __name__ == "__main__":
    unittest.main()
