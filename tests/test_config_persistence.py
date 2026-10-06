import json
import os
import tempfile
import unittest
from unittest import mock

from synthDrivers.autoTTS import configManager
from synthDrivers.autoTTS.configManager import AutoTTSConfig, LanguageVoiceConfig


class ConfigPersistenceTests(unittest.TestCase):
	def _newPath(self):
		fd, path = tempfile.mkstemp(prefix="autoTTS-test-", suffix=".json", dir="tests")
		os.close(fd)
		return path

	def _cleanup(self, settingsPath):
		for path in (settingsPath, settingsPath + ".bak", settingsPath + ".tmp"):
			if os.path.exists(path):
				os.remove(path)

	def test_save_keeps_previous_complete_file_as_backup(self):
		settingsPath = self._newPath()
		try:
			oldData = {
				"defaultLang": "ur",
				"languages": {
					"ur": {"synth": "espeak", "voice": "ur", "enabled": True},
				},
			}
			with open(settingsPath, "w", encoding="utf-8") as f:
				json.dump(oldData, f)

			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				cfg.languages["en"] = LanguageVoiceConfig("en", synth="oneCore", voice="English")
				cfg.save()

			with open(settingsPath + ".bak", "r", encoding="utf-8") as f:
				backup = json.load(f)
			self.assertIn("ur", backup["languages"])
			with open(settingsPath, "r", encoding="utf-8") as f:
				current = json.load(f)
			self.assertIn("ur", current["languages"])
			self.assertIn("en", current["languages"])
		finally:
			self._cleanup(settingsPath)

	def test_unexpected_empty_primary_recovers_populated_backup(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as f:
				json.dump({"languages": {}, "defaultLang": ""}, f)
			with open(settingsPath + ".bak", "w", encoding="utf-8") as f:
				json.dump({"languages": {"ur-pk": {"synth": "espeak"}}, "defaultLang": "ur-pk"}, f)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
			self.assertIn("ur-pk", cfg.languages)
			self.assertEqual(cfg.defaultLang, "ur-pk")
		finally:
			self._cleanup(settingsPath)

	def test_language_lock_is_session_only_and_never_restored_from_backup(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as f:
				json.dump({"languages": {}, "lockedLanguage": None}, f)
			with open(settingsPath + ".bak", "w", encoding="utf-8") as f:
				json.dump({
					"languages": {"ur-pk": {"synth": "googleTtsForNvda"}},
					"lockedLanguage": "ur-pk",
				}, f)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				self.assertIsNone(cfg.lockedLanguage)
				cfg.lockedLanguage = "ur-pk"
				cfg.save()
			with open(settingsPath, "r", encoding="utf-8") as f:
				self.assertIsNone(json.load(f)["lockedLanguage"])
		finally:
			self._cleanup(settingsPath)

	def test_corrupt_primary_recovers_backup_and_save_preserves_it(self):
		settingsPath = self._newPath()
		try:
			for invalid in ('{"languages":', '{"languages": {"en": {"customRate": "bad"}}}'):
				with self.subTest(primary=invalid):
					with open(settingsPath, "w", encoding="utf-8") as stream:
						stream.write(invalid)
					backup = {"languages": {"ur": {"synth": "espeak"}}, "defaultLang": "ur"}
					with open(settingsPath + ".bak", "w", encoding="utf-8") as stream:
						json.dump(backup, stream)
					with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
						cfg = AutoTTSConfig()
						self.assertIn("ur", cfg.languages)
						cfg.languages["en"] = LanguageVoiceConfig("en", synth="oneCore")
						cfg.save()
					with open(settingsPath + ".bak", encoding="utf-8") as stream:
						self.assertEqual(json.load(stream), backup)
					with open(settingsPath, encoding="utf-8") as stream:
						self.assertIn("en", json.load(stream)["languages"])
		finally:
			self._cleanup(settingsPath)

	def test_malformed_import_does_not_partially_replace_live_settings(self):
		cfg = AutoTTSConfig()
		cfg.defaultLang = "ur"
		cfg.languages = {"ur": LanguageVoiceConfig("ur", synth="espeak")}
		original = cfg._toFullDict()
		with self.assertRaises(ValueError):
			cfg._fromFullDict({"defaultLang": "fr", "languages": {
				"fr": {"synth": "espeak"}, "en": {"customRate": "invalid"},
			}})
		self.assertEqual(cfg._toFullDict(), original)

	def test_settings_can_still_be_saved_after_explicit_reset_and_reload(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as stream:
				json.dump({"languages": {"en": {"synth": "espeak"}}}, stream)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				cfg.languages.clear()
				cfg.save(allowEmptyProfiles=True)
				cfg = AutoTTSConfig()
				self.assertFalse(cfg.languages)
				cfg.enabled = False
				cfg.save()
				cfg = AutoTTSConfig()
				self.assertFalse(cfg.enabled)
				self.assertFalse(cfg.languages)
		finally:
			self._cleanup(settingsPath)

	def test_removing_last_profile_persists_an_intentional_empty_list(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as stream:
				json.dump({"languages": {"en": {"synth": "espeak"}}}, stream)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				cfg.removeLanguageConfig("en")
				self.assertFalse(AutoTTSConfig().languages)
		finally:
			self._cleanup(settingsPath)

	def test_unexpected_empty_save_cannot_replace_populated_profiles(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as f:
				json.dump({"languages": {"en": {"synth": "espeak"}}, "defaultLang": "en"}, f)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				cfg.languages.clear()
				cfg.save()
			with open(settingsPath, "r", encoding="utf-8") as f:
				self.assertIn("en", json.load(f)["languages"])
		finally:
			self._cleanup(settingsPath)

	def test_explicit_reset_can_save_an_intentionally_empty_profile_list(self):
		settingsPath = self._newPath()
		try:
			with open(settingsPath, "w", encoding="utf-8") as f:
				json.dump({"languages": {"en": {"synth": "espeak"}}, "defaultLang": "en"}, f)
			with mock.patch.object(configManager, "_getSettingsFilePath", return_value=settingsPath):
				cfg = AutoTTSConfig()
				cfg.languages.clear()
				cfg.save(allowEmptyProfiles=True)
			with open(settingsPath, "r", encoding="utf-8") as f:
				data = json.load(f)
			self.assertEqual(data["languages"], {})
			self.assertTrue(data["emptyProfilesIntentional"])
		finally:
			self._cleanup(settingsPath)


if __name__ == "__main__":
	unittest.main()
