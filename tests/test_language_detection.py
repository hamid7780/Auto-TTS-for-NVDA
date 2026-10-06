import unittest

from synthDrivers.autoTTS.languageDetection import (
	LangChangeCommand,
	addDetectedLanguageCommands,
	classify_arabic_segment,
)


class LanguageDetectionTests(unittest.TestCase):
	def test_urdu_evidence_keeps_whole_clause_urdu_despite_arabic_model_guess(self):
		text = "یہ ایک مکمل اردو جملہ ہے اور اسے درست ترتیب سے پڑھنا چاہیے۔"
		result = list(addDetectedLanguageCommands(
			[text],
			defaultLang="en",
			scriptSettings={"Arabic": "ur", "Latin": "en"},
			statisticalLanguages={"ur": "ur", "ar": "ar"},
			statisticalDetector=lambda text, candidates: "ar",
		))
		self.assertEqual(self.languages(result), ["ur"])
		self.assertEqual("".join(item for item in result if isinstance(item, str)), text)

	def test_arabic_evidence_keeps_whole_clause_arabic(self):
		text = "هذه جملة عربية كاملة وهي واضحة."
		result = list(addDetectedLanguageCommands(
			[text],
			defaultLang="ur",
			scriptSettings={"Arabic": "ur"},
			statisticalLanguages={"ur": "ur", "ar": "ar"},
			statisticalDetector=lambda text, candidates: "ur",
		))
		self.assertEqual(self.languages(result), ["ar"])
		self.assertEqual("".join(item for item in result if isinstance(item, str)), text)

	def test_ambiguous_arabic_script_phrase_stays_in_selected_urdu(self):
		text = "السلام علیکم"
		result = list(addDetectedLanguageCommands(
			[text],
			defaultLang="ur",
			scriptSettings={"Arabic": "ur"},
			statisticalLanguages={"ur": "ur", "ar": "ar"},
			statisticalDetector=lambda text, candidates: "ar",
		))
		self.assertEqual(self.languages(result), [])
		self.assertEqual("".join(item for item in result if isinstance(item, str)), text)

	def languages(self, sequence):
		return [item.lang for item in sequence if isinstance(item, LangChangeCommand)]

	def test_mixed_urdu_english_keeps_logical_order(self):
		sequence = list(addDetectedLanguageCommands(["پہلے English بعد"], defaultLang="ur"))
		self.assertEqual("".join(item for item in sequence if isinstance(item, str)), "پہلے English بعد")
		self.assertEqual(self.languages(sequence), ["en", "ur"])

	def test_long_urdu_verse_message_is_one_complete_ordered_chunk(self):
		text = (
			"آج کی آیت — دنیاوی زندگی کی حقیقت\n\n"
			"\"جان لو کہ دنیا کی زندگی صرف کھیل، تماشا، ظاہری زینت، آپس میں فخر کرنا اور مال و اولاد میں "
			"ایک دوسرے سے بڑھنے کی کوشش ہے۔ اس کی مثال اس بارش کی سی ہے جس سے پیدا ہونے والی کھیتی کسانوں "
			"کو اچھی لگتی ہے، پھر وہ خشک ہوجاتی ہے، پھر تم اسے زرد دیکھتے ہو، پھر وہ چورا چورا ہوجاتی ہے۔ "
			"اور آخرت میں سخت عذاب بھی ہے اور اللہ کی طرف سے مغفرت اور رضا بھی۔ اور دنیا کی زندگی دھوکے کے "
			"سامان کے سوا کچھ نہیں۔\"\n\n📖 سورۃ الحدید: 20"
		)
		sequence = list(addDetectedLanguageCommands(
			[text],
			defaultLang="en",
			scriptSettings={"Arabic": "ur", "Latin": "en"},
			granularityMode="word",
			statisticalLanguages={"en": "en", "ur": "ur", "ar": "ar"},
		))
		self.assertEqual(self.languages(sequence), ["ur"])
		self.assertEqual("".join(item for item in sequence if isinstance(item, str)), text)

	def test_arabic_current_language_beats_urdu_default(self):
		self.assertEqual(
			classify_arabic_segment("السلام عليكم", default_lang="ur", current_lang="ar"),
			"ar",
		)

	def test_granularity_modes_are_not_aliases(self):
		text = "یہ test ہے۔"
		word = list(addDetectedLanguageCommands([text], defaultLang="ur", granularityMode="word"))
		sentence = list(addDetectedLanguageCommands([text], defaultLang="ur", granularityMode="sentence"))
		self.assertNotEqual(self.languages(word), self.languages(sentence))

	def test_math_symbols_use_configured_math_language(self):
		sequence = list(addDetectedLanguageCommands(["قیمت α + β ہے"], defaultLang="ur", mathLanguage="en"))
		self.assertIn("en", self.languages(sequence))

	def test_document_tags_can_be_trusted(self):
		sequence = list(addDetectedLanguageCommands(
			[LangChangeCommand("ur"), "English"],
			defaultLang="en",
			tagMode="preferTags",
		))
		self.assertEqual(self.languages(sequence), ["ur"])

	def test_same_script_detector_can_select_enabled_profile(self):
		calls = []
		def detector(text, candidates):
			calls.append((text, candidates))
			return "fr"

		sequence = list(addDetectedLanguageCommands(
			["Bonjour tout le monde."],
			defaultLang="en",
			statisticalLanguages={"en": "en", "fr": "fr"},
			statisticalDetector=detector,
		))
		self.assertEqual(self.languages(sequence), ["fr"])
		self.assertEqual("".join(item for item in sequence if isinstance(item, str)), "Bonjour tout le monde.")
		self.assertEqual(calls[0][1], {"en": "en", "fr": "fr"})

	def test_same_script_model_is_not_run_when_it_cannot_improve_routing(self):
		def detector(text, candidates):
			self.fail("statistical detector should not run for an already definitive script")

		sequence = list(addDetectedLanguageCommands(
			["This stays English."],
			defaultLang="en",
			statisticalLanguages={"en": "en", "ur": "ur"},
			statisticalDetector=detector,
		))
		self.assertEqual(self.languages(sequence), [])

	def test_same_script_clauses_keep_original_order(self):
		def detector(text, candidates):
			return "fr" if "Bonjour" in text else "en"

		original = "Bonjour tout le monde. Hello everyone!"
		sequence = list(addDetectedLanguageCommands(
			[original],
			defaultLang="en",
			statisticalLanguages={"en": "en", "fr": "fr"},
			statisticalDetector=detector,
		))
		self.assertEqual(self.languages(sequence), ["fr", "en"])
		self.assertEqual("".join(item for item in sequence if isinstance(item, str)), original)


if __name__ == "__main__":
	unittest.main()
