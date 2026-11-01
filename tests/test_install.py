# -*- coding: utf-8 -*-
"""安装器与产物的不变量守护（BOM 纪律等，见 references/pitfalls.md）。"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "skills", "skill-craft", "scripts"))
import craft_cli  # noqa: E402

SKILL_DIR = os.path.join(REPO, "skills", "skill-craft")


class TestInstallerInvariants(unittest.TestCase):
    def test_ps1_has_bom(self):
        """含中文的 .ps1 必须带 BOM：PS 5.1 无 BOM 按 GBK 解析直接语法报错。"""
        with open(os.path.join(REPO, "install.ps1"), "rb") as fh:
            self.assertEqual(fh.read(3), b"\xef\xbb\xbf")

    def test_sh_has_no_bom(self):
        """.sh 绝不带 BOM：BOM 会破坏 shebang。"""
        with open(os.path.join(REPO, "install.sh"), "rb") as fh:
            head = fh.read(3)
        self.assertNotEqual(head, b"\xef\xbb\xbf")
        self.assertEqual(head, b"#!/")

    def test_init_templates_honor_bom_invariants(self):
        """init 生成的安装器模板同样遵守 BOM 纪律。"""
        ctx = {"name": "demo-skill"}
        self.assertTrue(craft_cli.render_install_ps1(ctx).startswith("\ufeff"))
        self.assertFalse(craft_cli.render_install_sh(ctx).startswith("\ufeff"))


class TestSkillPackageIntegrity(unittest.TestCase):
    def test_skill_dir_structure(self):
        for rel in ("SKILL.md", "references", "scripts", "runtime.conf"):
            self.assertTrue(
                os.path.exists(os.path.join(SKILL_DIR, rel)), "缺 " + rel
            )
        for rel in ("release.md", "credentials.md", "pitfalls.md",
                    "release-copy.md", "vocabulary.md"):
            self.assertTrue(
                os.path.exists(os.path.join(SKILL_DIR, "references", rel)),
                "缺 references/" + rel,
            )

    def test_runtime_conf_template(self):
        conf = craft_cli.read_runtime_conf(SKILL_DIR)
        self.assertEqual(conf.get("Runtime"), "Python")
        self.assertEqual(conf.get("Version"), "dev")
        self.assertIn("craft_cli.py", conf.get("Command", ""))

    def test_cli_syntax_compiles(self):
        import py_compile
        py_compile.compile(
            os.path.join(SKILL_DIR, "scripts", "craft_cli.py"), doraise=True)


if __name__ == "__main__":
    unittest.main()
