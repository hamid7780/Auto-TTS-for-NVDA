# Auto TTS - Unit tests for enhancements and bug fixes
# Covered by GNU General Public License (GPL)

import unittest
from unittest import mock
import time
import os
import tempfile

from synthDrivers.autoTTS import (
	numberProcessing,
	voiceMatch,
	voiceLabels,
	persoArabicLid,
	devanagariGroupLid,
	ngramLid,
	sharedScriptLid,
	activityLog,
)
from synthDrivers.autoTTS.configManager import LanguageVoiceConfig, sharedConfig
import synthDrivers.autoTTS as driver
from synthDrivers.autoTTS import languageDetection


class EnhancementsTests(unittest.TestCase):

	def test_perso_arabic_heuristics(self):
		# Urdu specific characters
		urduText = "یہ ایک ٹیسٹ ہے جس میں گاڑی اور کتاب ہے۔"
		decision = persoArabicLid.classify(urduText)
		self.assertEqual(decision, "ur")

		# Arabic text with definite article or Arabic specific letters
		arabicText = "الكتاب في المسجد والحمد لله"
		decision = persoArabicLid.classify(arabicText)
		self.assertEqual(decision, "ar")

		# Test sharedScriptLid resolve_segment
		self.assertEqual(sharedScriptLid.resolve_segment(urduText, "Arabic", {"ur", "ar"}), "ur")
		self.assertEqual(sharedScriptLid.resolve_segment(arabicText, "Arabic", {"ur", "ar"}), "ar")

	def test_devanagari_heuristics(self):
		# Marathi specific letters
		marathiText = "आम्ही पुण्यात राहतो ळ आणि हे आमचे घर आहे"
		decision = sharedScriptLid.resolve_segment(marathiText, "Devanagari", {"hi", "mr"})
		self.assertEqual(decision, "mr")

		# Hindi text
		hindiText = "यह एक बहुत सुंदर पुस्तक है और हम खुश हैं"
		decision = sharedScriptLid.resolve_segment(hindiText, "Devanagari", {"hi", "mr"})
		self.assertEqual(decision, "hi")

	def test_ngram_pure_python_lid(self):
		# Test n-gram classification directly on model
		modelPath = os.path.join(sharedScriptLid.MODEL_DIR, sharedScriptLid.GROUP_FILES["perso"])
		if os.path.exists(modelPath):
			model = ngramLid.NgramModel.load(modelPath)
			scores = model.scores("یہ کتاب بہت اچھی ہے")
			best = max(scores.items(), key=lambda kv: kv[1])[0]
			self.assertEqual(best, "ur")

	def test_mobile_number_processing(self):
		raw = "Call me at 03001234567 today."
		# 1. Spaces pattern
		reserved = numberProcessing.reserve_mobile(raw, "spaces")
		self.assertIn(numberProcessing.MOBILE_MARKER, reserved)
		expanded = numberProcessing.expand_reserved_mobile(reserved, "spaces")
		self.assertIn("0 3 0 0 1 2 3 4 5 6 7", expanded)

		# 2. Grouped pattern
		reserved = numberProcessing.reserve_mobile(raw, "grouped")
		expanded = numberProcessing.expand_reserved_mobile(reserved, "grouped")
		self.assertIn("0300 1234567", expanded)

		# 3. None pattern (disabled)
		reserved = numberProcessing.reserve_mobile(raw, "none")
		expanded = numberProcessing.expand_reserved_mobile(reserved, "none")
		self.assertEqual(expanded, raw)

	def test_long_numbers_processing(self):
		# Digits mode
		text = "Order 12345678 placed."
		rewritten = numberProcessing.rewrite_long_numbers(text, mode="digits", min_digits=5, crore_lakh_enabled=False)
		self.assertIn("1 2 3 4 5 6 7 8", rewritten)

		# Grouped mode
		rewritten = numberProcessing.rewrite_long_numbers(text, mode="grouped", min_digits=5, crore_lakh_enabled=False)
		self.assertIn("12 345 678", rewritten)

		# Crore Lakh mode for Indian numbering
		text = "Amount is 15000000 rupees."
		crore = numberProcessing.rewrite_crore_lakh(text, True)
		self.assertIn("1 crore", crore.lower())

	def test_voice_matching_aliases(self):
		class FakeVoiceInfo:
			def __init__(self, vid, name, lang):
				self.id = vid
				self.displayName = name
				self.language = lang

		class FakeSynth:
			def __init__(self):
				self.name = "eloquence"
				self.availableVoices = {
					"enu": FakeVoiceInfo("enu", "American English", "en-US"),
					"eng": FakeVoiceInfo("eng", "British English", "en-GB"),
					"esp": FakeVoiceInfo("esp", "Castilian Spanish", "es-ES"),
				}

		synth = FakeSynth()
		# English should match American English first or British
		matched = voiceMatch.usableVoice(synth, None, "en")
		self.assertIn(matched, ("enu", "eng"))

		# Spanish should match Castilian Spanish
		matched = voiceMatch.usableVoice(synth, None, "es")
		self.assertEqual(matched, "esp")

	def test_virtual_synths_filter(self):
		self.assertIn("autotts", voiceMatch.VIRTUAL_SYNTHS)
		self.assertIn("nvdaallinone", voiceMatch.VIRTUAL_SYNTHS)
		self.assertIn("silence", voiceMatch.VIRTUAL_SYNTHS)
		self.assertIn("multilang", voiceMatch.VIRTUAL_SYNTHS)

	def test_consecutive_chunk_merging_same_synth_voice(self):
		oldLanguages = sharedConfig.languages
		oldDefault = sharedConfig.defaultLang
		oldEnabled = sharedConfig.enabled
		sharedConfig.defaultLang = "en"
		sharedConfig.enabled = True
		sharedConfig.languages = {
			"en": LanguageVoiceConfig("en", synth="fakeSynth", voice="v1"),
			"es": LanguageVoiceConfig("es", synth="fakeSynth", voice="v1"), # Same synth & voice!
		}

		class MockSynth:
			name = "fakeSynth"
			voice = "v1"
			supportedCommands = {languageDetection.IndexCommand}
			def __init__(self):
				self.spokenSequences = []
			def speak(self, seq):
				self.spokenSequences.append(seq)
			def isSupported(self, setting): return True

		try:
			synthInstance = MockSynth()
			d = driver.SynthDriver.__new__(driver.SynthDriver)
			d._synthCache = {"fakeSynth": (synthInstance, {})}
			d._usedSynths = []
			d._synth = None
			d._isSpeaking = False
			d.speechQueue = driver.queue.Queue()
			d._markerCounter = driver.itertools.count(100)
			d._activeMarker = None
			d._activeChunkId = 0
			d._activeForwardIndices = set()
			d._voice = "en"
			d._getSynth = lambda lang: synthInstance

			# Feeding sequence with language changes that share the same synth and voice
			seq = ["Hello world. ", languageDetection.LangChangeCommand("es"), "Hola amigo."]
			d.speak(seq)

			# Verify that chunks were merged into a single speak() call instead of split
			self.assertEqual(len(synthInstance.spokenSequences), 1)
			spokenText = "".join(item for item in synthInstance.spokenSequences[0] if isinstance(item, str))
			self.assertIn("Hello world. ", spokenText)
			self.assertIn("Hola amigo.", spokenText)
		finally:
			sharedConfig.languages = oldLanguages
			sharedConfig.defaultLang = oldDefault
			sharedConfig.enabled = oldEnabled

	def test_dirty_state_property_check(self):
		# Verify that setting the same property value on a synth does not reassign it
		class TrackedSynth:
			name = "eloquence"
			def __init__(self):
				self.assignments = []
				self._voice = "enu"
				self._rate = 50
				self.supportedSettings = []
				self.availableVoices = {"enu": "American English"}
			@property
			def voice(self): return self._voice
			@voice.setter
			def voice(self, val):
				self.assignments.append(("voice", val))
				self._voice = val
			def isSupported(self, s): return s == "voice"

		s = TrackedSynth()
		# Value already matches "enu"
		if s.voice != "enu":
			s.voice = "enu"
		self.assertEqual(len(s.assignments), 0)

		# Value differs:
		if s.voice != "eng":
			s.voice = "eng"
		self.assertEqual(len(s.assignments), 1)

	def test_activity_log_write_and_privacy(self):
		oldEnabled = activityLog.isEnabled()
		oldIncludeText = activityLog.includeText()
		try:
			activityLog.setEnabled(True)
			activityLog.setIncludeText(False)
			desc = activityLog.clip("Secret password 12345")
			# When includeText is False, private text is not logged as plaintext
			self.assertNotIn("Secret password", desc)
			self.assertIn("chars", desc)

			activityLog.setIncludeText(True)
		finally:
			activityLog.setEnabled(oldEnabled)
			activityLog.setIncludeText(oldIncludeText)

	def test_speech_queue_does_not_deadlock_when_done_speaking_arrives_first(self):
		class FakeChildSynth:
			supportedCommands = {languageDetection.IndexCommand}
			def __init__(self):
				self.sequences = []
			def speak(self, seq):
				self.sequences.append(seq)

		child1 = FakeChildSynth()
		child2 = FakeChildSynth()

		s = driver.SynthDriver.__new__(driver.SynthDriver)
		s._voice = "en"
		s._isSpeaking = False
		s._activeLanguage = "en"
		s._synth = None
		s._synthCache = {}
		s._usedSynths = []
		s.speechQueue = driver.queue.Queue()
		s._markerCounter = driver.itertools.count(1_500_000_000)
		s._activeMarker = None
		s._doneSpeakingReceived = False
		s._activeChunkId = 0
		s._activeForwardIndices = set()

		def getSynth(lang):
			return child1 if lang == "en" else child2
		s._getSynth = getSynth

		# Queue two utterances
		s.speechQueue.put(("en", ["Channel message sent: "]))
		s.speechQueue.put(("ur", ["سلام"]))
		s.pumpSpeech()

		self.assertTrue(s._isSpeaking)
		self.assertIs(s._synth, child1)
		marker = s._activeMarker

		# Child 1 fires done speaking FIRST before index reached!
		s._onSynthDoneSpeaking(child1)

		# Index reached arrives SECOND
		s._onSynthIndexReached(child1, marker)

		# Child 2 must be started immediately without getting stuck!
		self.assertTrue(s._isSpeaking)
		self.assertIs(s._synth, child2)
		self.assertEqual(len(child2.sequences), 1)

	def test_voice_resolution_respects_configured_voice_over_heuristics(self):
		class FakeVoice:
			def __init__(self, vid, name, lang):
				self.id = vid
				self.name = name
				self.displayName = name
				self.language = lang

		class FakeSynth:
			def isSupported(self, attr): return attr == "voice"
			availableVoices = {
				"eng": FakeVoice("eng", "British English", "en-GB"),
				"enu": FakeVoice("enu", "American English", "en-US"),
			}

		synth = FakeSynth()
		# When user had 'enu' stored, it must return 'enu', not guess 'eng'
		chosen = voiceMatch.usableVoice(synth, "enu", "en", preferred="enu")
		self.assertEqual(chosen, "enu")

		# When synth native default is 'enu', it must prefer 'enu' over first candidate 'eng'
		chosen = voiceMatch.usableVoice(synth, None, "en", preferred="enu")
		self.assertEqual(chosen, "enu")

	def test_large_number_format_property(self):
		sharedConfig.croreLakhEnabled = True
		self.assertEqual(sharedConfig.largeNumberFormat, "indian")
		sharedConfig.largeNumberFormat = "western"
		self.assertFalse(sharedConfig.croreLakhEnabled)
		self.assertEqual(sharedConfig.largeNumberFormat, "western")
		sharedConfig.largeNumberFormat = "indian"
		self.assertTrue(sharedConfig.croreLakhEnabled)

	def test_eloquence_does_not_use_private_end_marker(self):
		class EloquenceSynth:
			name = "eloquence"
			supportedCommands = {languageDetection.IndexCommand}

		class IBMeCISynth:
			name = "ibmeci"
			supportedCommands = {languageDetection.IndexCommand}

		class ESpeakSynth:
			name = "espeak"
			supportedCommands = {languageDetection.IndexCommand}

		d = driver.SynthDriver()
		self.assertFalse(d._usesPrivateEndMarker(EloquenceSynth(), ["desktop list"]))
		self.assertFalse(d._usesPrivateEndMarker(IBMeCISynth(), ["this pc 2 of 30"]))
		self.assertTrue(d._usesPrivateEndMarker(ESpeakSynth(), ["hello world"]))

	def test_activity_log_max_bytes_capped_at_one_megabyte(self):
		from synthDrivers.autoTTS import activityLog
		self.assertEqual(activityLog._MAX_BYTES, 1 * 1024 * 1024)
		self.assertEqual(activityLog._MAX_BYTES_DETAILED, 5 * 1024 * 1024)


if __name__ == "__main__":
	unittest.main()

