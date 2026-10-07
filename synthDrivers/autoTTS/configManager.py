# Auto TTS for NVDA - Configuration Manager
# Covered by GNU General Public License (GPL)

import json
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from .languageDetection import DEFAULT_SCRIPT_MAPPINGS, normalize_language_code

try:
	import config
	import globalVars
	from logHandler import log
except ImportError:
	class _MockConf(dict):
		def __contains__(self, key): return False
		def __getitem__(self, key): return {}
		def __setitem__(self, key, value): pass
	class config:
		conf = _MockConf()
	class globalVars:
		class appArgs:
			configPath = ""
	class log:
		@staticmethod
		def error(msg): pass
		@staticmethod
		def exception(msg): pass
		@staticmethod
		def debug(msg): pass


DEFAULT_EXCLUDED_APPS = [
	"code.exe",
	"cmd.exe",
	"powershell.exe",
	"windowsterminal.exe",
	"devenv.exe",
	"notepad++.exe",
]


def _getSettingsFilePath() -> str:
	"""Return %appdata%/nvda/addons/autoTTS.json."""
	try:
		configDir = globalVars.appArgs.configPath
		if configDir:
			settingsDir = os.path.join(configDir, "addons")
			if not os.path.isdir(settingsDir):
				os.makedirs(settingsDir, exist_ok=True)
			return os.path.join(settingsDir, "autoTTS.json")
	except Exception:
		pass
	return os.path.join(os.path.expanduser("~"), "autoTTS.json")


@dataclass
class LanguageVoiceConfig:
	"""Configuration for a single language-to-TTS mapping."""
	lang: str
	synth: str = ""           # Empty means use NVDA's active/default synth
	voice: Optional[str] = None
	sendLang: bool = True
	enabled: bool = True
	profile: Optional[str] = None  # NVDA configuration profile name for rate/pitch/vol
	useCustomProsody: bool = False
	customRate: int = -1       # -1 = use TTS/profile saved value
	customPitch: int = -1
	customVolume: int = -1

	def toDict(self) -> Dict[str, Any]:
		return {
			"synth": self.synth,
			"voice": self.voice or "",
			"sendLang": self.sendLang,
			"enabled": self.enabled,
			"profile": self.profile or "",
			"useCustomProsody": self.useCustomProsody,
			"customRate": self.customRate,
			"customPitch": self.customPitch,
			"customVolume": self.customVolume,
		}

	@classmethod
	def fromDict(cls, lang: str, d: Dict[str, Any]) -> "LanguageVoiceConfig":
		return cls(
			lang=lang,
			synth=str(d.get("synth", "")),
			voice=str(d.get("voice", "")) or None,
			sendLang=bool(d.get("sendLang", True)),
			enabled=bool(d.get("enabled", True)),
			profile=str(d.get("profile", "")) or None,
			useCustomProsody=bool(d.get("useCustomProsody", False)),
			customRate=int(d.get("customRate", -1)),
			customPitch=int(d.get("customPitch", -1)),
			customVolume=int(d.get("customVolume", -1)),
		)


