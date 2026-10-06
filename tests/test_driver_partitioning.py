import itertools
import queue
import unittest
from unittest import mock

import synthDrivers.autoTTS as driver
from synthDrivers.autoTTS import languageDetection
from synthDrivers.autoTTS.configManager import LanguageVoiceConfig, sharedConfig


class DriverPartitioningTests(unittest.TestCase):
	def setUp(self):
		self.oldLanguages = sharedConfig.languages
		self.oldDefault = sharedConfig.defaultLang
		self.oldEnabled = sharedConfig.enabled
		self.oldUnicodeDetection = sharedConfig.useUnicodeLanguageDetection
		self.oldSave = sharedConfig.save
		sharedConfig.save = lambda: None
		driver.LangChangeCommand = languageDetection.LangChangeCommand
		driver.IndexCommand = languageDetection.IndexCommand
		sharedConfig.defaultLang = "ur"
		sharedConfig.enabled = True
		sharedConfig.useUnicodeLanguageDetection = True
		sharedConfig.languages = {
			"ur": LanguageVoiceConfig("ur", synth="fake", voice="urdu"),
			"en": LanguageVoiceConfig("en", synth="fake", voice="english"),
		}
		self.synth = driver.SynthDriver.__new__(driver.SynthDriver)
		self.synth._voice = "ur"
		self.synth._isSpeaking = False
		self.synth._activeLanguage = "ur"
		self.synth._synth = None
		self.synth._synthCache = {}
		self.synth.speechQueue = queue.Queue()
		self.synth._availableVoicesCache = {"ur": object(), "en": object()}
		self.synth._markerCounter = itertools.count(1_500_000_000)
		self.synth._activeMarker = None
		self.synth._activeChunkId = 0
		self.synth._activeForwardIndices = set()
		self.synth.pumpSpeech = lambda: None

	def tearDown(self):
		sharedConfig.languages = self.oldLanguages
		sharedConfig.defaultLang = self.oldDefault
		sharedConfig.enabled = self.oldEnabled
		sharedConfig.useUnicodeLanguageDetection = self.oldUnicodeDetection
		sharedConfig.save = self.oldSave

	def drain(self):
		chunks = []
		while not self.synth.speechQueue.empty():
			chunks.append(self.synth.speechQueue.get_nowait())
		return chunks

	def test_recursive_auto_tts_child_is_rejected_before_construction(self):
		with mock.patch.object(driver, "_getSynthInstance") as constructor:
			self.assertIsNone(self.synth._getSynthByName("autoTTS"))
			constructor.assert_not_called()

	def test_language_chunks_remain_in_source_order(self):
		index = languageDetection.IndexCommand(7)
		self.synth.speak([index, "پہلے English بعد"])
		chunks = self.drain()
		self.assertEqual([lang for lang, sequence in chunks], ["ur", "en", "ur"])
		self.assertEqual(
			"".join(item for lang, sequence in chunks for item in sequence if isinstance(item, str)),
			"پہلے English بعد",
		)
		self.assertEqual(
			sum(isinstance(item, languageDetection.IndexCommand) for lang, sequence in chunks for item in sequence),
			1,
		)

	def test_different_prosody_requires_a_chunk_boundary(self):
		sharedConfig.languages["en"].voice = "urdu"
		sharedConfig.languages["en"].useCustomProsody = True
		sharedConfig.languages["en"].customRate = 70
		self.synth.speak(["پہلے English بعد"])
		self.assertEqual([lang for lang, sequence in self.drain()], ["ur", "en", "ur"])

	def test_private_marker_waits_for_done_before_finishing_a_chunk(self):
		class FakeSynth:
			supportedCommands = {languageDetection.IndexCommand}
			def __init__(self):
				self.sequence = None
			def speak(self, sequence):
				self.sequence = sequence

		fake = FakeSynth()
		self.synth._getSynth = lambda lang: fake
		self.synth.pumpSpeech = driver.SynthDriver.pumpSpeech.__get__(self.synth)
		self.synth.speechQueue.put(("ur", ["متن"]))
		self.synth.pumpSpeech()
		marker = self.synth._activeMarker
		self.assertTrue(self.synth._isSpeaking)
		self.synth._onSynthIndexReached(FakeSynth(), marker)
		self.assertTrue(self.synth._isSpeaking)
		self.synth._onSynthIndexReached(fake, marker)
		self.assertTrue(self.synth._isSpeaking)
		self.synth._onSynthDoneSpeaking(fake)
		self.assertFalse(self.synth._isSpeaking)

	def test_next_language_does_not_start_until_previous_synth_is_done(self):
		class FakeSynth:
			supportedCommands = {languageDetection.IndexCommand}
			def __init__(self, name):
				self.name = name
				self.sequences = []
			def speak(self, sequence):
				self.sequences.append(sequence)

		english = FakeSynth("eloquence")
		urdu = FakeSynth("googleTtsForNvda")
		preparedLanguages = []
		def getSynth(lang):
			preparedLanguages.append(lang)
			return english if lang == "en" else urdu
		self.synth._getSynth = getSynth
		self.synth.pumpSpeech = driver.SynthDriver.pumpSpeech.__get__(self.synth)
		self.synth.speechQueue.put(("en", ["Rehan Malik "]))
		self.synth.speechQueue.put(("ur", ["آج کی آیت"] ))
		self.synth.pumpSpeech()

		marker = self.synth._activeMarker
		self.assertEqual(preparedLanguages, ["en", "ur"])
		self.synth._onSynthIndexReached(english, marker)
		self.assertEqual(len(urdu.sequences), 0)
		self.synth._onSynthDoneSpeaking(english)
		self.assertEqual(len(urdu.sequences), 1)

	def test_google_tts_uses_done_event_without_espeak_fallback(self):
		class FakeSynth:
			supportedCommands = {languageDetection.IndexCommand}
			name = "googleTtsForNvda"
			def __init__(self):
				self.sequences = []
			def speak(self, sequence):
				self.sequences.append(sequence)

		google = FakeSynth()
		self.synth._getSynth = lambda lang: google
		self.synth.pumpSpeech = driver.SynthDriver.pumpSpeech.__get__(self.synth)
		self.synth.speechQueue.put(("ur", ["مکمل اردو متن"]))
		self.synth.pumpSpeech()

		self.assertIsNone(self.synth._activeMarker)
		self.assertEqual(len(google.sequences), 1)
		self.assertFalse(any(isinstance(item, languageDetection.IndexCommand) for item in google.sequences[0]))
		self.synth._onSynthDoneSpeaking(google)
		self.assertFalse(self.synth._isSpeaking)

	def test_arbitrary_configured_bcp47_language_is_routable(self):
		sharedConfig.useUnicodeLanguageDetection = False
		sharedConfig.languages["sw-ke"] = LanguageVoiceConfig("sw-ke", synth="fake", voice="swahili")
		self.synth.speak([languageDetection.LangChangeCommand("sw-KE"), "Habari"])
		self.assertEqual([lang for lang, sequence in self.drain()], ["sw-ke"])

	def test_base_detector_tag_routes_to_configured_regional_profile(self):
		sharedConfig.languages = {
			"en": LanguageVoiceConfig("en", synth="eloquence", voice="english"),
			"ur-pk": LanguageVoiceConfig("ur-pk", synth="googleTtsForNvda", voice="ur-PK"),
		}
		sharedConfig.defaultLang = "en"
		self.synth._voice = "en"
		self.synth.speak([languageDetection.LangChangeCommand("ur"), "اردو متن"])
		chunks = self.drain()
		self.assertEqual([lang for lang, sequence in chunks], ["ur-pk"])
		self.assertEqual(sharedConfig.getLanguageConfig("ur").synth, "googleTtsForNvda")

	def test_settings_ring_never_creates_an_unconfigured_language(self):
		class FakeSynth:
			rate = 50
			pitch = 50
			volume = 100

		sharedConfig.languages["ur"].useCustomProsody = True
		self.synth._synth = FakeSynth()
		self.synth._isSpeaking = True
		self.synth._activeLanguage = "af"
		self.synth._set_rate(72)
		self.assertNotIn("af", sharedConfig.languages)
		self.assertEqual(sharedConfig.languages["ur"].customRate, 72)

	def test_ring_lists_only_configured_language_profiles(self):
		self.assertEqual(list(self.synth._getAvailableVoices()), ["en", "ur"])

	def test_base_profile_supports_regional_and_unconfigured_language_tags(self):
		sharedConfig.languages = {
			"en": LanguageVoiceConfig("en", synth="fake", voice="english"),
		}
		self.assertTrue(self.synth.languageIsSupported("en-US"))
		self.assertTrue(self.synth.languageIsSupported("en_GB"))
		self.assertTrue(self.synth.languageIsSupported("fr-FR"))
		self.assertTrue(self.synth.languageIsSupported(None))
		self.assertEqual(sharedConfig.getLanguageConfig("en-US").synth, "fake")

	def test_zero_profile_fallback_keeps_nvda_language_and_espeak_route_valid(self):
		sharedConfig.languages = {}
		self.synth._voice = "en"
		self.assertEqual(list(self.synth._getAvailableVoices()), ["en"])
		self.assertEqual(self.synth._get_language(), "en")
		self.assertTrue(self.synth.isSupported("voice"))

	def test_ring_edits_child_synth_when_custom_prosody_is_off(self):
		class FakeSynth:
			rate = 50

		fake = FakeSynth()
		self.synth._getSynth = lambda lang: fake
		self.synth._synthCache = {"fake": (fake, {"rate": 50})}
		self.synth._voice = "ur"
		self.synth._activeLanguage = "en"
		self.synth._set_rate(72)
		self.assertEqual(fake.rate, 72)
		self.assertEqual(self.synth._synthCache["fake"][1]["rate"], 72)
		self.assertFalse(sharedConfig.languages["ur"].useCustomProsody)
		self.assertEqual(sharedConfig.languages["ur"].customRate, -1)

	def test_ring_edits_only_profile_when_custom_prosody_is_on(self):
		class FakeSynth:
			pitch = 40

		fake = FakeSynth()
		sharedConfig.languages["ur"].useCustomProsody = True
		self.synth._getSynth = lambda lang: fake
		self.synth._synthCache = {"fake": (fake, {"pitch": 40})}
		self.synth._voice = "ur"
		self.synth._set_pitch(67)
		self.assertEqual(sharedConfig.languages["ur"].customPitch, 67)
		self.assertEqual(fake.pitch, 40)
		self.assertEqual(self.synth._synthCache["fake"][1]["pitch"], 40)

	def test_ring_uses_selected_profile_not_currently_speaking_language(self):
		class FakeSynth:
			def __init__(self, rate):
				self.rate = rate

		synths = {"ur": FakeSynth(61), "en": FakeSynth(79)}
		self.synth._getSynth = lambda lang: synths[lang]
		self.synth._voice = "ur"
		self.synth._activeLanguage = "en"
		self.synth._isSpeaking = True
		self.assertEqual(self.synth._get_rate(), 61)

	def test_load_settings_initializes_nvda_settings_ring(self):
		oldLoad = sharedConfig.load
		oldChangeVoice = driver.synthDriverHandler.changeVoice
		calls = []
		try:
			sharedConfig.load = lambda: None
			driver.synthDriverHandler.changeVoice = lambda synth, voice: calls.append((synth, voice))
			self.synth.loadSettings()
		finally:
			sharedConfig.load = oldLoad
			driver.synthDriverHandler.changeVoice = oldChangeVoice
		self.assertEqual(calls, [(self.synth, "ur")])


if __name__ == "__main__":
	unittest.main()
