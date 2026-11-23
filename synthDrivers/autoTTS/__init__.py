# Auto TTS for NVDA - Core Synthesizer Driver
# Covered by GNU General Public License (GPL)

import queue
import importlib
import itertools
import time
from collections import OrderedDict
from typing import Dict, Any, Optional

try:
	import wx
	import api
	import synthDriverHandler
	import languageHandler
	import addonHandler
	import config
	from autoSettingsUtils.driverSetting import (
		DriverSetting,
		NumericDriverSetting,
		BooleanDriverSetting,
	)
	from autoSettingsUtils.utils import StringParameterInfo
	from synthDriverHandler import VoiceInfo, synthDoneSpeaking, synthIndexReached
	from synthDrivers.espeak import SynthDriver as EspeakSynthDriver
	from synthDrivers.silence import SynthDriver as SilenceSynthDriver
	from speech.commands import (
		IndexCommand,
		CharacterModeCommand,
		PitchCommand,
		LangChangeCommand,
		BaseProsodyCommand,
	)
	from logHandler import log
	addonHandler.initTranslation()
except ImportError:
	api = None
	class EspeakSynthDriver: name = "espeak"
	class SilenceSynthDriver: name = "silence"
	class VoiceInfo:
		def __init__(self, id, displayName, language=None):
			self.id = id; self.displayName = displayName; self.language = language
	class DriverSetting:
		def __init__(self, id="voice", name="", minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True, useConfig=True):
			self.id = id; self.name = name; self.minStep = minStep; self.minVal = minVal; self.maxVal = maxVal; self.availableInSettingsRing = availableInSettingsRing
			self.useConfig = useConfig
	class StringParameterInfo:
		def __init__(self, id, displayName):
			self.id = id; self.displayName = displayName
	class NumericDriverSetting(DriverSetting):
		def __init__(self, id, name, minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True):
			super().__init__(id, name, minStep=minStep, minVal=minVal, maxVal=maxVal, availableInSettingsRing=availableInSettingsRing)
	class BooleanDriverSetting(DriverSetting):
		def __init__(self, id, name, availableInSettingsRing=True):
			super().__init__(id, name, availableInSettingsRing=availableInSettingsRing)
	class BaseProsodyCommand:
		defaultValue = property(lambda self: 50)
	class synthDriverHandler:
		class SynthDriver:
			VoiceSetting = DriverSetting
			RateSetting = NumericDriverSetting
			PitchSetting = NumericDriverSetting
			VolumeSetting = NumericDriverSetting
			@property
			def availableVoices(self):
				return self._getAvailableVoices()
			def isSupported(self, settingId):
				return any(getattr(s, "id", None) == settingId for s in getattr(self, "supportedSettings", []))
			@property
			def rate(self): return self._get_rate()
			@rate.setter
			def rate(self, val): self._set_rate(val)
			@property
			def pitch(self): return self._get_pitch()
			@pitch.setter
			def pitch(self, val): self._set_pitch(val)
			@property
			def volume(self): return self._get_volume()
			@volume.setter
			def volume(self, val): self._set_volume(val)
			@property
			def voice(self): return self._get_voice()
			@voice.setter
			def voice(self, val): self._set_voice(val)
		@staticmethod
		def changeVoice(synth, voice):
			if voice:
				synth.voice = voice
		@staticmethod
		def getSynthList(): return [("espeak", "eSpeak NG")]
		@staticmethod
		def getSynth(): return None
	# Outside NVDA (unit tests) every module must share one set of command classes,
	# or isinstance checks between the driver and the detector silently fail.
	from .languageDetection import IndexCommand, CharacterModeCommand, LangChangeCommand
	class PitchCommand: pass
	class synthDoneSpeaking:
		@staticmethod
		def register(fn): pass
		@staticmethod
		def unregister(fn): pass
		@staticmethod
		def notify(**kwargs): pass
	class synthIndexReached:
		@staticmethod
		def register(fn): pass
		@staticmethod
		def unregister(fn): pass
		@staticmethod
		def notify(**kwargs): pass
	class log:
		@staticmethod
		def debug(msg): pass
		@staticmethod
		def debugWarning(msg): pass
		@staticmethod
		def error(msg): pass
		@staticmethod
		def exception(msg): pass
	def _(s): return s

from . import languageDetection
from . import numberProcessing
from . import activityLog
from . import voiceMatch
from .configManager import sharedConfig

VIRTUAL_SYNTHS = voiceMatch.VIRTUAL_SYNTHS


def _isLangChangeCommand(item):
	return (
		isinstance(item, (LangChangeCommand, languageDetection.LangChangeCommand))
		or getattr(item, "__class__", None).__name__ == "LangChangeCommand"
	)


def _getSynthInstance(name: str):
	"""Imports and instantiates an underlying NVDA synth driver by name."""
	if not name or name in VIRTUAL_SYNTHS:
		name = "espeak"
	return importlib.import_module(f"synthDrivers.{name}", package="synthDrivers").SynthDriver()


def _isForegroundAppExcluded() -> bool:
	"""Checks if currently focused application is in user's exclusion list."""
	try:
		obj = api.getFocusObject()
		if obj and hasattr(obj, "appModule"):
			appName = getattr(obj.appModule, "appName", "")
			if appName:
				cleanName = appName.lower()
				if not cleanName.endswith(".exe"):
					cleanNameWithExe = f"{cleanName}.exe"
				else:
					cleanNameWithExe = cleanName
				if sharedConfig.isAppExcluded(cleanNameWithExe) or sharedConfig.isAppExcluded(cleanName):
					return True
	except Exception:
		pass
	return False


