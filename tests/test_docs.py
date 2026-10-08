import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relativePath):
	return (ROOT / relativePath).read_text(encoding="utf-8").replace("\r\n", "\n")


def manifestValue(key):
	match = re.search(r"^" + re.escape(key) + r"\s*=\s*\"?([^\"\n]+)\"?\s*$", read("manifest.ini"), re.M)
	assert match, key
	return match.group(1).strip()


def loadHelpBuilder():
	spec = importlib.util.spec_from_file_location("make_help", ROOT / "tools" / "make_help.py")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class DocumentationTests(unittest.TestCase):
	def test_help_page_is_generated_from_readme(self):
		self.assertEqual(
			read("doc/en/readme.html"),
			loadHelpBuilder().build(),
			"Run: python tools/make_help.py",
		)

	def test_version_is_the_same_everywhere(self):
		version = manifestValue("version")
		self.assertRegex(read("CHANGELOG.md"), r"^# Changelog\n\n## " + re.escape(version) + r"\n")
		self.assertIn("Auto TTS %s - Third-party notices" % version, read("THIRD_PARTY_NOTICES.txt"))
		self.assertIn("What's new in %s" % version, read("RELEASE_NOTES.md"))
		self.assertIn("autoTTS-%s.nvda-addon" % version, read("RELEASE_NOTES.md"))
		self.assertIn("Auto TTS %s'" % version, read(".github/ISSUE_TEMPLATE/bug_report.yml"))
		self.assertIn("Version %s." % version, read("doc/en/readme.html"))
		self.assertIn("| Version | `%s` |" % version, read("docs/PUBLISHING.md"))

	def test_nvda_versions_match_the_manifest(self):
		readme = read("README.md")
		self.assertIn("Needs NVDA %s or newer" % manifestValue("minimumNVDAVersion"), readme)
		self.assertIn("Last tested with NVDA %s." % manifestValue("lastTestedNVDAVersion"), readme)
		notes = read("RELEASE_NOTES.md")
		self.assertIn("**%s**" % manifestValue("minimumNVDAVersion"), notes)
		self.assertIn("**%s**" % manifestValue("lastTestedNVDAVersion"), notes)
		publishing = read("docs/PUBLISHING.md")
		self.assertIn("| Minimum NVDA | `%s` |" % manifestValue("minimumNVDAVersion"), publishing)
		self.assertIn("| Last tested NVDA | `%s` |" % manifestValue("lastTestedNVDAVersion"), publishing)

	def test_every_shortcut_in_the_code_is_documented(self):
		source = read("globalPlugins/autoTTS/__init__.py")
		gestures = re.findall(r'gesture="kb:([^"]+)"', source)
		self.assertGreaterEqual(len(gestures), 4)
		readme = read("README.md")
		for gesture in gestures:
			names = {"nvda": "NVDA", "control": "Ctrl"}
			parts = [names.get(part.lower(), part.capitalize()) for part in gesture.split("+")]
			self.assertIn("| " + "+".join(parts) + " |", readme, gesture)

	def test_default_excluded_apps_are_named_in_the_guide(self):
		from synthDrivers.autoTTS.configManager import DEFAULT_EXCLUDED_APPS
		self.assertEqual(len(DEFAULT_EXCLUDED_APPS), 6)
		readme = read("README.md")
		for name in ("Visual Studio Code", "Command Prompt", "PowerShell", "Windows Terminal", "Visual Studio", "Notepad++"):
			self.assertIn(name, readme)

	def test_project_links_use_the_manifest_address(self):
		address = manifestValue("url")
		self.assertEqual(address, "https://github.com/hamid7780/Auto-TTS-for-NVDA")
		for path in ("README.md", "docs/PUBLISHING.md", "docs/DEVELOPMENT.md", "RELEASE_NOTES.md", "doc/en/readme.html"):
			text = read(path)
			self.assertNotIn("hamid7780/autoTTS", text, path)
		self.assertIn(address + "/releases/latest", read("README.md"))

	def test_documents_avoid_em_dashes(self):
		for path in ("README.md", "CHANGELOG.md", "RELEASE_NOTES.md", "docs/DEVELOPMENT.md", "docs/PUBLISHING.md", "doc/en/readme.html"):
			self.assertNotIn("\u2014", read(path), path)


if __name__ == "__main__":
	unittest.main()
