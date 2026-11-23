"""Symbol-only lines, honorific signs and routing continuity (1.2.0)."""

import itertools
import queue
import re
import unittest
from pathlib import Path

import synthDrivers.autoTTS as driver
from synthDrivers.autoTTS import languageDetection as ld
from synthDrivers.autoTTS.configManager import LanguageVoiceConfig, sharedConfig

ROOT = Path(__file__).resolve().parents[1]


def texts(sequence):
	return [item for item in sequence if isinstance(item, str)]


class DriverSymbolTests(unittest.TestCase):
	def setUp(self):
		self.saved = (sharedConfig.languages, sharedConfig.defaultLang, sharedConfig.enabled,
			sharedConfig.useUnicodeLanguageDetection, sharedConfig.save)
		sharedConfig.save = lambda *args, **kwargs: None
		sharedConfig.defaultLang = "en"
		sharedConfig.enabled = True
		sharedConfig.useUnicodeLanguageDetection = True
		sharedConfig.languages = {
			"en": LanguageVoiceConfig("en", synth="fake", voice="english"),
			"ur": LanguageVoiceConfig("ur", synth="fake", voice="urdu"),
		}
		d = driver.SynthDriver.__new__(driver.SynthDriver)
		d._voice = "en"
		d._isSpeaking = False
		d._synth = None
		d._synthCache = {}
		d._usedSynths = []
		d.speechQueue = queue.Queue()
		d._markerCounter = itertools.count(1_500_000_000)
		d._activeMarker = None
		d._activeChunkId = 0
		d._activeForwardIndices = set()
		d._nvdaWords = frozenset({"link", "button"})
		d.pumpSpeech = lambda: None
		self.d = d

	def tearDown(self):
		(sharedConfig.languages, sharedConfig.defaultLang, sharedConfig.enabled,
			sharedConfig.useUnicodeLanguageDetection, sharedConfig.save) = self.saved

	def chunks(self, sequence):
		self.d.speak(sequence)
		out = []
		while not self.d.speechQueue.empty():
			lang, seq = self.d.speechQueue.get_nowait()[:2]
			out.append((lang, "".join(texts(seq)).strip()))
		return out

	def test_lone_honorific_sign_on_a_line_is_read_in_urdu(self):
		self.assertEqual(self.chunks(["ؑ"]), [("ur", "علیہ السلام")])

	def test_honorific_ligature_on_a_line_is_read_in_urdu(self):
		self.assertEqual(self.chunks(["ﷺ"]), [("ur", "صلی اللہ علیہ وسلم")])

	def test_honorific_sign_after_a_latin_word_is_still_read(self):
		self.assertEqual(self.chunks(["Musa ؑ"]), [("en", "Musa"), ("ur", "علیہ السلام")])

	def test_honorific_inside_urdu_text_is_expanded(self):
		self.assertEqual(self.chunks(["حضرت موسیٰ ؑ نے کہا"]), [("ur", "حضرت موسیٰ علیہ السلام نے کہا")])

	def test_line_of_only_urdu_punctuation_is_read_by_name(self):
		self.assertEqual(self.chunks(["؟"]), [("ur", "سوالیہ نشان")])
		self.assertEqual(self.chunks(["۔"]), [("ur", "ختمہ")])

	def test_punctuation_inside_a_sentence_is_never_read_by_name_or_switched(self):
		self.assertEqual(self.chunks(["Hello ۔"]), [("en", "Hello ۔")])
		self.assertEqual(self.chunks(["کیا حال ہے؟"]), [("ur", "کیا حال ہے؟")])

	def test_urdu_after_urdu_keeps_the_urdu_voice(self):
		# The previous utterance ended in Urdu and NVDA did not cancel in between.
		self.d._activePreparedLang = "ur"
		self.assertEqual([lang for lang, _text in self.chunks(["یہ اردو ہے"])], ["ur"])


