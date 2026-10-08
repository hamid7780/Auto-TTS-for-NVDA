# Auto TTS for NVDA - Core Synthesizer Driver
# Covered by GNU General Public License (GPL)

import queue
import importlib
import itertools
import time
from collections import OrderedDict
from typing import Dict, Any

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
	from synthDriverHandler import VoiceInfo, synthDoneSpeaking, synthIndexReached
	from synthDrivers.espeak import SynthDriver as EspeakSynthDriver
	from synthDrivers.silence import SynthDriver as SilenceSynthDriver
	from speech.commands import (
		IndexCommand,
		CharacterModeCommand,
		PitchCommand,
		LangChangeCommand,
	)
	from logHandler import log
	addonHandler.initTranslation()
except ImportError:
	class EspeakSynthDriver: name = "espeak"
	class SilenceSynthDriver: name = "silence"
	class VoiceInfo:
		def __init__(self, id, displayName, language=None):
			self.id = id; self.displayName = displayName; self.language = language
	class DriverSetting:
		def __init__(self, id="voice", name="", minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True):
			self.id = id; self.name = name; self.minStep = minStep; self.minVal = minVal; self.maxVal = maxVal; self.availableInSettingsRing = availableInSettingsRing
	class NumericDriverSetting(DriverSetting):
		def __init__(self, id, name, minStep=1, minVal=0, maxVal=100, availableInSettingsRing=True):
			super().__init__(id, name, minStep=minStep, minVal=minVal, maxVal=maxVal, availableInSettingsRing=availableInSettingsRing)
	class BooleanDriverSetting(DriverSetting):
		def __init__(self, id, name, availableInSettingsRing=True):
			super().__init__(id, name, availableInSettingsRing=availableInSettingsRing)
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
	class IndexCommand:
		def __init__(self, index=0): self.index = index
	class CharacterModeCommand: pass
	class PitchCommand: pass
	class LangChangeCommand:
		def __init__(self, lang): self.lang = lang
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
from .configManager import sharedConfig


def _getSynthInstance(name: str):
	"""Imports and instantiates an underlying NVDA synth driver by name."""
	if not name:
		name = "espeak"
	return importlib.import_module(f"synthDrivers.{name}", package="synthDrivers").SynthDriver()


def _isForegroundAppExcluded() -> bool:
	"""Checks if currently focused application is in user's exclusion list."""
	try:
		obj = api.getFocusObject()
		if obj and hasattr(obj, "appModule"):
			appName = getattr(obj.appModule, "appName", "")
			if appName:
				if sharedConfig.isAppExcluded(f"{appName}.exe") or sharedConfig.isAppExcluded(appName):
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
	return tuple(settings)


# Calls slower than this are written to the NVDA log at debug level so that a
# report of "speech starts late" can be traced to the step that is responsible.
_SLOW_CALL_MS = 3.0


def _logIfSlow(what, startedAt, detail=""):
	elapsed = (time.perf_counter() - startedAt) * 1000.0
	if elapsed >= _SLOW_CALL_MS:
		try:
			log.debug(f"AutoTTS: {what} took {elapsed:.1f} ms {detail}".rstrip())
		except Exception:
			pass


