"""Build the NVDA add-on with the Python standard library (Python 3.7+)."""

import argparse
import ast
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
PACKAGE_DIRS = ("synthDrivers", "globalPlugins", "doc", "locale")
PACKAGE_FILES = ("manifest.ini", "README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.txt")
REQUIRED = (
    "manifest.ini", "COPYING.txt", "doc/en/readme.html",
    "synthDrivers/autoTTS/__init__.py", "globalPlugins/autoTTS/__init__.py",
    "synthDrivers/autoTTS/models/lid.176.ftz",
    "synthDrivers/autoTTS/fasttext_runtime/LICENSE.txt",
    "synthDrivers/autoTTS/fasttext_runtime/fasttext_pybind.cp37-win32.pyd",
    "synthDrivers/autoTTS/fasttext_runtime/fasttext_pybind.cp311-win32.pyd",
    "synthDrivers/autoTTS/fasttext_runtime/fasttext_pybind.cp313-win_amd64.pyd",
)


def manifest_value(key):
    text = (ROOT / "manifest.ini").read_text(encoding="utf-8")
    match = re.search(r"^" + re.escape(key) + r"\s*=\s*(.*?)\s*$", text, re.MULTILINE)
    if match is None:
        raise ValueError("Missing manifest field: " + key)
    return match.group(1).strip('"')


def build(output_dir, expected_version=None):
    name, version = manifest_value("name"), manifest_value("version")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Invalid add-on name")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must use major.minor.patch")
    if expected_version is not None and version != expected_version:
        raise ValueError("Release tag does not match manifest version")
    if manifest_value("updateChannel") != "stable":
        raise ValueError("This release workflow expects the stable channel")
    entries = {filename: ROOT / filename for filename in PACKAGE_FILES}
    entries["COPYING.txt"] = ROOT / "LICENSE.txt"
    for directory in PACKAGE_DIRS:
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix not in (".py", ".pyd", ".ftz", ".txt", ".html", ".css", ".mo", ".ini"):
                continue
            entries[path.relative_to(ROOT).as_posix()] = path
    for required in REQUIRED:
        if required not in entries or not entries[required].is_file():
            raise ValueError("Missing required package file: " + required)
    for path in entries.values():
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    addon_path = output_dir / (name + "-" + version + ".nvda-addon")
    # Fixed metadata and sorted entries make builds reproducible on the same
    # Python/zlib version, without including local settings or bytecode caches.
    with zipfile.ZipFile(str(addon_path), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, path in sorted(entries.items()):
            info = zipfile.ZipInfo(filename, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(str(addon_path)) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError("Corrupt archive member: " + bad_file)
    checksum = hashlib.sha256(addon_path.read_bytes()).hexdigest()
    checksum_path = addon_path.with_suffix(addon_path.suffix + ".sha256")
    checksum_path.write_text(checksum + "  " + addon_path.name + "\n", encoding="ascii")
    print("Built {} ({} files)".format(addon_path, len(entries)))
    print("SHA256: " + checksum)
    return addon_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT))
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    build(args.output_dir, args.expected_version)
