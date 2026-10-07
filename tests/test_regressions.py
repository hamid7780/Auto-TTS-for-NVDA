from pathlib import Path
import time
import unittest

from synthDrivers.autoTTS import statisticalDetection
from synthDrivers.autoTTS.languageDetection import (
	LangChangeCommand,
	addDetectedLanguageCommands,
	get_char_type,
)
from synthDrivers.autoTTS.scripts import get_script


class RegressionTests(unittest.TestCase):
	def test_long_arabic_script_line_is_processed_quickly(self):
		# Line and sentence modes once classified the whole unit for every
		# Arabic character, which took about 12 seconds for 10,000 characters.
		text = "یہ ایک لمبی لائن ہے جس میں بہت سے الفاظ ہیں۔ " * 250
		for mode in ("line", "sentence"):
			started = time.perf_counter()
			result = list(addDetectedLanguageCommands(
				[text],
				defaultLang="ur",
				granularityMode=mode,
				useStatisticalDetection=False,
			))
			self.assertLess(time.perf_counter() - started, 1.5, mode)
			self.assertEqual("".join(item for item in result if isinstance(item, str)), text)
			languages = [item.lang for item in result if isinstance(item, LangChangeCommand)]
			self.assertTrue(all(language == "ur" for language in languages))

	def test_unit_decision_for_arabic_matches_mixed_unit(self):
		result = list(addDetectedLanguageCommands(
			["Hello وَالسَّلَامُ عَلَيْكُمْ"],
			defaultLang="en",
			scriptSettings={"Latin": "en", "Arabic": "ur"},
			granularityMode="line",
			useStatisticalDetection=False,
		))
		languages = [item.lang for item in result if isinstance(item, LangChangeCommand)]
		self.assertEqual(languages, ["ar"])

	def test_script_table_lookup(self):
		self.assertEqual(get_script(ord("a")), "Latin")
		self.assertEqual(get_script(0x0627), "Arabic")
		self.assertEqual(get_script(0x4E2D), "Han")
		self.assertEqual(get_script(0x0905), "Devanagari")
		self.assertEqual(get_script(ord(" ")), "Common")
		self.assertEqual(get_script(0x10FFFF), "Common")
		self.assertEqual(get_char_type("a"), "Latin")

	def test_slash_inside_words_is_not_a_protected_path(self):
		pattern = statisticalDetection._PROTECTED_RE
		self.assertIsNone(pattern.search("Please send it and/or call me tomorrow morning."))
		self.assertIsNone(pattern.search("The limit is 60 km/h on this road."))
		self.assertIsNotNone(pattern.search("Open /usr/local/bin/python now"))
		self.assertIsNotNone(pattern.search("Open C:\\Windows\\System32 now"))
		self.assertIsNotNone(pattern.search("Visit https://example.com today"))

	def test_sample_texts_use_the_right_language(self):
		source = (Path(__file__).resolve().parents[1] / "globalPlugins" / "autoTTS" / "settingsPanel.py").read_text(encoding="utf-8")
		japanese = [line for line in source.splitlines() if line.strip().startswith('"ja":')][0]
		self.assertNotIn("\u8fd9", japanese)  # simplified Chinese character
		self.assertIn("\u3053\u308c\u306f", japanese)
		self.assertNotIn("Questo \u00e9", source)


if __name__ == "__main__":
	unittest.main()