class SynthDriver(synthDriverHandler.SynthDriver):
	name = "autoTTS"
	description = _("Auto TTS for NVDA")

	supportedSettings = _buildSupportedSettings()

	def __init__(self):
		self._synthCache: Dict[str, Any] = {}
		# Child synths that have been given speech since the last cancel. Only these
		# can still be making sound, so cancel() does not have to stop idle ones.
		self._usedSynths = []
		self._synth = None
		self._isSpeaking = False
		self.speechQueue = queue.Queue()
		self._markerCounter = itertools.count(1_500_000_000)
		self._activeMarker = None
		self._activeChunkId = 0
		self._activeForwardIndices = set()

		# Initialize default language
		try:
			systemLang = languageHandler.getLanguage().split("_")[0]
		except Exception:
			systemLang = "en"

		self._voice = sharedConfig.defaultLang or systemLang
		if self._voice not in self.availableVoices:
			normVoice = languageDetection.get_base_language(self._voice)
			self._voice = normVoice if normVoice in self.availableVoices else next(iter(self.availableVoices), "en")

		synthDoneSpeaking.register(self._onSynthDoneSpeaking)
		synthIndexReached.register(self._onSynthIndexReached)

	def terminate(self):
		self.cancel()
		synthIndexReached.unregister(self._onSynthIndexReached)
		synthDoneSpeaking.unregister(self._onSynthDoneSpeaking)

		self._synth = None
		self._isSpeaking = False

		for synth, defaultConf in list(self._synthCache.values()):
			try:
				synth.cancel()
				synth.terminate()
			except Exception:
				pass
		self._synthCache.clear()

	def saveSettings(self):
		"""Saves AutoTTS settings to NVDA config."""
		sharedConfig.defaultLang = self._voice
		sharedConfig.save()

	def loadSettings(self, onlyChanged=False):
		"""Loads AutoTTS settings from NVDA config."""
		sharedConfig.load()
		try:
			systemLang = languageHandler.getLanguage().split("_")[0]
		except Exception:
			systemLang = "en"
		self._voice = sharedConfig.defaultLang or systemLang
		if self._voice not in self.availableVoices:
			normVoice = languageDetection.get_base_language(self._voice)
			self._voice = normVoice if normVoice in self.availableVoices else next(iter(self.availableVoices), "en")

		# SynthDriver.initSettings delegates to this override whenever an NVDA
		# config section already exists. The base implementation normally calls
		# changeVoice, which is also what creates/refreshes NVDA's settings ring.
		# Without this call globalVars.settingsRing remains None and every
		# NVDA+Ctrl+arrow settings-ring command fails silently for the user.
		synthDriverHandler.changeVoice(self, self._voice)

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
		"""Auto TTS can route every language tag through a profile or fallback.

		NVDA's base implementation compares language tags only against the voice
		IDs exposed in ``availableVoices``. Our voice list intentionally contains
		only configured profiles, so a base profile such as ``en`` would otherwise
		make inherited tags such as ``en-US`` appear unsupported. Unconfigured
		tags are still safe: ``_getSynth`` routes them through the configured
		default synth or the eSpeak fallback.
		"""
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
		"""Return the child synth configured for the ring's selected profile."""
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
		langConfig = sharedConfig.languages[settingsLang]
		if langConfig.useCustomProsody:
			# Custom values belong solely to this Auto TTS language profile.
			# Do not write them into the child synth's NVDA configuration.
			setattr(langConfig, customAttribute, val)
			sharedConfig.setLanguageConfig(langConfig)
			return

		# With custom prosody disabled, this is an ordinary child-synth setting.
		synth = self._getSettingsSynth(settingsLang)
		if synth is None or not hasattr(synth, settingId):
			return
		try:
			setattr(synth, settingId, val)
		except Exception:
			return
		self._saveUnderlyingSynthSetting(settingsLang, synth, settingId, val)

	def _get_rate(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customRate >= 0:
				return defCfg.customRate
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "rate", 50) if synth else 50

	def _set_rate(self, val):
		self._setProsodySetting("rate", "customRate", val, 50)

	def _get_pitch(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customPitch >= 0:
				return defCfg.customPitch
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "pitch", 50) if synth else 50

	def _set_pitch(self, val):
		self._setProsodySetting("pitch", "customPitch", val, 50)

	def _get_volume(self):
		settingsLang = self._getSettingsLanguage()
		if settingsLang:
			defCfg = sharedConfig.languages[settingsLang]
			if defCfg.useCustomProsody and defCfg.customVolume >= 0:
				return defCfg.customVolume
		synth = self._getSettingsSynth(settingsLang)
		return getattr(synth, "volume", 100) if synth else 100

	def _set_volume(self, val):
		self._setProsodySetting("volume", "customVolume", val, 100)

	def _onSynthDoneSpeaking(self, synth):
		"""Handle completion for children which do not use our private end marker.

		Most NVDA synths use an injected IndexCommand to prevent stale completion
		events from advancing the queue. Google TTS handles its own asynchronous queue
		and completion correctly, but does not reliably return an injected trailing
		marker when nested under Auto TTS, so it deliberately uses ``done`` instead.
		"""
		if synth is self or synth is not self._synth or not self._isSpeaking:
			return
		if self._activeMarker is not None:
			return
		chunkId = self._activeChunkId
		self._scheduleChunkFinished(synth, chunkId)

	def _usesPrivateEndMarker(self, synth):
		"""Whether this child can reliably return Auto TTS's trailing marker."""
		try:
			if IndexCommand not in getattr(synth, "supportedCommands", set()):
				return False
			identity = "{} {}".format(
				getattr(synth, "name", ""),
				getattr(type(synth), "__module__", ""),
			).lower()
			return "googlettsfornvda" not in identity
		except Exception:
			return False

	def _scheduleChunkFinished(self, synth, chunkId):
		try:
			if wx.IsMainThread():
				self._finishActiveChunk(synth, chunkId)
			else:
				wx.CallAfter(self._finishActiveChunk, synth, chunkId)
		except Exception:
			self._finishActiveChunk(synth, chunkId)

	def _finishActiveChunk(self, synth, chunkId):
		if not self._isSpeaking or synth is not self._synth or chunkId != self._activeChunkId:
			return
		self._activeMarker = None
		self._activeForwardIndices.clear()
		self._processNextChunkOrFinish(synth)

	def _processNextChunkOrFinish(self, synth=None):
		try:
			lang, speechSequence = self.speechQueue.get_nowait()
			self._startChunk(lang, speechSequence)
		except queue.Empty:
			self._isSpeaking = False
			self._activeLanguage = self._voice
			self._activeMarker = None
			self._activeForwardIndices.clear()
			synthDoneSpeaking.notify(synth=self)

	def _onSynthIndexReached(self, synth, index):
		if synth is self or synth is not self._synth or not self._isSpeaking:
			return
		if index == self._activeMarker:
			# The private marker proves that this is the active utterance, but an index
			# can be reported while the final audio is still buffered. Wait for the
			# child's subsequent done event before starting a different synth, otherwise
			# the end of an English name can overlap the beginning of an Urdu sentence.
			self._activeMarker = None
		elif index in self._activeForwardIndices:
			synthIndexReached.notify(synth=self, index=index)

	def _markSynthUsed(self, synth):
		"""Remember that a child synth may be producing audio until the next cancel."""
		if synth is not None and not any(used is synth for used in self._usedSynths):
			self._usedSynths.append(synth)

	def _startChunk(self, lang, speechSequence):
		self._activeLanguage = lang
		startedAt = time.perf_counter()
		self._synth = self._getSynth(lang)
		_logIfSlow("preparing the voice", startedAt, f"(language {lang})")
		self._markSynthUsed(self._synth)
		if self._synth is None:
			# Skip a broken language route instead of leaving the complete queue stuck.
			self._processNextChunkOrFinish()
			return

		sequence = list(speechSequence)
		self._activeForwardIndices = {
			item.index for item in sequence if isinstance(item, IndexCommand) and hasattr(item, "index")
		}
		self._activeChunkId += 1
		self._activeMarker = None

		try:
			if self._usesPrivateEndMarker(self._synth):
				marker = next(self._markerCounter)
				while marker in self._activeForwardIndices:
					marker = next(self._markerCounter)
				self._activeMarker = marker
				insertAt = len(sequence)
				while insertAt > 0 and sequence[insertAt - 1].__class__.__name__ == "EndUtteranceCommand":
					insertAt -= 1
				sequence.insert(insertAt, IndexCommand(marker))
			self._synth.speak(sequence)
			# Creating Chromium/WASM based synths only after the previous language has
			# finished introduces a multi-second silent gap. The next chunk is already
			# known, so initialize/apply its voice while the current audio is playing.
			self._prewarmNextQueuedSynth()
		except Exception as e:
			try:
				log.error(f"AutoTTS: Error speaking language chunk '{self._activeLanguage}': {e}")
			except Exception:
				pass
			self._processNextChunkOrFinish(self._synth)

	def _prewarmNextQueuedSynth(self):
		"""Prepare (but never speak) the next queued language synth in advance."""
		try:
			with self.speechQueue.mutex:
				if not self.speechQueue.queue:
					return
				nextLang = self.speechQueue.queue[0][0]
			nextConfig = sharedConfig.getLanguageConfig(nextLang)
			nextSynthName = nextConfig.synth or "espeak"
			currentSynthName = getattr(self._synth, "name", "")
			# Changing voice/prosody on the same child while it is still speaking can
			# affect its active utterance. Same-synth transitions need no construction
			# warmup anyway, so leave them until the normal chunk boundary.
			if nextSynthName == currentSynthName:
				return
			self._getSynth(nextLang)
		except Exception:
			# Prewarming is only a latency optimization; speech must remain functional
			# even when an optional child synthesizer cannot initialize early.
			pass

	def _prewarmConfiguredHighLatencySynths(self):
		"""Start known asynchronous child runtimes shortly after NVDA startup."""
		seen = set()
		for langConfig in sharedConfig.languages.values():
			synthName = langConfig.synth
			if not synthName or synthName in seen:
				continue
			seen.add(synthName)
			if "googlettsfornvda" not in synthName.lower():
				continue
			try:
				self._getSynthByName(synthName)
			except Exception:
				pass

	def pumpSpeech(self):
		"""Pumps speech from the queue only if not already speaking."""
		if self._isSpeaking:
			return

		try:
			lang, speechSequence = self.speechQueue.get_nowait()
		except queue.Empty:
			self._isSpeaking = False
			self._activeLanguage = self._voice
			return

		try:
			self._isSpeaking = True
			self._startChunk(lang, speechSequence)
		except Exception as e:
			try:
				log.error(f"AutoTTS: Error during synth speech execution for language '{lang}': {e}")
			except Exception:
				pass
			self._isSpeaking = False
			synthDoneSpeaking.notify(synth=self)

	def _getSynthByName(self, synthName: str):
		if not synthName:
			synthName = "espeak"
		# Imported profiles may accidentally point back to this routing driver.
		# Reject that route so normal fallback can run without recursive drivers.
		if synthName == self.name:
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
		return synth

	def _getChildSynthConfig(self, langConfig, synthName, synth):
		"""Return the NVDA synth config section used by a language profile."""
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
		"""Persist a non-custom ring value in the selected child synth config."""
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
		if not synthName:
			defLang = sharedConfig.defaultLang
			if defLang != lang:
				defCfg = sharedConfig.getLanguageConfig(defLang)
				synthName = defCfg.synth
			if not synthName:
				synthName = "espeak"

		synth = self._getSynthByName(synthName)
		if synth is None:
			for fallbackName, displayName in synthDriverHandler.getSynthList():
				if fallbackName in (synthName, self.name, SilenceSynthDriver.name):
					continue
				synth = self._getSynthByName(fallbackName)
				if synth is not None:
					synthName = fallbackName
					break
			if synth is None:
				log.error(f"AutoTTS: No working synthesizer found for language '{lang}'.")
				return None

		_, defaultConf = self._synthCache.get(synthName, (synth, {}))

		lastLangKey = f"_autoTTS_lastLang_{synthName}"
		lastAppliedLang = getattr(self, lastLangKey, None)
		forceApply = (lastAppliedLang != lang)
		setattr(self, lastLangKey, lang)

		conf = self._getChildSynthConfig(langConfig, synthName, synth)

		# 1. Apply Voice
		if synth.isSupported("voice"):
			if langConfig.voice:
				targetVoice = langConfig.voice
			elif conf is not None and "voice" in conf:
				targetVoice = conf["voice"]
			else:
				targetVoice = defaultConf.get("voice")

			if targetVoice is not None and targetVoice in getattr(synth, "availableVoices", {}):
				if forceApply or targetVoice != getattr(synth, "voice", None):
					try:
						synth.voice = targetVoice
					except Exception:
						pass

		# 2. Apply Prosody (Rate, Pitch, Volume)
		for setting in getattr(synth, "supportedSettings", []):
			if setting.id == "voice":
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
			if not forceApply and getattr(synth, setting.id, None) == val:
				continue
			try:
				setattr(synth, setting.id, val)
			except Exception:
				pass

		return synth

	def speak(self, speechSequence):
		startedAt = time.perf_counter()
		try:
			self._speak(speechSequence)
		finally:
			_logIfSlow("speak", startedAt)

	def _speak(self, speechSequence):
		"""
		Processes incoming speech sequence, checks language lock and application bypass,
		segments multi-language text, and routes chunks to synthesizers.
		"""
		try:
			# 1. Check Language Lock
			if sharedConfig.lockedLanguage:
				targetLang = sharedConfig.lockedLanguage
				baseLang = languageDetection.get_base_language(targetLang)
				langConfig = sharedConfig.getLanguageConfig(targetLang)
				# Strip any conflicting LangChangeCommands
				cleanSeq = []
				for item in speechSequence:
					if not isinstance(item, LangChangeCommand):
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
					if not isinstance(item, LangChangeCommand):
						cleanSeq.append(item)
				if langConfig.sendLang:
					cleanSeq.insert(0, LangChangeCommand(baseLang))
				self.speechQueue.put((targetLang, cleanSeq))
				self.pumpSpeech()
				return

			# 3. Automatic Language Detection & Segmentation
			if sharedConfig.useUnicodeLanguageDetection and sharedConfig.enabled:
				statisticalLanguages = {}
				for configuredTag, configuredProfile in sharedConfig.languages.items():
					if not configuredProfile.enabled:
						continue
					base = languageDetection.get_base_language(configuredTag)
					# Prefer an exact base profile when both a base and regional
					# variant exist; fastText identifies languages, not dialects.
					if base not in statisticalLanguages or configuredTag == base:
						statisticalLanguages[base] = configuredTag
				speechSequence = list(languageDetection.addDetectedLanguageCommands(
					speechSequence,
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
				))

			lang = self._voice
			langConfig = sharedConfig.getLanguageConfig(lang)
			newSpeechSequence = []
			hasText = False
			# Only these commands represent state which must be restored when a
			# language boundary genuinely requires another synth/voice invocation.
			stateCommands = OrderedDict()

			def routeSignature(cfg):
				synthName = cfg.synth
				if not synthName:
					defCfg = sharedConfig.getLanguageConfig(sharedConfig.defaultLang or self._voice)
					synthName = defCfg.synth or "espeak"
				return (
					synthName,
					cfg.voice,
					cfg.sendLang,
					cfg.profile,
					cfg.useCustomProsody,
					cfg.customRate,
					cfg.customPitch,
					cfg.customVolume,
				)

			def rememberStateCommand(command):
				if command.__class__.__name__ in {
					"CharacterModeCommand", "PitchCommand", "RateCommand", "VolumeCommand"
				}:
					stateCommands[command.__class__] = command

			for item in speechSequence:
				if isinstance(item, str):
					if item.isspace():
						newSpeechSequence.append(item)
						continue
					if langConfig.sendLang and not hasText:
						baseLang = languageDetection.get_base_language(lang)
						newSpeechSequence.append(LangChangeCommand(baseLang))
					newSpeechSequence.append(item)
					hasText = True

				elif isinstance(item, LangChangeCommand):
					rawLang = item.lang
					if rawLang is None:
						newLang = self._voice
						normFull, baseLang = languageDetection.normalize_language_code(newLang)
					else:
						normFull, baseLang = languageDetection.normalize_language_code(rawLang)
						# Resolve base detector output to an existing regional profile too,
						# e.g. ``ur`` -> the user's configured ``ur-pk`` Google voice.
						newLang = sharedConfig.resolveLanguageCode(normFull)

					if newLang == lang:
						continue

					newLangConfig = sharedConfig.getLanguageConfig(newLang)
					if not newLangConfig.enabled:
						newLang = self._voice
						newLangConfig = sharedConfig.getLanguageConfig(newLang)
						baseLang = languageDetection.get_base_language(newLang)

					if routeSignature(newLangConfig) == routeSignature(langConfig):
						if newLangConfig.sendLang:
							newSpeechSequence.append(LangChangeCommand(baseLang))
					elif hasText:
						self.speechQueue.put((lang, newSpeechSequence))
						# Replay only persistent speech state.  Indexes, breaks, beeps and
						# end-utterance commands must never migrate to another chunk.
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
			try:
				log.error(f"AutoTTS: Error in speak pipeline: {e}")
			except Exception:
				pass

	def pause(self, switch):
		if self._synth is not None:
			try:
				self._synth.pause(switch)
			except Exception:
				pass

	def cancel(self):
		"""Instantly and synchronously cancels all active speech across all cached synths."""
		try:
			while True:
				self.speechQueue.get_nowait()
		except queue.Empty:
			pass

		self._isSpeaking = False
		self._activeLanguage = self._voice
		self._activeChunkId += 1
		self._activeMarker = None
		self._activeForwardIndices.clear()

		# Stopping an audio device costs time on every key press, so only the child
		# synths which were actually given speech since the last cancel are stopped.
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

		self._synth = None
		_logIfSlow("cancel", startedAt, f"({len(used)} synths)")

	def _getAvailableVoices(self):
		"""Return only Auto TTS profiles as languages in NVDA's settings ring."""
		profileLangs = sorted(sharedConfig.languages.keys())
		# NVDA requires the current synth voice to exist in availableVoices even
		# before any profile is configured. This single fallback also keeps the
		# eSpeak route available; it disappears once the first profile exists.
		if not profileLangs:
			profileLangs = [getattr(self, "_voice", None) or sharedConfig.defaultLang or "en"]
		voices = OrderedDict()
		for code in profileLangs:
			try:
				desc = languageHandler.getLanguageDescription(code) or code
			except Exception:
				desc = code
			voices[code] = VoiceInfo(code, f"{desc} ({code})", code)
		return voices

	def _get_availableVoices(self):
		# Profiles can be added, renamed or removed while the synth is active.
		return self._getAvailableVoices()

	def _get_voice(self):
		return self._voice

	def _get_language(self):
		"""Always return a valid language, including the zero-profile fallback."""
		voiceInfo = self.availableVoices.get(self._voice)
		if voiceInfo is not None and getattr(voiceInfo, "language", None):
			return voiceInfo.language
		return languageDetection.get_base_language(self._voice or sharedConfig.defaultLang or "en")

	def _set_voice(self, voice):
		if voice in self.availableVoices:
			changed = voice != getattr(self, "_voice", None)
			self._voice = voice
			sharedConfig.defaultLang = voice
			if changed:
				sharedConfig.save()