class ProsodyRingTests(unittest.TestCase):
	def test_custom_prosody_change_from_the_settings_ring_applies_immediately(self):
		saved = (sharedConfig.languages, sharedConfig.defaultLang, sharedConfig.save)
		sharedConfig.save = lambda *args, **kwargs: None
		sharedConfig.defaultLang = "ur"
		sharedConfig.languages = {"ur": LanguageVoiceConfig("ur", useCustomProsody=True, customRate=40)}
		try:
			d = driver.SynthDriver.__new__(driver.SynthDriver)
			d._voice = "ur"
			d._activePreparedLang = "ur"
			d._set_rate(65)
			self.assertEqual(sharedConfig.languages["ur"].customRate, 65)
			self.assertIsNone(d._activePreparedLang)
		finally:
			sharedConfig.languages, sharedConfig.defaultLang, sharedConfig.save = saved


class DetectorTests(unittest.TestCase):
	def test_nvda_words_are_not_statistically_scored(self):
		calls = []

		def detector(text, candidates):
			calls.append(text)
			return "fr"

		common = dict(
			defaultLang="en",
			useStatisticalDetection=True,
			statisticalLanguages={"en": "en", "fr": "fr"},
			statisticalDetector=detector,
		)
		list(ld.addDetectedLanguageCommands(["button"], protectedTexts=frozenset({"button"}), **common))
		self.assertEqual(calls, [])
		list(ld.addDetectedLanguageCommands(["bonjour tout le monde"], protectedTexts=frozenset({"button"}), **common))
		self.assertEqual(len(calls), 1)

	def test_nvda_locale_form(self):
		self.assertEqual(ld.to_nvda_locale("ur-pk"), "ur_PK")
		self.assertEqual(ld.to_nvda_locale("pa-PK"), "pa_PK")
		self.assertEqual(ld.to_nvda_locale("ur"), "ur")
		self.assertEqual(ld.to_nvda_locale("zh-hant-tw"), "zh_hant_TW")

	def test_arabic_script_languages_include_shahmukhi(self):
		for code in ("ur", "ur-pk", "pnb", "pa-pk", "ar", "fa"):
			self.assertTrue(ld.is_arabic_script_lang(code), code)
		for code in ("pa", "pa-in", "hi", "en"):
			self.assertFalse(ld.is_arabic_script_lang(code), code)


class SymbolDictionaryTests(unittest.TestCase):
	"""The NVDA symbol dictionaries and the driver's own table must not drift apart."""

	@staticmethod
	def readDictionary(path):
		entries = {}
		inSymbols = False
		for line in path.read_text(encoding="utf-8").splitlines():
			if line.strip() == "symbols:":
				inSymbols = True
				continue
			if not inSymbols or not line or line.startswith("#"):
				continue
			fields = line.split("\t")
			entries[fields[0]] = (fields[1], fields[2] if len(fields) > 2 else "")
		return entries

	def test_manifest_declares_the_dictionary_and_every_file_exists(self):
		manifest = (ROOT / "manifest.ini").read_text(encoding="utf-8")
		self.assertRegex(manifest, r"\[symbolDictionaries\]\s*\n\s*\[\[autoTTS\]\]")
		for locale in ("ur", "pnb", "pa_PK", "pa"):
			self.assertTrue((ROOT / "locale" / locale / "symbols-autoTTS.dic").is_file(), locale)
		self.assertEqual(list(ROOT.glob("locale/*/symbols.dic")), [])

	def test_urdu_dictionary_matches_the_driver_table(self):
		for locale, lang in (("ur", "ur"), ("pnb", "pnb"), ("pa_PK", "pa-pk")):
			entries = self.readDictionary(ROOT / "locale" / locale / "symbols-autoTTS.dic")
			for symbol, (replacement, level) in entries.items():
				self.assertEqual(ld.get_spoken_symbol(symbol, lang), replacement, (locale, symbol))
				if symbol in ld.HONORIFIC_CHARS:
					# Honorific signs are words: NVDA must read them at every symbol level.
					self.assertEqual(level, "none", (locale, symbol))

	def test_dictionary_lines_are_well_formed(self):
		for path in ROOT.glob("locale/*/symbols-autoTTS.dic"):
			for symbol, (replacement, level) in self.readDictionary(path).items():
				self.assertTrue(replacement.strip(), (path, symbol))
				self.assertIn(level, ("none", "some", "most", "all", "char"), (path, symbol))
				self.assertNotRegex(replacement, r"^\s|\s$")


if __name__ == "__main__":
	unittest.main()
