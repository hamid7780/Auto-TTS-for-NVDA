"""Labeled corpus for Arabic-script and mixed-language detection.

Every sentence lists the language each piece must be read in. The statistical models are
off here, so these results come from letter evidence alone and stay the same on every
machine. Sentences that only a model can settle (Sindhi or Pashto written without any of
their own letters) are deliberately not listed.
"""

import unittest

from synthDrivers.autoTTS import languageDetection as ld
from synthDrivers.autoTTS import persoArabicLid

ALL_PROFILES = {"ur": "ur", "ar": "ar", "fa": "fa", "ps": "ps", "sd": "sd", "en": "en"}
URDU_ARABIC = {"ur": "ur", "ar": "ar", "en": "en"}

# (expected language of every Arabic-script word, sentence)
WHOLE_SENTENCES = [
	("ur", "یہ میری کتاب ہے"),
	("ur", "میں اسکول جا رہا ہوں"),
	("ur", "میں نے کہا کہ الحمد للہ سب ٹھیک ہے"),
	("ur", "السلام علیکم آپ کیسے ہیں"),
	("ur", "يہ كتاب بهت اچهي ہے"),  # Urdu typed on an Arabic keyboard
	("ur", "حضرت عمر رضی اللہ عنہ نے فرمایا"),
	("ar", "بسم الله الرحمن الرحيم"),
	("ar", "ذهبت إلى السوق أمس واشتريت الخبز"),
	("ar", "أنا أحب القراءة كثيرا"),
	("ar", "قال الله تعالى إن الله مع الصابرين"),
	("ar", "هذا كتاب جميل"),
	("ar", "السلام عليكم ورحمة الله"),
	("fa", "این یک کتاب خوب است"),
	("fa", "من به مدرسه می‌روم و درس می‌خوانم"),
	("ps", "زه کور ته ځم"),
	("sd", "آئون ڪتاب پڙهان ٿو"),
]

# (expected (language, text) pieces in word mode, sentence)
MIXED_SENTENCES = [
	(
		[("ur", "انہوں نے کہا"), ("ar", "بسم الله الرحمن الرحيم"), ("ur", "اور پھر کھانا کھایا")],
		"انہوں نے کہا بسم الله الرحمن الرحيم اور پھر کھانا کھایا",
	),
	(
		[("ur", "ہم نے"), ("en", "Facebook"), ("ur", "پر"), ("en", "post"), ("ur", "کیا")],
		"ہم نے Facebook پر post کیا",
	),
]


def pieces(text, mode, profiles, defaultLang="en"):
	out = []
	lang = defaultLang
	for item in ld.addDetectedLanguageCommands(
		[text], defaultLang=defaultLang, granularityMode=mode,
		useStatisticalDetection=False, statisticalLanguages=profiles,
	):
		if isinstance(item, ld.LangChangeCommand):
			lang = item.lang
		elif isinstance(item, str) and item.strip():
			if out and out[-1][0] == lang:
				out[-1] = (lang, out[-1][1] + item)
			else:
				out.append((lang, item))
	return [(lang, text.strip()) for lang, text in out]


class CorpusTests(unittest.TestCase):
	def test_whole_sentences_with_every_profile(self):
		for mode in ("word", "sentence", "line"):
			for expected, text in WHOLE_SENTENCES:
				with self.subTest(mode=mode, text=text):
					self.assertEqual({lang for lang, _ in pieces(text, mode, ALL_PROFILES)}, {expected})

	def test_languages_without_a_profile_fall_back_to_urdu(self):
		for expected, text in WHOLE_SENTENCES:
			want = expected if expected in URDU_ARABIC else "ur"
			with self.subTest(text=text):
				self.assertEqual({lang for lang, _ in pieces(text, "word", URDU_ARABIC)}, {want})

	def test_mixed_sentences_in_word_mode(self):
		for expected, text in MIXED_SENTENCES:
			with self.subTest(text=text):
				self.assertEqual(pieces(text, "word", ALL_PROFILES), expected)

	def test_sentence_mode_counts_words_not_characters(self):
		self.assertEqual({lang for lang, _ in pieces("ہم نے Facebook پر post کیا", "sentence", URDU_ARABIC)}, {"ur"})

	def test_shahmukhi_default_keeps_its_own_profile(self):
		profiles = {"pa": "pa-pk", "ar": "ar", "en": "en"}
		self.assertEqual({lang for lang, _ in pieces("ایہہ میری کتاب اے", "word", profiles, "pa-pk")}, {"pa-pk"})


class EvidenceTests(unittest.TestCase):
	def test_shared_letters_are_not_urdu_evidence(self):
		# ی and ک are Persian too; only letters Urdu alone uses decide Urdu.
		self.assertEqual(persoArabicLid.word_evidence("کتاب"), ("xa", persoArabicLid.WEAK))
		self.assertEqual(persoArabicLid.word_evidence("ہے")[0], "ur")

	def test_models_are_asked_only_without_decisive_letters(self):
		asked = []

		def model(text):
			asked.append(text)
			return "fa"

		self.assertEqual(persoArabicLid.resolve_clause("یہ میری کتاب ہے", ("ur", "fa"), model), "ur")
		self.assertEqual(asked, [])
		self.assertEqual(persoArabicLid.resolve_clause("دا زما کتاب دی", ("ur", "fa"), model), "fa")
		self.assertEqual(len(asked), 1)

	def test_sindhi_yeh_is_not_arabic_when_sindhi_is_configured(self):
		self.assertNotEqual(persoArabicLid.resolve_clause("هي منهنجو گهر آهي", ("ur", "ar", "sd")), "ar")


if __name__ == "__main__":
	unittest.main()
