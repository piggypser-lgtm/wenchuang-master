import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_package


SOURCE = Path(__file__).resolve().parents[2]


class PackageAssetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "assets").mkdir()
        self.readme = self.root / "README.md"
        self.readme.write_text("# Example", encoding="utf-8")
        config = "assets/project-config.example.json"
        self.qr = self.root / check_package.CONTACT_QR
        for resource in (config, check_package.CONTACT_QR):
            shutil.copyfile(SOURCE / resource, self.root / resource)
        allowed = ("README.md", config, check_package.CONTACT_QR)
        entries = patch.object(check_package, "RELEASE_FILES", allowed)
        entries.start()
        self.addCleanup(entries.stop)

    def test_only_the_declared_image_bypasses_text_decoding(self):
        self.assertEqual(check_package.check(self.root), ([], []))
        self.readme.write_bytes(self.qr.read_bytes())
        errors, _ = check_package.check(self.root)
        self.assertTrue(any("UTF-8" in error and "README.md" in error for error in errors))

    def test_invalid_or_truncated_qr_is_rejected(self):
        jpeg = self.qr.read_bytes()
        for invalid in (b"", b"plain text", jpeg[:jpeg.find(b"\xff\xd9")], jpeg[3:]):
            with self.subTest(size=len(invalid)):
                self.qr.write_bytes(invalid)
                errors, _ = check_package.check(self.root)
                self.assertTrue(any("JPEG" in error for error in errors))

    def test_html_images_must_resolve_to_packaged_files(self):
        self.readme.write_text('<IMG alt="Contact" src="assets/wechat-qr.jpg">', encoding="utf-8")
        self.assertEqual(check_package.check(self.root), ([], []))
        (self.root / "extra.jpg").write_bytes(self.qr.read_bytes())
        for ref, expected in (("missing.jpg", "不存在"), ("../outside.jpg", "超出"), ("extra.jpg", "未列入")):
            with self.subTest(ref=ref):
                self.readme.write_text(f"<img alt='X' src='{ref}'>", encoding="utf-8")
                errors, _ = check_package.check(self.root)
                self.assertTrue(any(expected in error for error in errors))
