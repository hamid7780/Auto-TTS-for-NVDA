"""Speech queue, prosody and settings-ring behaviour fixed in 1.2.0."""

import itertools
import queue
import unittest
from unittest import mock

import synthDrivers.autoTTS as driver
from synthDrivers.autoTTS import languageDetection as ld
from synthDrivers.autoTTS.configManager import LanguageVoiceConfig, sharedConfig


def bareDriver():
	d = driver.SynthDriver.__new__(driver.SynthDriver)
	d._voice = "en"
	d._isSpeaking = True
	d._synth = None
	d._synthCache = {}
	d._usedSynths = []
	d.speechQueue = queue.Queue()
	d._markerCounter = itertools.count(1_500_000_000)
	d._activeMarker = None
	d._doneSpeakingReceived = False
	d._activeChunkId = 0
	d._activeForwardIndices = set()
	return d


class QueueTests(unittest.TestCase):
	def test_done_speaking_is_reported_only_when_the_queue_is_empty(self):
		d = bareDriver()
		started = []
		d._startChunk = lambda lang, seq: started.append(lang)
		d.speechQueue.put(("en", [ld.IndexCommand(1)], False))
		d.speechQueue.put(("ur", ["اردو"], True))
		with mock.patch.object(driver.synthDoneSpeaking, "notify") as done, \
				mock.patch.object(driver.synthIndexReached, "notify") as indexReached:
			d._processNextChunkOrFinish()
			indexReached.assert_called_once()
			done.assert_not_called()
			self.assertEqual(started, ["ur"])
			d._processNextChunkOrFinish()
			done.assert_called_once()

	def test_child_done_from_another_thread_is_handled_on_the_main_thread(self):
		d = bareDriver()
		child = object()
		d._synth = child
		calls = []
		with mock.patch.object(driver.SynthDriver, "_onMainThread", side_effect=lambda f, *a: calls.append((f.__name__, a))):
			d._onSynthDoneSpeaking(child)
		self.assertEqual(calls, [("_handleChildDone", (child, 0))])

	def test_a_late_done_for_an_old_chunk_is_ignored(self):
		d = bareDriver()
		child = object()
		d._synth = child
		d._activeChunkId = 5
		d._finishActiveChunk = mock.Mock()
		d._handleChildDone(child, 4)
		d._finishActiveChunk.assert_not_called()
		d._handleChildDone(child, 5)
		d._finishActiveChunk.assert_called_once_with(child, 5)


class ProsodyTests(unittest.TestCase):
	def test_relative_prosody_is_measured_against_the_speaking_child(self):
		class Pitch(driver.BaseProsodyCommand):
			settingName = "pitch"

		class Child:
			pitch = 30

		original = Pitch()
		bound = driver._bindProsodyToChild(original, Child())
		self.assertIsInstance(bound, Pitch)
		self.assertEqual(bound.defaultValue, 30)
		# NVDA's own class and the original command are left alone.
		self.assertEqual(original.defaultValue, 50)
		self.assertEqual(Pitch().defaultValue, 50)

	def test_other_commands_pass_through(self):
		index = ld.IndexCommand(3)
		self.assertIs(driver._bindProsodyToChild(index, object()), index)


class LanguageLockSettingTests(unittest.TestCase):
	def setUp(self):
		self.saved = (sharedConfig.languages, sharedConfig.lockedLanguage)
		sharedConfig.languages = {
			"en": LanguageVoiceConfig("en"),
			"ur": LanguageVoiceConfig("ur"),
			"ar": LanguageVoiceConfig("ar", enabled=False),
		}
		sharedConfig.lockedLanguage = None

	def tearDown(self):
		sharedConfig.languages, sharedConfig.lockedLanguage = self.saved

	def test_lock_choices_and_values(self):
		d = bareDriver()
		self.assertTrue(d.isSupported("languageLock"))
		setting = next(s for s in driver.SynthDriver.supportedSettings if s.id == "languageLock")
		self.assertFalse(setting.useConfig)
		self.assertEqual(list(d._get_availableLanguagelocks()), ["", "en", "ur"])
		d._set_languageLock("ur")
		self.assertEqual(sharedConfig.lockedLanguage, "ur")
		self.assertEqual(d._get_languageLock(), "ur")
		d._set_languageLock("ar")  # disabled profile
		self.assertIsNone(sharedConfig.lockedLanguage)
		d._set_languageLock("")
		self.assertEqual(d._get_languageLock(), "")


class SaveTests(unittest.TestCase):
	def test_ring_changes_save_without_wx_immediately(self):
		# Outside NVDA there is no main loop to delay the save, so it happens at once.
		with mock.patch.object(sharedConfig, "_saveToJSON") as write:
			sharedConfig.scheduleSave()
			write.assert_called_once()


if __name__ == "__main__":
	unittest.main()