def _buildSupportedSettings():
	"""Builds official SynthDriver settings recognizing NVDA's built-in setting classes."""
	settings = []
	try:
		if hasattr(synthDriverHandler.SynthDriver, "VoiceSetting"):
			settings.append(synthDriverHandler.SynthDriver.VoiceSetting())
		else:
			settings.append(DriverSetting("voice", _("Default &voice"), availableInSettingsRing=True))

		if hasattr(synthDriverHandler.SynthDriver, "RateSetting"):
			settings.append(synthDriverHandler.SynthDriver.RateSetting())
		else:
			settings.append(NumericDriverSetting("rate", _("&Rate"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True))

		if hasattr(synthDriverHandler.SynthDriver, "PitchSetting"):
			settings.append(synthDriverHandler.SynthDriver.PitchSetting())
		else:
			settings.append(NumericDriverSetting("pitch", _("&Pitch"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True))

		if hasattr(synthDriverHandler.SynthDriver, "VolumeSetting"):
			settings.append(synthDriverHandler.SynthDriver.VolumeSetting())
		else:
			settings.append(NumericDriverSetting("volume", _("V&olume"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True))
	except Exception:
		settings = [
			DriverSetting("voice", _("Default &voice"), availableInSettingsRing=True),
			NumericDriverSetting("rate", _("&Rate"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True),
			NumericDriverSetting("pitch", _("&Pitch"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True),
			NumericDriverSetting("volume", _("V&olume"), minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True),
		]
	# The language lock (NVDA+Alt+L) is also reachable from the settings ring. useConfig=False:
	# NVDA never stores it, so a lock always ends when NVDA restarts.
	settings.append(DriverSetting("languageLock", _("&Language lock"), availableInSettingsRing=True, useConfig=False))
	return tuple(settings)


_SLOW_CALL_MS = 3.0


def _logIfSlow(what, startedAt, detail=""):
	elapsed = (time.perf_counter() - startedAt) * 1000.0
	if elapsed >= _SLOW_CALL_MS:
		try:
			log.debug(f"AutoTTS: {what} took {elapsed:.1f} ms {detail}".rstrip())
		except Exception:
			pass


def _activeAutoTTS():
	"""The Auto TTS driver NVDA is speaking with, or None."""
	try:
		synth = synthDriverHandler.getSynth()
	except Exception:
		return None
	return synth if isinstance(synth, SynthDriver) else None


def _installProsodyRouting():
	"""Make relative pitch, rate and volume commands (a capital letter's higher pitch) measure
	themselves against the child voice that speaks them, not against Auto TTS's own settings.

	The commands must stay NVDA's own objects: eSpeak, SAPI5 and Eloquence recognise them by
	their exact class (type(item)), so a copy or subclass is silently ignored. Only how their
	base value is looked up changes, and only while Auto TTS is the active synthesizer;
	otherwise NVDA's original lookup runs. Installed once, however many drivers exist."""
	current = BaseProsodyCommand.defaultValue
	if getattr(getattr(current, "fget", None), "_autoTTSOriginal", None) is not None:
		return

	def defaultValue(cmd, _original=current):
		auto = _activeAutoTTS()
		child = auto._synth if auto is not None else None
		name = getattr(cmd, "settingName", None)
		if child is not None and name:
			try:
				return getattr(child, name)
			except Exception:
				pass
		return _original.fget(cmd)

	defaultValue._autoTTSOriginal = current
	BaseProsodyCommand.defaultValue = property(defaultValue)


def _uninstallProsodyRouting():
	original = getattr(getattr(BaseProsodyCommand.defaultValue, "fget", None), "_autoTTSOriginal", None)
	if original is not None:
		BaseProsodyCommand.defaultValue = original


def _nvdaVocabulary() -> frozenset:
	"""NVDA's role and state names as they reach speech ("link", "button", "not checked").
	They are never statistically scored for language: a lone short word is weak evidence."""
	words = set()
	try:
		import controlTypes
	except ImportError:
		return frozenset()
	for enum, negative in ((getattr(controlTypes, "Role", None), False), (getattr(controlTypes, "State", None), True)):
		if enum is None:
			continue
		try:
			# Read the label table directly: displayString logs an error for members without a label.
			labels = next(iter(enum))._displayStringLabels
		except Exception:
			continue
		for member in enum:
			label = labels.get(member)
			if label:
				words.add(str(label).strip().lower())
			if negative:
				try:
					words.add(str(member.negativeDisplayString).strip().lower())
				except Exception:
					pass
	words.discard("")
	return frozenset(words)


class SynthDriver(synthDriverHandler.SynthDriver):
	name = "autoTTS"
	description = _("Auto TTS for NVDA")

	supportedSettings = _buildSupportedSettings()
	_activePreparedLang = None
	_paused = False
	_nvdaWords: Optional[frozenset] = None

	def __init__(self):
		self._synthCache: Dict[str, Any] = {}
		self._usedSynths = []
		self._synth = None
		self._activePreparedLang: Optional[str] = None
		self._paused = False
		self._nvdaWords: Optional[frozenset] = None
		self._isSpeaking = False
		self.speechQueue = queue.Queue()
		self._markerCounter = itertools.count(1_500_000_000)
		self._activeMarker = None
		self._doneSpeakingReceived = False
		self._activeChunkId = 0
		self._activeForwardIndices = set()
		self._everActive = False
		_installProsodyRouting()

		# Initialize default language
		try:
			systemLang = languageHandler.getLanguage().split("_")[0]
		except Exception:
			systemLang = "en"

		self._voice = sharedConfig.defaultLang or systemLang
		if self._voice not in self.availableVoices:
			normVoice = languageDetection.get_base_language(self._voice)
			self._voice = normVoice if normVoice in self.availableVoices else next(iter(self.availableVoices), "en")

		synthDriverHandler.changeVoice(self, self._voice)

		synthDoneSpeaking.register(self._onSynthDoneSpeaking)
		synthIndexReached.register(self._onSynthIndexReached)
		activityLog.write("START", f"AutoTTS driver initialized with default voice '{self._voice}'")

	def terminate(self):
		# Unregister global handlers FIRST
		try:
			synthIndexReached.unregister(self._onSynthIndexReached)
		except Exception:
			pass
		try:
			synthDoneSpeaking.unregister(self._onSynthDoneSpeaking)
		except Exception:
			pass
		# A temporary instance (NVDA's settings dialogs make some) must not remove the routing
		# the active one relies on.
		if _activeAutoTTS() is self:
			_uninstallProsodyRouting()

		try:
			self.cancel()
		except Exception:
			pass

		self._synth = None
		self._activePreparedLang = None
		self._isSpeaking = False
		sharedConfig.flushPendingSave()

		# Only terminate child synths if this instance was actively used
		if getattr(self, "_everActive", False):
			for synth, defaultConf in list(self._synthCache.values()):
				try:
					synth.cancel()
					synth.terminate()
				except Exception:
					pass
		self._synthCache.clear()
		activityLog.write("START", "AutoTTS driver terminated")

	def saveSettings(self):
		"""Saves AutoTTS settings to NVDA config."""
		sharedConfig.defaultLang = self._voice
		sharedConfig.save()

	def loadSettings(self, onlyChanged=False):
		"""Loads AutoTTS settings from NVDA config and refreshes profile routing without destroying cached synths."""
		sharedConfig.load()
		self._activePreparedLang = None

		try:
			systemLang = languageHandler.getLanguage().split("_")[0]
		except Exception:
			systemLang = "en"
		self._voice = sharedConfig.defaultLang or systemLang
		if self._voice not in self.availableVoices:
			normVoice = languageDetection.get_base_language(self._voice)
			self._voice = normVoice if normVoice in self.availableVoices else next(iter(self.availableVoices), "en")

		synthDriverHandler.changeVoice(self, self._voice)
		self._rebindSettingsRing()

	@classmethod
	def check(cls):
		return True

	supportedCommands = {
		IndexCommand,
		CharacterModeCommand,
		PitchCommand,
		LangChangeCommand,
	}
	try:
		import speech.commands as _sc
		for _cmdName in (
			"PhonemeCommand", "BreakCommand", "BeepCommand", "EndUtteranceCommand",
			"RateCommand", "VolumeCommand",
		):
			_cmd = getattr(_sc, _cmdName, None)
			if _cmd is not None:
				supportedCommands.add(_cmd)
	except Exception:
		pass

	supportedNotifications = {synthIndexReached, synthDoneSpeaking}

	def isSupported(self, settingId):
		return any(getattr(s, "id", None) == settingId for s in self.supportedSettings)

	def languageIsSupported(self, lang):
		return True

	def _getSettingsLanguage(self):
		"""Configured language explicitly selected in NVDA's settings ring."""
		candidates = (self._voice, sharedConfig.defaultLang)
		for candidate in candidates:
			if not candidate:
				continue
			normFull, baseLang = languageDetection.normalize_language_code(candidate)
			for configured in (candidate, normFull, baseLang):
				if configured in sharedConfig.languages:
					return configured
		return None

	def _getSettingsSynth(self, settingsLang=None):
		settingsLang = settingsLang or self._getSettingsLanguage()
		return self._getSynth(settingsLang) if settingsLang else None

	def _setProsodySetting(self, settingId, customAttribute, val, fallback):
		try:
			val = max(0, min(100, int(val)))
		except Exception:
			val = fallback
		settingsLang = self._getSettingsLanguage()
		if not settingsLang:
			return
		langConfig = sharedConfig.languages.get(settingsLang)
		if not langConfig:
			return
		if langConfig.useCustomProsody:
			setattr(langConfig, customAttribute, val)
			sharedConfig.setLanguageConfig(langConfig, saveLater=True)
			# Re-apply the profile on the next utterance; the fast path in _getSynth
			# would otherwise keep speaking with the old value.
			self._activePreparedLang = None
			return

		synth = self._getSettingsSynth(settingsLang)
		if synth is None or not hasattr(synth, settingId):
			return
		try:
			if getattr(synth, settingId, None) != val:
				setattr(synth, settingId, val)
		except Exception:
			return
		self._saveUnderlyingSynthSetting(settingsLang, synth, settingId, val)

	def _get_rate(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang and settingsLang in sharedConfig.languages:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customRate >= 0:
				return defCfg.customRate
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "rate", 50) if synth else 50

	def _set_rate(self, val):
		self._setProsodySetting("rate", "customRate", val, 50)

	def _get_pitch(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang and settingsLang in sharedConfig.languages:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customPitch >= 0:
				return defCfg.customPitch
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "pitch", 50) if synth else 50

	def _set_pitch(self, val):
		self._setProsodySetting("pitch", "customPitch", val, 50)

	def _get_volume(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang and settingsLang in sharedConfig.languages:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customVolume >= 0:
				return defCfg.customVolume
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "volume", 100) if synth else 100

	def _set_volume(self, val):
		self._setProsodySetting("volume", "customVolume", val, 100)

	@staticmethod
	def _onMainThread(func, *args):
		"""Run func on NVDA's main thread. Child synths report from their own audio threads
		(eSpeak, OneCore), and wx timers and Auto TTS's queue must only be touched on the main one."""
		try:
			onMain = wx.IsMainThread()
		except Exception:  # outside NVDA (tests)
			onMain = True
		if onMain:
			func(*args)
		else:
			wx.CallAfter(func, *args)

	def _onSynthDoneSpeaking(self, synth):
		"""Completion reported by a child synth, on whatever thread it uses."""
		if synth is self or synth is not self._synth or not self._isSpeaking:
			return
		self._onMainThread(self._handleChildDone, synth, self._activeChunkId)

	def _handleChildDone(self, synth, chunkId):
		if chunkId != self._activeChunkId or not self._isSpeaking or synth is not self._synth:
			return
		if getattr(synth, "name", "") == "sapi5":
			# SAPI5 reports the end of each stream. While the voice is still speaking, wait for
			# its next report; the watchdog covers one that never comes. Never block here.
			try:
				if synth.tts.Status.RunningState in (0, 2):
					return
			except Exception:
				pass
		if activityLog.isEnabled():
			activityLog.write("DONE", f"Synth '{getattr(synth, 'name', '')}' done chunk #{chunkId}")

		# If waiting on a private marker, mark doneSpeaking as received and start safety timeout
		# so a dropped IndexCommand never causes a speech deadlock!
		if self._activeMarker is not None:
			self._doneSpeakingReceived = True
			self._scheduleMarkerTimeout(synth, chunkId)
			return

		self._finishActiveChunk(synth, chunkId)

	def _scheduleMarkerTimeout(self, synth, chunkId):
		def _onTimeout():
			if getattr(self, "_activeChunkId", None) == chunkId and getattr(self, "_isSpeaking", False):
				if self._activeMarker is not None:
					activityLog.write("DEBUG", f"Private marker timed out on chunk #{chunkId}; completing chunk safely")
					self._activeMarker = None
					self._doneSpeakingReceived = False
					self._finishActiveChunk(synth, chunkId)
		try:
			wx.CallLater(35, _onTimeout)
		except Exception:
			pass

	def _usesPrivateEndMarker(self, synth, sequence=None):
		"""Whether this child can reliably return Auto TTS's trailing marker.
		Synths that have their own internal sentinel end markers (like Eloquence /
		IBMeCI) must NEVER receive Auto TTS private trailing markers. In Eloquence,
		an extra trailing marker steals pending audio from Eloquence's own 0xFFFF
		sentinel, causing premature player.idle() calls that create an audible
		stutter/chop at the end of every utterance."""
		try:
			if IndexCommand not in getattr(synth, "supportedCommands", set()):
				return False
			identity = "{} {}".format(
				getattr(synth, "name", ""),
				getattr(type(synth), "__module__", ""),
			).lower()
			if any(k in identity for k in ("googlettsfornvda", "eloquence", "ibmeci", "eci", "openevv")):
				return False
			# Never use private end markers for empty or purely punctuation/symbol utterances:
			# synthesizers produce no phonemes and drop IndexCommand on them.
			if sequence is not None:
				has_words = any(
					any(c.isalnum() for c in item)
					for item in sequence
					if isinstance(item, str)
				)
				if not has_words:
					return False
			return True
		except Exception:
			return False

	def _finishActiveChunk(self, synth, chunkId):
		if not self._isSpeaking or chunkId != self._activeChunkId:
			return
		if synth is not None and self._synth is not None and synth is not self._synth:
			if not any(used is synth for used in self._usedSynths):
				return
		self._activeMarker = None
		self._doneSpeakingReceived = False
		self._activeForwardIndices.clear()
		self._processNextChunkOrFinish(synth)

	def _processNextChunkOrFinish(self, synth=None):
		while True:
			try:
				chunk = self.speechQueue.get_nowait()
			except queue.Empty:
				self._isSpeaking = False
				self._activeLanguage = self._voice
				self._activeMarker = None
				self._doneSpeakingReceived = False
				self._activeForwardIndices.clear()
				synthDoneSpeaking.notify(synth=self)
				return

			if len(chunk) == 3:
				lang, speechSequence, hasText = chunk
			else:
				lang, speechSequence = chunk
				hasText = any(isinstance(item, str) and not item.isspace() for item in speechSequence)

			if hasText:
				self._startChunk(lang, speechSequence)
				return

			# Chunk has no speakable text (only IndexCommand or whitespace): report its indexes
			# and go on with the queue. Speech is done only when the queue is empty; reporting
			# it here made NVDA think Auto TTS had finished while chunks were still waiting.
			for item in speechSequence:
				if isinstance(item, IndexCommand) and hasattr(item, "index"):
					try:
						synthIndexReached.notify(synth=self, index=item.index)
					except Exception:
						pass

	def _onSynthIndexReached(self, synth, index):
		if synth is self or synth is not self._synth or not self._isSpeaking:
			return
		if index == self._activeMarker:
			self._onMainThread(self._handleMarkerReached, synth, self._activeChunkId, index)
		elif index in self._activeForwardIndices:
			try:
				synthIndexReached.notify(synth=self, index=index)
			except Exception:
				pass

	def _handleMarkerReached(self, synth, chunkId, index):
		if chunkId != self._activeChunkId or index != self._activeMarker:
			return
		self._activeMarker = None
		if self._doneSpeakingReceived:
			self._doneSpeakingReceived = False
			self._finishActiveChunk(synth, chunkId)

	def _markSynthUsed(self, synth):
		if synth is not None and not any(used is synth for used in self._usedSynths):
			self._usedSynths.append(synth)

	@staticmethod
	def _alignLanguageCommands(synth, speechSequence):
		"""Aligns LangChangeCommand subtag with target voice language to keep voice selection intact."""
		try:
			voiceLang = getattr(synth, "language", None)
		except Exception:
			return speechSequence
		if not voiceLang or not isinstance(voiceLang, str):
			return speechSequence
		primary = voiceLang.replace("_", "-").split("-")[0].lower()
		out = []
		for item in speechSequence:
			if (
				_isLangChangeCommand(item)
				and item.lang
				and item.lang.replace("_", "-").split("-")[0].lower() == primary
			):
				out.append(LangChangeCommand(voiceLang))
			else:
				out.append(item)
		return out

	def _startChunk(self, lang, speechSequence):
		self._activeLanguage = lang
		startedAt = time.perf_counter()
		self._synth = self._getSynth(lang)
		self._activePreparedLang = lang
		_logIfSlow("preparing the voice", startedAt, f"(language {lang})")
		self._markSynthUsed(self._synth)
		if self._synth is None:
			self._processNextChunkOrFinish()
			return

		sequence = list(speechSequence)
		self._activeForwardIndices = {
			item.index for item in sequence if isinstance(item, IndexCommand) and hasattr(item, "index")
		}
		self._activeChunkId += 1
		chunkId = self._activeChunkId
		self._activeMarker = None
		self._doneSpeakingReceived = False

		try:
			if self._usesPrivateEndMarker(self._synth, sequence):
				marker = next(self._markerCounter)
				while marker in self._activeForwardIndices:
					marker = next(self._markerCounter)
				self._activeMarker = marker
				insertAt = len(sequence)
				while insertAt > 0 and sequence[insertAt - 1].__class__.__name__ == "EndUtteranceCommand":
					insertAt -= 1
				sequence.insert(insertAt, IndexCommand(marker))

			alignedSeq = self._alignLanguageCommands(self._synth, sequence)
			if activityLog.isEnabled():
				# Formatting reads every prosody property of the child synth; only pay for it when logging.
				activityLog.write(
					"SPEAK",
					f"lang={lang} -> {getattr(self._synth, 'name', '')} "
					f"[{activityLog.describeSynth(self._synth)}] seq: {activityLog.describeSequence(alignedSeq)}"
				)
			self._synth.speak(alignedSeq)
			self._prewarmNextQueuedSynth()
			# Generous on purpose: at the slowest rates a voice reads about 5 characters a second,
			# and firing early would start the next chunk over the one still speaking.
			totalChars = sum(len(x) for x in sequence if isinstance(x, str))
			self._armWatchdog(chunkId, self._synth, max(10000, totalChars * 250))
		except Exception as e:
			activityLog.writeException("ERROR", f"Error speaking language chunk '{self._activeLanguage}': {e}")
			self._processNextChunkOrFinish(self._synth)

	def _armWatchdog(self, chunkId, synth, timeoutMs):
		"""Advance the queue if a child synth never reports completion, so a silent or crashed
		synth can never leave Auto TTS mute. While speech is paused the deadline is postponed:
		a paused chunk is not a stuck chunk."""

		def _expired():
			if self._activeChunkId != chunkId or not self._isSpeaking:
				return
			if self._paused:
				self._armWatchdog(chunkId, synth, timeoutMs)
				return
			activityLog.write("DEBUG", f"Chunk #{chunkId} watchdog expired; advancing queue safely")
			self._finishActiveChunk(synth, chunkId)

		try:
			wx.CallLater(timeoutMs, _expired)
		except Exception:
			pass

	def _prewarmNextQueuedSynth(self):
		try:
			with self.speechQueue.mutex:
				if not self.speechQueue.queue:
					return
				nextLang = self.speechQueue.queue[0][0]
			nextConfig = sharedConfig.getLanguageConfig(nextLang)
			nextSynthName = nextConfig.synth or "espeak"
			currentSynthName = getattr(self._synth, "name", "")
			if nextSynthName == currentSynthName or nextSynthName in VIRTUAL_SYNTHS:
				return
			self._getSynth(nextLang)
		except Exception:
			pass

	def prewarm(self):
		"""Start what the enabled profiles need before it is first needed: every configured
		synthesizer and the shared-script language models. Otherwise the first switch to
		another voice waits mid-sentence for its engine to start. Engines start one per
		main-loop turn so NVDA stays responsive."""
		# Only the active instance prewarms, and its children must be terminated with it.
		self._everActive = True
		enabled = {code: cfg for code, cfg in sharedConfig.languages.items() if cfg.enabled}
		try:
			from . import sharedScriptLid
			sharedScriptLid.preload({languageDetection.get_base_language(code) for code in enabled})
		except Exception:
			pass
		defaultSynth = sharedConfig.getLanguageConfig(sharedConfig.defaultLang).synth
		pending = []
		for cfg in enabled.values():
			name = cfg.synth if cfg.synth and cfg.synth not in VIRTUAL_SYNTHS else defaultSynth
			name = name if name and name not in VIRTUAL_SYNTHS else "espeak"
			if name not in pending:
				pending.append(name)

		def startNext():
			while pending:
				name = pending.pop(0)
				if name in self._synthCache:
					continue
				try:
					self._getSynthByName(name)
				except Exception:
					pass
				try:
					wx.CallLater(200, startNext)
				except Exception:
					continue
				return

		startNext()

	def pumpSpeech(self):
		if self._isSpeaking:
			return

		self._isSpeaking = True
		self._processNextChunkOrFinish()

	def _rebindSettingsRing(self):
		"""Keeps the NVDA settings ring bound to AutoTTS when child synths are initialized."""
		if getattr(self, "_rebinding", False):
			return
		self._rebinding = True
		try:
			import globalVars
			ring = getattr(globalVars, "settingsRing", None)
			getSynth = getattr(synthDriverHandler, "getSynth", None)
			active = getSynth() if callable(getSynth) else getattr(synthDriverHandler, "synth", None)
			if ring is not None and active is self:
				ring.updateSupportedSettings(self)
			try:
				import speechDictHandler
				speechDictHandler.loadVoiceDict(self)
			except Exception:
				pass
		except Exception:
			pass
		finally:
			self._rebinding = False

	def _getSynthByName(self, synthName: str):
		if not synthName:
			synthName = "espeak"
		# Disallow virtual router synths to avoid recursion
		if synthName in VIRTUAL_SYNTHS or synthName == self.name:
			return None

		synth, defaultConf = self._synthCache.get(synthName, (None, {}))
		if synth is not None:
			return synth

		try:
			synth = _getSynthInstance(synthName)
		except Exception:
			return None

		for setting in getattr(synth, "supportedSettings", []):
			if not hasattr(synth, setting.id):
				setattr(synth, setting.id, getattr(setting, "defaultVal", None))
			val = getattr(synth, setting.id, None)
			defaultConf[setting.id] = val

		try:
			synth._unregisterConfigSaveAction()
		except Exception:
			pass
		synth.saveSettings = lambda: None

		self._synthCache[synthName] = (synth, defaultConf)
		self._rebindSettingsRing()
		return synth

	def _getChildSynthConfig(self, langConfig, synthName, synth):
		try:
			profileName = langConfig.profile
			profile = config.conf._getProfile(profileName)
			if "speech" in profile and synthName in profile["speech"]:
				conf = profile["speech"][synthName]
				try:
					conf.configspec = synth.getConfigSpec()
					profile.validate(config.conf.validator, section=conf)
				except Exception:
					pass
				return conf
		except Exception:
			pass
		try:
			if "speech" in config.conf and synthName in config.conf["speech"]:
				return config.conf["speech"][synthName]
		except Exception:
			pass
		return None

	def _saveUnderlyingSynthSetting(self, lang, synth, settingId, val):
		synthName = None
		defaultConf = None
		for cachedName, (cachedSynth, cachedDefaults) in self._synthCache.items():
			if cachedSynth is synth:
				synthName = cachedName
				defaultConf = cachedDefaults
				break
		if synthName is None:
			return
		if defaultConf is not None:
			defaultConf[settingId] = val
		langConfig = sharedConfig.languages.get(lang)
		if langConfig is None:
			return
		conf = self._getChildSynthConfig(langConfig, synthName, synth)
		if conf is not None:
			try:
				conf[settingId] = val
			except Exception:
				pass

	def _getSynth(self, lang: str):
		langConfig = sharedConfig.getLanguageConfig(lang)
		synthName = langConfig.synth
		if not synthName or synthName in VIRTUAL_SYNTHS:
			defLang = sharedConfig.defaultLang
			if defLang != lang:
				defCfg = sharedConfig.getLanguageConfig(defLang)
				synthName = defCfg.synth
			if not synthName or synthName in VIRTUAL_SYNTHS:
				synthName = "espeak"

		# Fast path: if the currently active synth is already prepared for this
		# exact language profile, skip config reads and property checks entirely.
		# This avoids touching the synth at all between consecutive same-language
		# chunks which is critical for ETI Eloquence 16kHz stability.
		if (
			self._activePreparedLang == lang
			and self._synth is not None
			and getattr(self._synth, "name", "") == synthName
		):
			return self._synth

		synth = self._getSynthByName(synthName)
		if synth is None:
			for fallbackName, displayName in synthDriverHandler.getSynthList():
				if fallbackName in (synthName, self.name, SilenceSynthDriver.name) or fallbackName in VIRTUAL_SYNTHS:
					continue
				synth = self._getSynthByName(fallbackName)
				if synth is not None:
					synthName = fallbackName
					break
			if synth is None:
				log.error(f"AutoTTS: No working synthesizer found for language '{lang}'.")
				return None

		_, defaultConf = self._synthCache.get(synthName, (synth, {}))
		conf = self._getChildSynthConfig(langConfig, synthName, synth)

		# 1. Apply Voice (with strict dirty-state checking)
		if synth.isSupported("voice"):
			storedVoice = langConfig.voice or (conf["voice"] if (conf is not None and "voice" in conf) else None)
			nativePreferred = defaultConf.get("voice")
			targetVoice = voiceMatch.usableVoice(synth, storedVoice, lang, preferred=nativePreferred)

			if targetVoice is not None and targetVoice in getattr(synth, "availableVoices", {}):
				if getattr(synth, "voice", None) != targetVoice:
					try:
						synth.voice = targetVoice
					except Exception:
						pass

		# 2. Apply Variant (with dirty-state checking)
		if synth.isSupported("variant"):
			targetVariant = getattr(langConfig, "variant", None) or defaultConf.get("variant")
			if targetVariant and targetVariant in getattr(synth, "availableVariants", {}):
				if getattr(synth, "variant", None) != targetVariant:
					try:
						synth.variant = targetVariant
					except Exception:
						pass

		# 3. Apply Prosody (Rate, Pitch, Volume) with strict dirty-state checking
		for setting in getattr(synth, "supportedSettings", []):
			if setting.id in ("voice", "variant"):
				continue

			val = conf[setting.id] if (conf is not None and setting.id in conf) else defaultConf.get(setting.id)

			if langConfig.useCustomProsody:
				if setting.id == "rate" and langConfig.customRate >= 0:
					val = langConfig.customRate
				elif setting.id == "pitch" and langConfig.customPitch >= 0:
					val = langConfig.customPitch
				elif setting.id == "volume" and langConfig.customVolume >= 0:
					val = langConfig.customVolume

			if not getattr(setting, "useConfig", True) or val is None:
				continue
			# Coerce config values (often stored as strings by configobj) to
			# match the native type of the synth property so the dirty-state
			# comparison below is reliable.  Without this, "80" != 80 in
			# Python 3 and every prosody property gets reassigned on every
			# speak() call, resetting ETI Eloquence's 16kHz audio buffer.
			currentVal = getattr(synth, setting.id, None)
			if currentVal is not None and type(val) is not type(currentVal):
				try:
					val = type(currentVal)(val)
				except (TypeError, ValueError):
					pass
			# DIRTY STATE CHECK: Never reassign property if value already matches!
			# This is the critical fix preventing ETI Eloquence 16kHz audio buffer resets.
			if currentVal == val:
				continue
			try:
				setattr(synth, setting.id, val)
			except Exception:
				pass

		return synth

	def speak(self, speechSequence):
		getSynth = getattr(synthDriverHandler, "getSynth", None)
		active = getSynth() if callable(getSynth) else getattr(synthDriverHandler, "synth", None)
		if active is self:
			self._everActive = True

		startedAt = time.perf_counter()
		try:
			self._speak(speechSequence)
		finally:
			_logIfSlow("speak", startedAt)

	def _getActiveKeyboardLanguage(self) -> Optional[str]:
		try:
			api_mod = globals().get("api")
			if not api_mod or not hasattr(api_mod, "getFocusObject"):
				return None
			import winUser
			focus = api_mod.getFocusObject()
			threadId = getattr(focus, "windowThreadID", 0) if focus else 0
			hkl = winUser.getKeyboardLayout(threadId)
			langId = hkl & 0xFFFF
			import locale
			loc = locale.windows_locale.get(langId)
			if loc:
				return loc.split("_")[0].lower()
		except Exception:
			pass
		return None

	def _speak(self, speechSequence):
		"""
		Processes incoming speech sequence, applies number preprocessing,
		segments multi-language text, merges consecutive chunks targeting the same synth & voice,
		and routes speech.
		"""
		try:
			# 1. Check Language Lock
			if sharedConfig.lockedLanguage:
				targetLang = sharedConfig.lockedLanguage
				baseLang = languageDetection.get_base_language(targetLang)
				langConfig = sharedConfig.getLanguageConfig(targetLang)
				cleanSeq = []
				for item in speechSequence:
					if not _isLangChangeCommand(item):
						cleanSeq.append(item)
				if langConfig.sendLang:
					cleanSeq.insert(0, LangChangeCommand(baseLang))
				self.speechQueue.put((targetLang, cleanSeq))
				self.pumpSpeech()
				return

			# 2. Check App-Specific Auto-Bypass
			if _isForegroundAppExcluded():
				targetLang = self._voice
				baseLang = languageDetection.get_base_language(targetLang)
				langConfig = sharedConfig.getLanguageConfig(targetLang)
				cleanSeq = []
				for item in speechSequence:
					if not _isLangChangeCommand(item):
						cleanSeq.append(item)
				if langConfig.sendLang:
					cleanSeq.insert(0, LangChangeCommand(baseLang))
				self.speechQueue.put((targetLang, cleanSeq))
				self.pumpSpeech()
				return

			# 3. Pre-process dates, mobile patterns & other numbers
			preprocessedSequence = []
			for item in speechSequence:
				if isinstance(item, str):
					text = numberProcessing.reserve_dates(item, getattr(sharedConfig, "dateMode", "default"))
					text = numberProcessing.reserve_mobile(text, sharedConfig.mobilePattern)
					otherMode = getattr(sharedConfig, "otherNumberMode", "default")
					if otherMode != "default":
						text = numberProcessing.rewrite_other_numbers(
							text,
							otherMode,
							crore_lakh=sharedConfig.croreLakhEnabled
						)
					else:
						text = numberProcessing.rewrite_long_numbers(
							text,
							sharedConfig.longNumberMode,
							sharedConfig.longNumberMinDigits,
							sharedConfig.croreLakhEnabled
						)
					preprocessedSequence.append(text)
				else:
					preprocessedSequence.append(item)

			# A text with no letters or digits anywhere (a line holding only ؟ or ؑ) is read by
			# symbol name; inside a sentence punctuation only shapes intonation.
			symbolOnlyUtterance = not any(
				isinstance(item, str) and languageDetection.has_content(item) for item in speechSequence
			)
			hasCharacterMode = any(isinstance(item, CharacterModeCommand) for item in speechSequence)

			# 4. Automatic Language Detection & Segmentation
			if sharedConfig.useUnicodeLanguageDetection and sharedConfig.enabled:
				if self._nvdaWords is None:
					self._nvdaWords = _nvdaVocabulary()
				statisticalLanguages = {}
				for configuredTag, configuredProfile in sharedConfig.languages.items():
					if not configuredProfile.enabled:
						continue
					base = languageDetection.get_base_language(configuredTag)
					if base not in statisticalLanguages or configuredTag == base:
						statisticalLanguages[base] = configuredTag
				preprocessedSequence = list(languageDetection.addDetectedLanguageCommands(
					preprocessedSequence,
					defaultLang=self._voice,
					scriptSettings=sharedConfig.scriptMapping,
					smartUrduArabic=sharedConfig.smartUrduArabic,
					numberMode=sharedConfig.numberMode,
					granularityMode=sharedConfig.granularityMode,
					protectMathSymbols=sharedConfig.protectMathSymbols,
					mathLanguage=sharedConfig.mathLanguage,
					tagMode=sharedConfig.tagMode,
					useStatisticalDetection=sharedConfig.useStatisticalLanguageDetection,
					statisticalLanguages=statisticalLanguages,
					currentLang=self._activePreparedLang,
					activeKeyboardLang=self._getActiveKeyboardLanguage() if hasCharacterMode else None,
					protectedTexts=self._nvdaWords,
				))

			# 5. Expand reserved dates & mobile numbers, rewrite crore/lakh per-run
			expandedSequence = []
			curRunLang = self._voice
			charModeActive = False
			for item in preprocessedSequence:
				if isinstance(item, CharacterModeCommand):
					charModeActive = getattr(item, "state", True)
					expandedSequence.append(item)
				elif _isLangChangeCommand(item):
					curRunLang = item.lang or self._voice
					expandedSequence.append(item)
				elif isinstance(item, str):
					runText = numberProcessing.expand_reserved_dates(
						item, getattr(sharedConfig, "dateMode", "default"), lang=curRunLang
					)
					runText = numberProcessing.expand_reserved_mobile(runText, sharedConfig.mobilePattern)
					if sharedConfig.croreLakhEnabled:
						base = languageDetection.get_base_language(curRunLang)
						if base == "en":
							runText = numberProcessing.rewrite_crore_lakh(runText, True)
						else:
							runText = numberProcessing.rewrite_deferred_long_numbers(
								runText, sharedConfig.longNumberMode, sharedConfig.longNumberMinDigits
							)
					spoken = languageDetection.expand_honorifics(runText, curRunLang)
					if spoken == runText and (symbolOnlyUtterance or charModeActive):
						spoken = languageDetection.expand_spoken_symbols(runText, curRunLang)
					if charModeActive and spoken != runText:
						# A name read in character mode would be spelled letter by letter.
						expandedSequence.extend((CharacterModeCommand(False), spoken, CharacterModeCommand(True)))
						continue
					expandedSequence.append(spoken)
				else:
					expandedSequence.append(item)

			# 6. Consecutive Chunk Merging & Route Signatures
			lang = self._voice
			langConfig = sharedConfig.getLanguageConfig(lang)
			newSpeechSequence = []
			hasText = False
			stateCommands = OrderedDict()

			def _resolvedSynthAndVoice(cfg):
				sName = cfg.synth
				if not sName or sName in VIRTUAL_SYNTHS:
					defCfg = sharedConfig.getLanguageConfig(sharedConfig.defaultLang or self._voice)
					sName = defCfg.synth or "espeak"
				if sName in VIRTUAL_SYNTHS:
					sName = "espeak"
				sVoice = cfg.voice or ""
				return sName.lower(), sVoice.lower()

			def routeSignature(cfg):
				sName, sVoice = _resolvedSynthAndVoice(cfg)
				return (
					sName,
					sVoice,
					cfg.useCustomProsody,
					cfg.customRate if cfg.useCustomProsody else -1,
					cfg.customPitch if cfg.useCustomProsody else -1,
					cfg.customVolume if cfg.useCustomProsody else -1,
				)

			def rememberStateCommand(command):
				if command.__class__.__name__ in {
					"CharacterModeCommand", "PitchCommand", "RateCommand", "VolumeCommand"
				}:
					stateCommands[command.__class__] = command

			for item in expandedSequence:
				if isinstance(item, str):
					if item.isspace():
						newSpeechSequence.append(item)
						continue
					if langConfig.sendLang and not hasText:
						baseLang = languageDetection.get_base_language(lang)
						newSpeechSequence.append(LangChangeCommand(baseLang))
					newSpeechSequence.append(item)
					hasText = True

				elif _isLangChangeCommand(item):
					rawLang = item.lang
					if rawLang is None:
						newLang = self._voice
						normFull, baseLang = languageDetection.normalize_language_code(newLang)
					else:
						normFull, baseLang = languageDetection.normalize_language_code(rawLang)
						newLang = sharedConfig.resolveLanguageCode(normFull)

					if newLang == lang:
						continue

					newLangConfig = sharedConfig.getLanguageConfig(newLang)
					if not newLangConfig.enabled:
						newLang = self._voice
						newLangConfig = sharedConfig.getLanguageConfig(newLang)
						baseLang = languageDetection.get_base_language(newLang)

					# CONSECUTIVE CHUNK MERGING:
					# If new language routes to the same underlying synthesizer, voice, and prosody,
					# merge directly into newSpeechSequence without splitting into separate speak() calls!
					if routeSignature(newLangConfig) == routeSignature(langConfig):
						if newLangConfig.sendLang:
							newSpeechSequence.append(LangChangeCommand(baseLang))
					elif hasText:
						if activityLog.isEnabled():
							activityLog.write(
								"QUEUE",
								f"Split chunk: {lang} ({_resolvedSynthAndVoice(langConfig)}) -> "
								f"{newLang} ({_resolvedSynthAndVoice(newLangConfig)})"
							)
						self.speechQueue.put((lang, newSpeechSequence))
						newSpeechSequence = list(stateCommands.values())
						hasText = False

					lang = newLang
					langConfig = newLangConfig

				else:
					newSpeechSequence.append(item)
					rememberStateCommand(item)

			if newSpeechSequence:
				self.speechQueue.put((lang, newSpeechSequence))
			self.pumpSpeech()
		except Exception as e:
			activityLog.writeException("ERROR", f"Error in speak pipeline: {e}")

	def pause(self, switch):
		self._paused = bool(switch)
		if self._synth is not None:
			try:
				self._synth.pause(switch)
			except Exception:
				pass

	def cancel(self):
		"""Instantly and synchronously cancels speech across active child synths."""
		try:
			while True:
				self.speechQueue.get_nowait()
		except queue.Empty:
			pass

		self._isSpeaking = False
		self._paused = False
		self._activeLanguage = self._voice
		self._activeChunkId += 1
		self._activeMarker = None
		self._doneSpeakingReceived = False
		self._activeForwardIndices.clear()

		startedAt = time.perf_counter()
		used = self._usedSynths
		self._usedSynths = []
		active = self._synth
		if active is not None and not any(item is active for item in used):
			used.append(active)
		for childSynth in used:
			try:
				childSynth.cancel()
			except Exception:
				pass

		if self._synth is not None:
			self._synth = None
			self._activePreparedLang = None

		_logIfSlow("cancel", startedAt, f"({len(used)} synths)")

	def _getAvailableVoices(self):
		"""Return only Auto TTS profiles as languages in NVDA's settings ring."""
		profileLangs = sorted(sharedConfig.languages.keys())
		if not profileLangs:
			profileLangs = [getattr(self, "_voice", None) or sharedConfig.defaultLang or "en"]
		voices = OrderedDict()
		for code in profileLangs:
			try:
				desc = languageHandler.getLanguageDescription(code) or code
			except Exception:
				desc = code
			# NVDA looks up symbol names and character descriptions by this language,
			# so it must be in NVDA's locale form (pa_PK), not a hyphenated tag.
			voices[code] = VoiceInfo(code, f"{desc} ({code})", languageDetection.to_nvda_locale(code))
		return voices

	def _get_availableVoices(self):
		return self._getAvailableVoices()

	def _get_availableLanguagelocks(self):
		"""Choices for the language lock setting: automatic switching, then each enabled profile."""
		# Translators: The language lock choice that keeps automatic language switching.
		locks = OrderedDict([("", StringParameterInfo("", _("Off, switch automatically")))])
		for code, info in self._getAvailableVoices().items():
			profile = sharedConfig.languages.get(code)
			if profile is not None and profile.enabled:
				locks[code] = StringParameterInfo(code, info.displayName)
		return locks

	def _get_languageLock(self):
		return sharedConfig.lockedLanguage or ""

	def _set_languageLock(self, value):
		profile = sharedConfig.languages.get(value) if value else None
		sharedConfig.lockedLanguage = value if profile is not None and profile.enabled else None

	def _get_voice(self):
		return self._voice

	def _get_language(self):
		# NVDA asks for this on every utterance; answer without rebuilding the voice list.
		return languageDetection.to_nvda_locale(self._voice or sharedConfig.defaultLang or "en")

	def _set_voice(self, voice):
		if voice in self.availableVoices:
			changed = voice != getattr(self, "_voice", None)
			self._voice = voice
			sharedConfig.defaultLang = voice
			if changed:
				self._activePreparedLang = None
				sharedConfig.scheduleSave()
