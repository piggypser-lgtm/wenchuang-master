import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import read_feasibility as reader
import read_stage


class FeasibilityReadTests(unittest.TestCase):
    def test_command_returns_exact_section_through_a_legacy_code_page(self):
        command = [sys.executable, "-B", str(Path(reader.__file__))]
        data = subprocess.check_output(command)
        document = reader.SOURCE.read_text(encoding="utf-8-sig")
        section = reader.HEADING + document.split(reader.HEADING, 1)[1].split("\n## ", 1)[0]
        self.assertTrue(data.isascii())
        self.assertEqual(json.loads(data.decode("cp936")), section.strip())

    def test_entrypoint_is_readable_even_with_mismatched_windows_code_pages(self):
        data = (read_stage.SOURCE.parent / "SKILL.md").read_bytes()
        self.assertTrue(data.isascii())
        self.assertEqual(data.decode("cp936"), data.decode("utf-8"))

    def test_slicing_handoff_exposes_inspect_before_desktop_fallback(self):
        entry = (read_stage.SOURCE.parent / "SKILL.md").read_text(encoding="utf-8")
        stage = read_stage.read_section(read_stage.SOURCE, read_stage.STAGES["6"])
        self.assertIn("scripts/bambu_project.py inspect --input", entry)
        self.assertIn("references/bambu-adapter.md#", stage)
        self.assertIn("inspect --input", stage)
        self.assertIn("references/slicing-automation.md#", stage)
        self.assertLess(stage.index("inspect --input"), stage.index("references/slicing-automation.md#"))

    def test_all_stage_commands_return_only_the_current_section(self):
        document = read_stage.SOURCE.read_text(encoding="utf-8-sig")
        env = dict(os.environ, PYTHONIOENCODING="cp936")
        with tempfile.TemporaryDirectory(prefix="stage read ") as work:
            for stage, heading in read_stage.STAGES.items():
                with self.subTest(stage=stage):
                    data = subprocess.check_output(
                        [sys.executable, "-B", str(Path(read_stage.__file__)), stage],
                        cwd=work, env=env,
                    )
                    self.assertTrue(data.isascii())
                    start = document.index("\n" + heading + "\n") + 1
                    tail = document[start + len(heading):]
                    depth = len(heading.split(" ", 1)[0])
                    body = re.split(rf"(?m)^#{{1,{depth}}} ", tail, maxsplit=1)[0]
                    self.assertEqual(json.loads(data.decode("cp936")), (heading + body).strip())

    def test_missing_or_empty_section_fails(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "guide.md"
            for text in ("# unrelated", reader.HEADING + "\n\n## Next\nOther text"):
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        reader.read_criteria(path)