class AutoTTSConfig:
	"""
	Central configuration manager for Auto TTS.
	Stored in %appdata%/nvda/addons/autoTTS.json.
	"""

	def __init__(self):
		self.languages: Dict[str, LanguageVoiceConfig] = {}
		self.enabled: bool = True
		# Empty means follow NVDA/Windows language until the user selects a profile.
		self.defaultLang: str = ""
		self.smartUrduArabic: bool = True
		self.numberMode: str = "current"
		self.useUnicodeLanguageDetection: bool = True
		self.useStatisticalLanguageDetection: bool = True
		self.granularityMode: str = "word"  # "word", "sentence", "line"
		self.protectMathSymbols: bool = True
		self.mathLanguage: str = "current"
		self.tagMode: str = "override"
		self.excludedApps: List[str] = list(DEFAULT_EXCLUDED_APPS)
		self.lockedLanguage: Optional[str] = None
		self.firstRun: bool = True
		self._emptyProfilesIntentional: bool = False
		self.scriptMapping: Dict[str, str] = dict(DEFAULT_SCRIPT_MAPPINGS)
		self.load()

	def _toFullDict(self) -> Dict[str, Any]:
		"""Serializes entire config to a plain dict for JSON storage."""
		return {
			"enabled": self.enabled,
			"defaultLang": self.defaultLang,
			"smartUrduArabic": self.smartUrduArabic,
			"numberMode": self.numberMode,
			"useUnicodeLanguageDetection": self.useUnicodeLanguageDetection,
			"useStatisticalLanguageDetection": self.useStatisticalLanguageDetection,
			"granularityMode": self.granularityMode,
			"protectMathSymbols": self.protectMathSymbols,
			"mathLanguage": self.mathLanguage,
			"tagMode": self.tagMode,
			"excludedApps": list(self.excludedApps),
			# Language lock is intentionally session-only. Persisting it caused an old
			# backup to reactivate a lock after an add-on update or NVDA restart.
			"lockedLanguage": None,
			"firstRun": self.firstRun,
			"emptyProfilesIntentional": self._emptyProfilesIntentional and not self.languages,
			"languages": {
				langCode: langCfg.toDict()
				for langCode, langCfg in self.languages.items()
			},
			"scriptMapping": dict(self.scriptMapping),
		}

	def _fromFullDict(self, data: Dict[str, Any]):
		"""Deserializes config from a plain dict."""
		# Validate profiles before changing any live settings. A malformed import
		# must not leave the current profile list partially replaced.
		languages = self._parseLanguages(data)
		self.enabled = bool(data.get("enabled", True))
		self.defaultLang = str(data.get("defaultLang", ""))
		self.smartUrduArabic = bool(data.get("smartUrduArabic", True))
		self.numberMode = str(data.get("numberMode", "current"))
		self.useUnicodeLanguageDetection = bool(data.get("useUnicodeLanguageDetection", True))
		self.useStatisticalLanguageDetection = bool(data.get("useStatisticalLanguageDetection", True))
		self.granularityMode = str(data.get("granularityMode", "word"))
		self.protectMathSymbols = bool(data.get("protectMathSymbols", True))
		self.mathLanguage = str(data.get("mathLanguage", "current"))
		self.tagMode = str(data.get("tagMode", "override"))
		self.lockedLanguage = None
		self.firstRun = bool(data.get("firstRun", False))
		self._emptyProfilesIntentional = bool(data.get("emptyProfilesIntentional", False))

		if "excludedApps" in data and isinstance(data["excludedApps"], list):
			self.excludedApps = [str(x).strip().lower() for x in data["excludedApps"] if x]

		if "languages" in data:
			self.languages = languages
		if self.languages:
			self._emptyProfilesIntentional = False

		if "scriptMapping" in data and isinstance(data["scriptMapping"], dict):
			for scriptName, langCode in data["scriptMapping"].items():
				if isinstance(langCode, str):
					self.scriptMapping[scriptName] = langCode

	@staticmethod
	def _parseLanguages(data):
		if not isinstance(data, dict):
			raise ValueError("Auto TTS settings must be a JSON object")
		profiles = data.get("languages", {})
		if not isinstance(profiles, dict):
			raise ValueError("Auto TTS languages must be a JSON object")
		languages = {}
		for code, profile in profiles.items():
			if not code or not isinstance(profile, dict):
				raise ValueError("Invalid Auto TTS language profile")
			languages[code] = LanguageVoiceConfig.fromDict(code, profile)
		return languages

	def _readSettingsData(self, path):
		try:
			with open(path, "r", encoding="utf-8") as stream:
				data = json.load(stream)
			self._parseLanguages(data)
			return data
		except FileNotFoundError:
			return None
		except (OSError, ValueError, TypeError) as error:
			log.error(f"AutoTTS: Cannot read settings file '{path}': {error}")
			return None

	def load(self):
		"""Loads settings from addons/autoTTS.json."""
		settingsPath = _getSettingsFilePath()
		try:
			data = self._readSettingsData(settingsPath)
			backupPath = settingsPath + ".bak"
			primaryHasProfiles = isinstance(data, dict) and bool(data.get("languages"))
			primaryWasIntentionallyReset = isinstance(data, dict) and bool(data.get("emptyProfilesIntentional"))
			if not primaryHasProfiles and not primaryWasIntentionallyReset and os.path.isfile(backupPath):
				backupData = self._readSettingsData(backupPath)
				if isinstance(backupData, dict) and backupData.get("languages"):
					data = backupData
					log.error("AutoTTS: Recovered language profiles from autoTTS.json.bak after missing, invalid or unexpectedly empty settings.")
			if isinstance(data, dict):
				self._fromFullDict(data)
		except Exception as e:
			try:
				log.error(f"AutoTTS: Error loading JSON settings: {e}")
			except Exception:
				pass

	def _saveToJSON(self, allowEmptyProfiles=False):
		"""Saves settings to JSON file atomically."""
		try:
			settingsPath = _getSettingsFilePath()
			settingsDir = os.path.dirname(settingsPath)
			if settingsDir and not os.path.isdir(settingsDir):
				os.makedirs(settingsDir, exist_ok=True)
			data = self._toFullDict()
			tmpPath = settingsPath + ".tmp"
			backupPath = settingsPath + ".bak"
			if allowEmptyProfiles:
				self._emptyProfilesIntentional = True
				data["emptyProfilesIntentional"] = True
			elif self.languages:
				self._emptyProfilesIntentional = False
				data["emptyProfilesIntentional"] = False
			elif not self._emptyProfilesIntentional:
				# Never let an unmarked, unexpectedly empty in-memory object destroy
				# a populated primary file or recovery backup during startup/update.
				for protectedPath in (settingsPath, backupPath):
					if not os.path.isfile(protectedPath):
						continue
					try:
						with open(protectedPath, "r", encoding="utf-8") as f:
							protectedData = json.load(f)
						if isinstance(protectedData, dict) and protectedData.get("languages"):
							log.error("AutoTTS: Refusing to overwrite populated profile settings with an unexpected empty profile list.")
							return
					except Exception:
						pass
			with open(tmpPath, "w", encoding="utf-8") as f:
				json.dump(data, f, indent=2, ensure_ascii=False)
			if os.path.exists(settingsPath):
				# Keep the last complete file recoverable before replacing it.
				# This is deliberately outside the add-on package directory so an
				# update cannot discard the user's most recent configuration.
				oldData = self._readSettingsData(settingsPath)
				backupData = self._readSettingsData(backupPath)
				preserveRecoveryBackup = (
					oldData is None
					or (not oldData.get("languages") and bool(backupData and backupData.get("languages")))
				)
				if not preserveRecoveryBackup:
					shutil.copy2(settingsPath, backupPath)
				os.replace(tmpPath, settingsPath)
			else:
				os.rename(tmpPath, settingsPath)
		except Exception as e:
			try:
				log.error(f"AutoTTS: Error saving JSON settings: {e}")
			except Exception:
				pass

	def save(self, allowEmptyProfiles=False):
		"""Saves settings to primary JSON storage."""
		self._saveToJSON(allowEmptyProfiles=allowEmptyProfiles)

	def exportConfig(self, exportFilePath: str):
		"""Exports complete settings to a backup file (.autotts or .json)."""
		data = self._toFullDict()
		with open(exportFilePath, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2, ensure_ascii=False)

	def importConfig(self, importFilePath: str):
		"""Imports settings from a backup file and persists immediately."""
		with open(importFilePath, "r", encoding="utf-8") as f:
			data = json.load(f)
		self._fromFullDict(data)
		self.save()

	def isAppExcluded(self, appProcessName: Optional[str]) -> bool:
		"""Checks if a process name (e.g. 'code.exe') is in the excluded apps list."""
		if not appProcessName:
			return False
		cleanName = appProcessName.strip().lower()
		for excluded in self.excludedApps:
			if cleanName == excluded.lower() or cleanName.endswith(f"\\{excluded.lower()}"):
				return True
		return False

	def resolveLanguageCode(self, langCode: str) -> str:
		"""Resolve a detected/document tag to the best configured profile key.

		Detectors normally return base tags such as ``ur`` while users commonly
		configure a regional profile such as ``ur-pk``. An exact/base profile wins;
		otherwise use the default regional profile for that language, or the first
		enabled configured regional profile when there is only no more specific match.
		"""
		normFull, baseLang = normalize_language_code(langCode or self.defaultLang or "en")
		if normFull in self.languages:
			return normFull
		if baseLang in self.languages:
			return baseLang

		defaultFull, defaultBase = normalize_language_code(self.defaultLang)
		if defaultBase == baseLang and defaultFull in self.languages:
			return defaultFull

		for configuredCode, configuredProfile in self.languages.items():
			_configuredFull, configuredBase = normalize_language_code(configuredCode)
			if configuredBase == baseLang and configuredProfile.enabled:
				return configuredCode
		return normFull

	def getLanguageConfig(self, langCode: str) -> LanguageVoiceConfig:
		"""
		Gets config for a language or dialect tag.
		If a regional dialect (e.g. 'en-PK', 'en-US', 'ur-PK') is not explicitly configured,
		it automatically inherits the configuration of its base language (e.g. 'en', 'ur').
		"""
		if not langCode:
			langCode = self.defaultLang or "en"

		# 1. Exact match
		if langCode in self.languages:
			return self.languages[langCode]

		# 2. Normalized full tag match (e.g. en_pk -> en-pk)
		normFull, baseLang = normalize_language_code(langCode)
		if normFull in self.languages:
			return self.languages[normFull]

		# 3. A base detector tag can map to a configured regional profile, e.g.
		# ``ur`` -> ``ur-pk``. This is essential for automatic switching because
		# Unicode/statistical detectors identify languages, not user dialect tags.
		resolvedCode = self.resolveLanguageCode(normFull)
		if resolvedCode in self.languages:
			return self.languages[resolvedCode]

		# 4. Base language inheritance (e.g. en-PK -> inherits 'en' profile)
		if baseLang in self.languages:
			baseCfg = self.languages[baseLang]
			return LanguageVoiceConfig(
				lang=langCode,
				synth=baseCfg.synth,
				voice=baseCfg.voice,
				sendLang=baseCfg.sendLang,
				enabled=baseCfg.enabled,
				profile=baseCfg.profile,
				useCustomProsody=baseCfg.useCustomProsody,
				customRate=baseCfg.customRate,
				customPitch=baseCfg.customPitch,
				customVolume=baseCfg.customVolume,
			)

		# 5. Check if defaultLang matches base language
		defNormFull, defBase = normalize_language_code(self.defaultLang)
		if baseLang == defBase and self.defaultLang in self.languages:
			baseCfg = self.languages[self.defaultLang]
			return LanguageVoiceConfig(
				lang=langCode,
				synth=baseCfg.synth,
				voice=baseCfg.voice,
				sendLang=baseCfg.sendLang,
				enabled=baseCfg.enabled,
				profile=baseCfg.profile,
				useCustomProsody=baseCfg.useCustomProsody,
				customRate=baseCfg.customRate,
				customPitch=baseCfg.customPitch,
				customVolume=baseCfg.customVolume,
			)

		# 6. Return a temporary default config without storing it
		return LanguageVoiceConfig(lang=langCode)

	def setLanguageConfig(self, langConfig: LanguageVoiceConfig):
		"""Updates a language config and persists immediately."""
		self._emptyProfilesIntentional = False
		self.languages[langConfig.lang] = langConfig
		self.save()

	def removeLanguageConfig(self, langCode: str):
		"""Removes a language configuration and persists immediately."""
		if langCode in self.languages:
			del self.languages[langCode]
			self.save(allowEmptyProfiles=not self.languages)


# Global singleton instance
sharedConfig = AutoTTSConfig()
