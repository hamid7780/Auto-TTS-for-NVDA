import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

import build as packaging


class PackagingTests(unittest.TestCase):
    def test_installable_archive_contains_help_runtimes_licenses_and_no_caches(self):
        with tempfile.TemporaryDirectory(dir="tests") as directory:
            version = packaging.manifest_value("version")
            addon = packaging.build(directory, expected_version=version)
            with zipfile.ZipFile(str(addon)) as archive:
                names = archive.namelist()
                for required in packaging.REQUIRED:
                    self.assertIn(required, names)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(any(name.startswith(("tests/", ".git/", ".tools/")) for name in names))
                self.assertIsNone(archive.testzip())
                manifest = archive.read("manifest.ini").decode("utf-8")
                self.assertIn('version = "{}"'.format(version), manifest)
                self.assertIn("updateChannel = stable", manifest)
            checksum = addon.with_suffix(addon.suffix + ".sha256").read_text(encoding="ascii")
            self.assertEqual(checksum.split()[0], hashlib.sha256(addon.read_bytes()).hexdigest())

    def test_mismatched_release_tag_cannot_create_a_package(self):
        with tempfile.TemporaryDirectory(dir="tests") as directory:
            with self.assertRaisesRegex(ValueError, "Release tag"):
                packaging.build(directory, expected_version="9.9.9")
            self.assertFalse(list(Path(directory).iterdir()))

    def test_repeated_builds_have_identical_checksums(self):
        with tempfile.TemporaryDirectory(dir="tests") as directory:
            addon = packaging.build(directory)
            first = hashlib.sha256(addon.read_bytes()).hexdigest()
            packaging.build(directory)
            self.assertEqual(first, hashlib.sha256(addon.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
