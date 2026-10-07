# Auto TTS for NVDA - Settings Panel (Profile-Based)
# Covered by GNU General Public License (GPL)

from typing import List, Tuple, Dict, Any, Optional
import locale as pythonLocale
import re

try:
	import wx
	from gui import guiHelper
	from gui.settingsDialogs import SettingsPanel
	import config
	import addonHandler
	import languageHandler
	import synthDriverHandler
	import speech
	from speech.commands import LangChangeCommand
	from logHandler import log
	addonHandler.initTranslation()
except ImportError:
	class SettingsPanel: pass
	class guiHelper:
		class BoxSizerHelper:
			def __init__(self, *args, **kwargs): pass
			def addItem(self, item): return item
			def addLabeledControl(self, label, cls, **kwargs): return cls()
	class speech:
		@staticmethod
		def speak(seq): pass
	class synthDriverHandler:
		synth = None
		@staticmethod
		def getSynthList(): return [("espeak", "eSpeak NG")]
	class languageHandler:
		@staticmethod
		def getLanguageDescription(code): return code
	class config:
		class conf:
			@staticmethod
			def listProfiles(): return []
	class addonHandler:
		@staticmethod
		def initTranslation(): pass
	class log:
		@staticmethod
		def error(msg): pass
		@staticmethod
		def exception(msg): pass
	def _(s): return s

from synthDrivers.autoTTS.configManager import (
	sharedConfig,
	LanguageVoiceConfig,
	DEFAULT_EXCLUDED_APPS,
)
from synthDrivers.autoTTS.languageDetection import (
	DEFAULT_SCRIPT_MAPPINGS,
	normalize_language_code,
	get_base_language,
)


def _getSynthInstance(name: str):
	import importlib
	if not name:
		name = "espeak"
	return importlib.import_module(f"synthDrivers.{name}", package="synthDrivers").SynthDriver()


# World languages sorted alphabetically by display name
BASE_WORLD_LANGUAGES: List[Tuple[str, str]] = sorted([
	("af", "Afrikaans"),
	("sq", "Albanian (Shqip)"),
	("ar", "Arabic (العربية)"),
	("az", "Azerbaijani (Azərbaycan)"),
	("bn", "Bengali (বাংলা)"),
	("bg", "Bulgarian (Български)"),
	("ca", "Catalan (Català)"),
	("zh", "Chinese (中文)"),
	("hr", "Croatian (Hrvatski)"),
	("cs", "Czech (Čeština)"),
	("da", "Danish (Dansk)"),
	("nl", "Dutch (Nederlands)"),
	("en", "English"),
	("et", "Estonian (Eesti)"),
	("fi", "Finnish (Suomi)"),
	("fr", "French (Français)"),
	("ka", "Georgian (ქართული)"),
	("de", "German (Deutsch)"),
	("el", "Greek (Ελληνικά)"),
	("gu", "Gujarati (ગુજરાતી)"),
	("he", "Hebrew (עברית)"),
	("hi", "Hindi (हिन्दी)"),
	("hu", "Hungarian (Magyar)"),
	("is", "Icelandic (Íslenska)"),
	("id", "Indonesian (Bahasa Indonesia)"),
	("it", "Italian (Italiano)"),
	("ja", "Japanese (日本語)"),
	("kn", "Kannada (ಕನ್ನಡ)"),
	("ko", "Korean (한국어)"),
	("lv", "Latvian (Latviešu)"),
	("lt", "Lithuanian (Lietuvių)"),
	("ms", "Malay (Bahasa Melayu)"),
	("ml", "Malayalam (മലയാളം)"),
	("mr", "Marathi (मराठी)"),
	("ne", "Nepali (नेपाली)"),
	("no", "Norwegian (Norsk)"),
	("pa", "Punjabi (ਪੰਜਾਬੀ)"),
	("ps", "Pashto (پښتو)"),
	("fa", "Persian (فارسی)"),
	("pl", "Polish (Polski)"),
	("pt", "Portuguese (Português)"),
	("ro", "Romanian (Română)"),
	("ru", "Russian (Русский)"),
	("sr", "Serbian (Српски)"),
	("sd", "Sindhi (سنڌي)"),
	("si", "Sinhala (සිංහල)"),
	("sk", "Slovak (Slovenčina)"),
	("sl", "Slovenian (Slovenščina)"),
	("es", "Spanish (Español)"),
	("sw", "Swahili (Kiswahili)"),
	("sv", "Swedish (Svenska)"),
	("ta", "Tamil (தமிழ்)"),
	("te", "Telugu (తెలుగు)"),
	("th", "Thai (ไทย)"),
	("tr", "Turkish (Türkçe)"),
	("uk", "Ukrainian (Українська)"),
	("ur", "Urdu (اردو)"),
	("vi", "Vietnamese (Tiếng Việt)"),
], key=lambda x: x[1].lower())


def _buildLanguageCatalog() -> List[Tuple[str, str]]:
	"""Build a broad BCP-47 catalog without limiting users to a fixed list."""
	catalog = {code: name for code, name in BASE_WORLD_LANGUAGES}

	# Python's Windows locale table supplies regional language tags available on
	# Windows without adding a large third-party language database.
	for localeName in set(pythonLocale.windows_locale.values()):
		normFull, baseLang = normalize_language_code(localeName)
		if not normFull:
			continue
		try:
			description = languageHandler.getLanguageDescription(normFull) or normFull
		except Exception:
			description = normFull
		catalog.setdefault(normFull, description)

	# Preserve every custom language/dialect the user has already configured.
	for code in sharedConfig.languages:
		normFull, baseLang = normalize_language_code(code)
		catalog.setdefault(normFull, _getLangName(normFull))

	# Add NVDA interface languages when the running NVDA version exposes them.
	try:
		for entry in languageHandler.getAvailableLanguages():
			code = entry[0] if isinstance(entry, (tuple, list)) else entry
			normFull, baseLang = normalize_language_code(code)
			catalog.setdefault(normFull, _getLangName(normFull))
	except Exception:
		pass

	return sorted(catalog.items(), key=lambda item: (str(item[1]).lower(), item[0]))

SAMPLE_TEXTS: Dict[str, str] = {
	"ur": "یہ آٹو ٹی ٹی ایس کا ٹیسٹ پیغام ہے۔ آواز اور رفتار کی تصدیق کی جا رہی ہے۔",
	"ar": "هذه رسالة اختبار لنظام تحويل النص إلى كلام التلقائي.",
	"en": "This is a test of Auto TTS for NVDA. Speech rate and voice settings are verified.",
	"hi": "यह ऑटो टीटीएस का परीक्षण संदेश है। ध्वनि और गति की पुष्टि हो रही है।",
	"fa": "این یک پیام آزمایشی برای تبدیل متن به گفتار است.",
	"ps": "دا د متن څخه د خبرو کولو ازموینې پیغام دی.",
	"es": "Este es un mensaje de prueba para Auto TTS en NVDA.",
	"fr": "Ceci est un message de test pour Auto TTS dans NVDA.",
	"de": "Dies ist eine Testnachricht für Auto TTS in NVDA.",
	"ru": "Это тестовое сообщение для Auto TTS в NVDA.",
	"zh": "这是 NVDA 自动语音转换的测试消息。",
	"ja": "これは NVDA Auto TTS のテストメッセージです。",
	"ko": "NVDA 자동 음성 변환 테스트 메시지입니다.",
	"tr": "Bu NVDA Auto TTS için bir test mesajıdır.",
	"pt": "Esta é uma mensagem de teste para o Auto TTS no NVDA.",
	"it": "Questo è un messaggio di test per Auto TTS in NVDA.",
}

NUMBER_MODES: List[Tuple[str, str]] = [
	("current", _("Current speaking language (Contextual)")),
	("default", _("Default / Fallback language")),
	("en", _("Always English (en)")),
	("ur", _("Always Urdu (ur)")),
	("ar", _("Always Arabic (ar)")),
	("hi", _("Always Hindi (hi)")),
]

GRANULARITY_MODES: List[Tuple[str, str]] = [
	("word", _("Word-by-Word (Default - switches on every word)")),
	("sentence", _("Sentence / Clause Level (Switches on clauses & sentences)")),
	("line", _("Line Level (Switches on new lines)")),
]

MATH_LANGUAGE_MODES: List[Tuple[str, str]] = [
	("current", _("Current speaking language")),
	("default", _("Default language profile")),
]

TAG_MODES: List[Tuple[str, str]] = [
	("override", _("Detect from text even when the document language tag is wrong")),
	("preferTags", _("Trust document language tags when they are present")),
]


def _safeInt(val: Any, default: int = 50) -> int:
	try:
		if val is not None:
			return int(val)
	except Exception:
		pass
	return default


def _getInstalledSynths() -> List[Tuple[str, str]]:
	"""Returns list of (synthId, displayName) for all installed synths."""
	synths = [("", _("[Use NVDA Default Synthesizer]"))]
	try:
		for id, name in synthDriverHandler.getSynthList():
			if id not in ("autoTTS", "silence"):
				synths.append((id, name))
	except Exception:
		synths.append(("espeak", "eSpeak NG"))
	return synths


def _getLangName(code: str) -> str:
	"""Gets display name for a language code."""
	for c, name in BASE_WORLD_LANGUAGES:
		if c == code:
			return name
	try:
		return languageHandler.getLanguageDescription(code) or code
	except Exception:
		return code


def _getAvailableProfiles() -> List[Tuple[str, str]]:
	"""Returns list of (profileName, displayName) for NVDA config profiles."""
	profiles = [("", _("[None - Use TTS default settings]"))]
	try:
		for name in config.conf.listProfiles():
			profiles.append((name, name))
	except Exception:
		pass
	return profiles


def _getPreviewSynth(synthId: str):
	"""Gets an already-cached synth instance for preview."""
	activeSynth = getattr(synthDriverHandler, "synth", None)

	if not synthId:
		if activeSynth and getattr(activeSynth, "name", "") == "autoTTS":
			defLang = sharedConfig.defaultLang
			defCfg = sharedConfig.getLanguageConfig(defLang)
			if defCfg.synth and hasattr(activeSynth, "_synthCache") and defCfg.synth in activeSynth._synthCache:
				return activeSynth._synthCache[defCfg.synth][0]
			if hasattr(activeSynth, "_synthCache") and "espeak" in activeSynth._synthCache:
				return activeSynth._synthCache["espeak"][0]
		elif activeSynth and getattr(activeSynth, "name", "") not in ("autoTTS", "silence"):
			return activeSynth

	if activeSynth and getattr(activeSynth, "name", "") == "autoTTS":
		if hasattr(activeSynth, "_synthCache") and synthId in activeSynth._synthCache:
			return activeSynth._synthCache[synthId][0]

	if activeSynth and getattr(activeSynth, "name", "").lower() == (synthId or "").lower():
		return activeSynth

	if not hasattr(_getPreviewSynth, "_fallbackCache"):
		_getPreviewSynth._fallbackCache = {}
	if synthId in _getPreviewSynth._fallbackCache:
		return _getPreviewSynth._fallbackCache[synthId]

	return None


def _ensurePreviewSynth(synthId: str):
	"""Gets or creates a synth instance when user explicitly requests speech."""
	synth = _getPreviewSynth(synthId)
	if synth is not None:
		return synth

	activeSynth = getattr(synthDriverHandler, "synth", None)

	if not synthId:
		if activeSynth and getattr(activeSynth, "name", "") == "autoTTS":
			if hasattr(activeSynth, "_getSynth"):
				return activeSynth._getSynth(sharedConfig.defaultLang)
		elif activeSynth and getattr(activeSynth, "name", "") not in ("autoTTS", "silence"):
			return activeSynth
		synthId = "espeak"

	if activeSynth and getattr(activeSynth, "name", "") == "autoTTS":
		if hasattr(activeSynth, "_getSynthByName"):
			return activeSynth._getSynthByName(synthId)

	try:
		if not hasattr(_getPreviewSynth, "_fallbackCache"):
			_getPreviewSynth._fallbackCache = {}
		if synthId not in _getPreviewSynth._fallbackCache:
			s = _getSynthInstance(synthId)
			_getPreviewSynth._fallbackCache[synthId] = s
		return _getPreviewSynth._fallbackCache.get(synthId)
	except Exception as e:
		log.error(f"AutoTTS: Error ensuring preview synth for '{synthId}': {e}")
		return None


def _saveSynthState(synthId: str) -> Dict[str, Any]:
	"""Saves the current state of a cached synth for later restoration."""
	state = {}
	synth = _getPreviewSynth(synthId)
	if synth:
		for attr in ("voice", "rate", "pitch", "volume"):
			try:
				if hasattr(synth, attr):
					state[attr] = getattr(synth, attr)
			except Exception:
				pass
	return state


def _restoreSynthState(synthId: str, state: Dict[str, Any]):
	"""Restores a cached synth to a previously saved state."""
	if not state:
		return
	synth = _getPreviewSynth(synthId)
	if synth:
		if "voice" in state:
			try:
				if hasattr(synth, "voice") and synth.voice != state["voice"]:
					synth.voice = state["voice"]
			except Exception:
				pass
		for attr in ("rate", "pitch", "volume"):
			if attr in state:
				try:
					setattr(synth, attr, state[attr])
				except Exception:
					pass


def _getVoicesForSynth(synthId: str, voiceListCache: Dict) -> List[Tuple[str, str]]:
	"""Gets available voices for a synth using already-cached instances."""
	cacheKey = synthId or "__default__"
	if cacheKey in voiceListCache:
		return voiceListCache[cacheKey]

	voices = []
	try:
		cachedSynth = _getPreviewSynth(synthId)
		if cachedSynth and hasattr(cachedSynth, "availableVoices") and cachedSynth.availableVoices:
			for vId, vInfo in cachedSynth.availableVoices.items():
				vName = getattr(vInfo, "displayName", None) or getattr(vInfo, "name", None) or str(vId)
				voices.append((vId, vName))
	except Exception as e:
		log.error(f"AutoTTS: Error retrieving voices for '{synthId}': {e}")

	if not voices:
		voices = [("", _("Default Voice"))]
	voiceListCache[cacheKey] = voices
	return voices


def _getSynthCurrentSettings(synthId: str) -> Dict[str, Any]:
	"""Gets synth's current rate/pitch/volume from autoTTS cache or NVDA config."""
	res = {}
	synth = _getPreviewSynth(synthId)
	if synth:
		for attr in ("rate", "pitch", "volume"):
			try:
				if hasattr(synth, attr):
					res[attr] = getattr(synth, attr)
			except Exception:
				pass
		if res:
			return res
	try:
		if hasattr(config, "conf") and "speech" in config.conf:
			targetKey = (synthId or "").lower()
			for k in config.conf["speech"].keys():
				if k.lower() == targetKey:
					for p in ("rate", "pitch", "volume"):
						if p in config.conf["speech"][k]:
							res[p] = config.conf["speech"][k][p]
					return res
	except Exception:
		pass
	return res


def _getSynthDefaultVoice(synthId: str) -> str:
	"""Gets the synth's current/default voice from autoTTS cache or NVDA config."""
	synth = _getPreviewSynth(synthId)
	if synth:
		try:
			return synth.voice
		except Exception:
			pass
	try:
		if hasattr(config, "conf") and "speech" in config.conf:
			targetKey = (synthId or "").lower()
			for k in config.conf["speech"].keys():
				if k.lower() == targetKey:
					return config.conf["speech"][k].get("voice", "")
	except Exception:
		pass
	return ""


# ─────────────────────────────────────────────────────────────────────────────
# App Exclusion Dialog (Auto-Bypass)
# ─────────────────────────────────────────────────────────────────────────────

class AppExclusionDialog(wx.Dialog):
	"""Dialog for managing applications excluded from language auto-switching."""

	def __init__(self, parent):
		super().__init__(parent, title=_("Excluded Applications (Auto-Bypass)"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.excludedList = list(sharedConfig.excludedApps)
		self._buildUI()
		self.Fit()
		self.CentreOnScreen()

	def _buildUI(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		pad = 8

		descText = wx.StaticText(
			self,
			label=_(
				"In excluded applications (e.g. code editors, command prompts), Auto TTS\n"
				"bypasses language switching and reads all text using your default voice."
			)
		)
		mainSizer.Add(descText, 0, wx.ALL, pad)

		# List of excluded apps
		mainSizer.Add(wx.StaticText(self, label=_("&Excluded Application Processes:")), 0, wx.LEFT | wx.TOP, pad)
		self.appsListBox = wx.ListBox(self, size=(350, 180), choices=self.excludedList, style=wx.LB_SINGLE)
		self.appsListBox.Bind(wx.EVT_LISTBOX, self._onSelectionChanged)
		mainSizer.Add(self.appsListBox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		# Add process entry & buttons row
		addSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.procText = wx.TextCtrl(self, size=(200, -1))
		self.addBtn = wx.Button(self, label=_("&Add Process"))
		self.addBtn.Bind(wx.EVT_BUTTON, self._onAdd)
		self.removeBtn = wx.Button(self, label=_("&Remove"))
		self.removeBtn.Bind(wx.EVT_BUTTON, self._onRemove)
		self.removeBtn.Enable(False)

		addSizer.Add(self.procText, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
		addSizer.Add(self.addBtn, 0, wx.RIGHT, 4)
		addSizer.Add(self.removeBtn, 0)
		mainSizer.Add(addSizer, 0, wx.EXPAND | wx.ALL, pad)

		# Dialog OK / Cancel
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.okBtn = wx.Button(self, wx.ID_OK, label=_("OK"))
		self.okBtn.Bind(wx.EVT_BUTTON, self._onOK)
		self.okBtn.SetDefault()
		self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
		btnSizer.Add(self.okBtn, 0, wx.RIGHT, pad)
		btnSizer.Add(self.cancelBtn, 0)
		mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, pad)

		self.SetSizer(mainSizer)

	def _onSelectionChanged(self, event):
		sel = self.appsListBox.GetSelection()
		self.removeBtn.Enable(sel != wx.NOT_FOUND)

	def _onAdd(self, event):
		name = self.procText.GetValue().strip().lower()
		if name:
			if not name.endswith(".exe"):
				name += ".exe"
			if name not in self.excludedList:
				self.excludedList.append(name)
				self.appsListBox.Append(name)
				self.procText.Clear()

	def _onRemove(self, event):
		sel = self.appsListBox.GetSelection()
		if sel != wx.NOT_FOUND:
			del self.excludedList[sel]
			self.appsListBox.Delete(sel)
			self.removeBtn.Enable(False)

	def _onOK(self, event):
		sharedConfig.excludedApps = list(self.excludedList)
		sharedConfig.save()
		self.EndModal(wx.ID_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Profile Editor Sub-Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ProfileEditorDialog(wx.Dialog):
	"""Sub-dialog for adding or editing a single language profile."""

	def __init__(self, parent, langConfig=None, voiceListCache=None, availableSynths=None):
		isEdit = langConfig is not None
		title = _("Edit Language Profile") if isEdit else _("Add Language Profile")
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self._voiceListCache = voiceListCache if voiceListCache is not None else {}
		self._availableSynths = availableSynths or _getInstalledSynths()
		self._availableProfiles = _getAvailableProfiles()
		self._languageOptions = _buildLanguageCatalog()
		self.currentVoices: List[Tuple[str, str]] = [("", _("Default Voice"))]
		self.result: Optional[LanguageVoiceConfig] = None

		self._originalSynthStates: Dict[str, Dict[str, Any]] = {}
		self._previewTimer = None

		try:
			self._buildUI()

			if isEdit and langConfig:
				self._loadFromConfig(langConfig)
			else:
				for i, (c, langName) in enumerate(self._languageOptions):
					if c not in sharedConfig.languages:
						self.langChoice.SetSelection(i)
						break
				if self.synthChoice.GetCount() > 0:
					self.synthChoice.SetSelection(0)
					self._loadVoicesForSelectedSynth()

			self._updateProsodyState()
			self.Fit()
			self.CentreOnScreen()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error initializing ProfileEditorDialog: {e}")
			except Exception:
				pass

	def _buildUI(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		pad = 8

		# Language
		mainSizer.Add(wx.StaticText(self, label=_("&Language:")), 0, wx.LEFT | wx.TOP, pad)
		langLabels = [f"{name} ({code})" for code, name in self._languageOptions]
		self.langChoice = wx.ComboBox(
			self,
			choices=langLabels,
			name=_("Language or BCP-47 code"),
			style=wx.CB_DROPDOWN,
		)
		self.langChoice.SetSelection(0)
		self.langChoice.Bind(wx.EVT_CHOICE, self._onLangChanged)
		self.langChoice.Bind(wx.EVT_TEXT, self._onLangChanged)
		mainSizer.Add(self.langChoice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		# TTS Engine
		mainSizer.Add(wx.StaticText(self, label=_("&TTS Engine:")), 0, wx.LEFT | wx.TOP, pad)
		synthLabels = [sName for sId, sName in self._availableSynths]
		self.synthChoice = wx.Choice(self, choices=synthLabels, name=_("TTS Engine"))
		self.synthChoice.Bind(wx.EVT_CHOICE, self._onSynthChanged)
		mainSizer.Add(self.synthChoice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		# Voice
		mainSizer.Add(wx.StaticText(self, label=_("&Voice:")), 0, wx.LEFT | wx.TOP, pad)
		self.voiceChoice = wx.Choice(self, choices=[_("Default Voice")], name=_("Voice"))
		self.voiceChoice.Bind(wx.EVT_CHOICE, self._onVoiceChanged)
		mainSizer.Add(self.voiceChoice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		# Send lang
		self.sendLangCheck = wx.CheckBox(self, label=_("&Send language information to synthesizer"))
		self.sendLangCheck.SetValue(True)
		mainSizer.Add(self.sendLangCheck, 0, wx.LEFT | wx.TOP, pad)

		self.profileEnabledCheck = wx.CheckBox(self, label=_("&Enable this language profile for automatic switching"))
		self.profileEnabledCheck.SetValue(True)
		mainSizer.Add(self.profileEnabledCheck, 0, wx.LEFT | wx.TOP, pad)

		# NVDA Profile
		mainSizer.Add(wx.StaticText(self, label=_("NVDA &Profile (for rate/pitch/volume):")), 0, wx.LEFT | wx.TOP, pad)
		profileLabels = [pName for pId, pName in self._availableProfiles]
		self.profileChoice = wx.Choice(self, choices=profileLabels, name=_("NVDA Profile"))
		self.profileChoice.SetSelection(0)
		mainSizer.Add(self.profileChoice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		mainSizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, pad)

		# Custom Prosody
		self.customProsodyCheck = wx.CheckBox(self, label=_("&Use custom rate, pitch and volume (overrides TTS/profile defaults)"))
		self.customProsodyCheck.SetValue(False)
		self.customProsodyCheck.Bind(wx.EVT_CHECKBOX, self._onProsodyCheckChanged)
		mainSizer.Add(self.customProsodyCheck, 0, wx.LEFT | wx.TOP, pad)

		mainSizer.Add(wx.StaticText(self, label=_("Ra&te:")), 0, wx.LEFT | wx.TOP, pad)
		self.rateSlider = wx.Slider(self, value=50, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL, name=_("Rate"))
		self.rateSlider.Bind(wx.EVT_SLIDER, self._onRateChanged)
		mainSizer.Add(self.rateSlider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		mainSizer.Add(wx.StaticText(self, label=_("Pi&tch:")), 0, wx.LEFT | wx.TOP, pad)
		self.pitchSlider = wx.Slider(self, value=50, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL, name=_("Pitch"))
		self.pitchSlider.Bind(wx.EVT_SLIDER, self._onPitchChanged)
		mainSizer.Add(self.pitchSlider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		mainSizer.Add(wx.StaticText(self, label=_("Vo&lume:")), 0, wx.LEFT | wx.TOP, pad)
		self.volumeSlider = wx.Slider(self, value=100, minValue=0, maxValue=100, style=wx.SL_HORIZONTAL, name=_("Volume"))
		self.volumeSlider.Bind(wx.EVT_SLIDER, self._onVolumeChanged)
		mainSizer.Add(self.volumeSlider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, pad)

		mainSizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, pad)

		# Test Speech button
		self.testBtn = wx.Button(self, label=_("&Test Speech"))
		self.testBtn.Bind(wx.EVT_BUTTON, self._onTest)
		mainSizer.Add(self.testBtn, 0, wx.LEFT | wx.TOP | wx.BOTTOM, pad)

		# OK / Cancel
		btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.okBtn = wx.Button(self, label=_("OK"))
		self.okBtn.Bind(wx.EVT_BUTTON, self._onOK)
		self.okBtn.SetDefault()
		self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
		self.cancelBtn.Bind(wx.EVT_BUTTON, self._onCancel)
		btnSizer.Add(self.okBtn, 0, wx.RIGHT, pad)
		btnSizer.Add(self.cancelBtn, 0)
		mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, pad)

		self._previewTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onPreviewTimer, self._previewTimer)

		self.mainSizer = mainSizer
		self.SetSizer(mainSizer)

	def _loadFromConfig(self, cfg: LanguageVoiceConfig):
		normFull, baseCode = normalize_language_code(cfg.lang)
		langIdx = next((i for i, (c, langName) in enumerate(self._languageOptions) if c == normFull), -1)
		if langIdx >= 0:
			self.langChoice.SetSelection(langIdx)
		else:
			self.langChoice.SetValue(normFull)

		synthIdx = 0
		for i, (sId, sName) in enumerate(self._availableSynths):
			if sId.lower() == (cfg.synth or "").lower():
				synthIdx = i
				break
		self.synthChoice.SetSelection(synthIdx)

		self._loadVoicesForSelectedSynth()

		if cfg.voice:
			for i, (vId, vName) in enumerate(self.currentVoices):
				if str(vId).lower() == str(cfg.voice).lower():
					self.voiceChoice.SetSelection(i)
					break

		self.sendLangCheck.SetValue(cfg.sendLang)
		self.profileEnabledCheck.SetValue(cfg.enabled)

		profileIdx = 0
		if cfg.profile:
			for i, (pId, pName) in enumerate(self._availableProfiles):
				if pId == cfg.profile:
					profileIdx = i
					break
		self.profileChoice.SetSelection(profileIdx)

		self.customProsodyCheck.SetValue(cfg.useCustomProsody)
		if cfg.useCustomProsody:
			if cfg.customRate >= 0:
				self.rateSlider.SetValue(cfg.customRate)
			if cfg.customPitch >= 0:
				self.pitchSlider.SetValue(cfg.customPitch)
			if cfg.customVolume >= 0:
				self.volumeSlider.SetValue(cfg.customVolume)

	def _getSelectedSynthId(self) -> str:
		idx = self.synthChoice.GetSelection()
		if 0 <= idx < len(self._availableSynths):
			return self._availableSynths[idx][0]
		return ""

	def _getSelectedLangCode(self) -> str:
		idx = self.langChoice.GetSelection()
		if 0 <= idx < len(self._languageOptions):
			return self._languageOptions[idx][0]
		value = self.langChoice.GetValue().strip()
		match = re.search(r"\(([A-Za-z]{2,8}(?:[-_][A-Za-z0-9]{1,8})*)\)\s*$", value)
		if match:
			value = match.group(1)
		if not value:
			return ""
		normFull, baseLang = normalize_language_code(value)
		if re.fullmatch(r"[a-z]{2,8}(?:-[a-z0-9]{1,8})*", normFull):
			return normFull
		return ""

	def _getSelectedProfileName(self) -> Optional[str]:
		idx = self.profileChoice.GetSelection()
		if 0 <= idx < len(self._availableProfiles):
			pId = self._availableProfiles[idx][0]
			return pId if pId else None
		return None

	def _updateProsodyState(self):
		enabled = self.customProsodyCheck.GetValue()
		self.rateSlider.Enable(enabled)
		self.pitchSlider.Enable(enabled)
		self.volumeSlider.Enable(enabled)

	def _loadVoicesForSelectedSynth(self):
		synthId = self._getSelectedSynthId()
		langCode = self._getSelectedLangCode()
		baseLang = get_base_language(langCode)
		langName = _getLangName(langCode).lower()

		if synthId and synthId not in self._originalSynthStates:
			self._originalSynthStates[synthId] = _saveSynthState(synthId)

		try:
			allVoices = _getVoicesForSynth(synthId, self._voiceListCache)
		except Exception:
			allVoices = [("", _("Default Voice"))]

		if langCode and len(allVoices) > 1:
			langLower = langCode.lower()
			baseLower = baseLang.lower()
			filtered = []
			for vId, vName in allVoices:
				if not vId:
					continue
				vIdLower = str(vId).lower()
				vNameLower = str(vName).lower()

				isMatch = (
					vIdLower == langLower
					or vIdLower == baseLower
					or vIdLower.startswith(f"{langLower}_") or vIdLower.startswith(f"{langLower}-")
					or vIdLower.startswith(f"{baseLower}_") or vIdLower.startswith(f"{baseLower}-")
					or f"({langLower})" in vNameLower or f"[{langLower}]" in vNameLower
					or f"({baseLower})" in vNameLower or f"[{baseLower}]" in vNameLower
					or f"_{langLower}" in vIdLower or f"-{langLower}" in vIdLower
					or f"_{baseLower}" in vIdLower or f"-{baseLower}" in vIdLower
					or langName in vNameLower
				)
				if isMatch:
					filtered.append((vId, vName))

			if filtered:
				self.currentVoices = [("", _("Default Voice"))] + filtered
			else:
				self.currentVoices = allVoices
		else:
			self.currentVoices = allVoices

		self.voiceChoice.Clear()
		for vId, vName in self.currentVoices:
			self.voiceChoice.Append(vName)

		defaultVoice = _getSynthDefaultVoice(synthId)
		vIdx = -1
		if defaultVoice:
			for i, (vId, vName) in enumerate(self.currentVoices):
				if str(vId).lower() == str(defaultVoice).lower():
					vIdx = i
					break

		if vIdx == -1 and langCode:
			langCodeLower = langCode.lower()
			baseLower = baseLang.lower()
			for i, (vId, vName) in enumerate(self.currentVoices):
				vIdLower = str(vId).lower()
				vNameLower = str(vName).lower()
				if (f"{langCodeLower}_" in vIdLower or f"{langCodeLower}-" in vIdLower
					or f"{baseLower}_" in vIdLower or f"{baseLower}-" in vIdLower
					or f"({langCodeLower})" in vNameLower or f"[{langCodeLower}]" in vNameLower
					or langCodeLower in vIdLower or baseLower in vIdLower
					or langName in vNameLower):
					vIdx = i
					break

		if vIdx == -1:
			vIdx = 0

		if self.voiceChoice.GetCount() > 0:
			self.voiceChoice.SetSelection(vIdx)

		self._applyVoiceToPreviewSynth()

	def _applyVoiceToPreviewSynth(self):
		synthId = self._getSelectedSynthId()
		voiceIdx = self.voiceChoice.GetSelection()
		voiceId = self.currentVoices[voiceIdx][0] if 0 <= voiceIdx < len(self.currentVoices) else ""
		synth = _ensurePreviewSynth(synthId)
		if synth and hasattr(synth, "voice"):
			try:
				if voiceId and voiceId in getattr(synth, "availableVoices", {}):
					synth.voice = voiceId
			except Exception:
				pass

	def _applyProsodyToPreviewSynth(self):
		synthId = self._getSelectedSynthId()
		synth = _ensurePreviewSynth(synthId)
		if synth:
			try:
				if hasattr(synth, "rate"):
					synth.rate = self.rateSlider.GetValue()
				if hasattr(synth, "pitch"):
					synth.pitch = self.pitchSlider.GetValue()
				if hasattr(synth, "volume"):
					synth.volume = self.volumeSlider.GetValue()
			except Exception:
				pass

	def _onSynthChanged(self, event):
		self._loadVoicesForSelectedSynth()

	def _onVoiceChanged(self, event):
		self._applyVoiceToPreviewSynth()

	def _onLangChanged(self, event):
		self._loadVoicesForSelectedSynth()

	def _onProsodyCheckChanged(self, event):
		self._updateProsodyState()
		if self.customProsodyCheck.GetValue():
			synthId = self._getSelectedSynthId()
			settings = _getSynthCurrentSettings(synthId or "espeak")
			if settings:
				if "rate" in settings:
					self.rateSlider.SetValue(_safeInt(settings["rate"], 50))
				if "pitch" in settings:
					self.pitchSlider.SetValue(_safeInt(settings["pitch"], 50))
				if "volume" in settings:
					self.volumeSlider.SetValue(_safeInt(settings["volume"], 100))
		else:
			synthId = self._getSelectedSynthId()
			if synthId in self._originalSynthStates:
				_restoreSynthState(synthId, self._originalSynthStates[synthId])

	def _onRateChanged(self, event):
		if self.customProsodyCheck.GetValue():
			self._applyProsodyToPreviewSynth()
			self._schedulePreviewSpeech()

	def _onPitchChanged(self, event):
		if self.customProsodyCheck.GetValue():
			self._applyProsodyToPreviewSynth()
			self._schedulePreviewSpeech()

	def _onVolumeChanged(self, event):
		if self.customProsodyCheck.GetValue():
			self._applyProsodyToPreviewSynth()
			self._schedulePreviewSpeech()

	def _schedulePreviewSpeech(self):
		if self._previewTimer:
			self._previewTimer.Stop()
			self._previewTimer.Start(500, oneShot=True)

	def _onPreviewTimer(self, event):
		self._speakPreviewSample()

	def _speakPreviewSample(self):
		synthId = self._getSelectedSynthId()
		synth = _ensurePreviewSynth(synthId)
		activeWrapper = getattr(synthDriverHandler, "synth", None)
		if activeWrapper and getattr(activeWrapper, "name", "") == "autoTTS" and getattr(activeWrapper, "_isSpeaking", False):
			# A direct child preview must first invalidate the wrapper's queue and
			# marker; otherwise its completion can leave normal speech stuck.
			activeWrapper.cancel()

		langCode = self._getSelectedLangCode()
		baseLang = get_base_language(langCode)
		sampleText = SAMPLE_TEXTS.get(baseLang, SAMPLE_TEXTS.get(langCode, f"This is a test for language {langCode}. Auto TTS is active."))

		self._applyVoiceToPreviewSynth()
		if self.customProsodyCheck.GetValue():
			self._applyProsodyToPreviewSynth()

		spoken = False
		if synth is not None:
			try:
				synth.cancel()
			except Exception:
				pass

			try:
				supportedCmds = getattr(synth, "supportedCommands", set())
				if self.sendLangCheck.GetValue() and LangChangeCommand in supportedCmds:
					seq = [LangChangeCommand(baseLang), sampleText]
				else:
					seq = [sampleText]
				synth.speak(seq)
				spoken = True
			except Exception as e:
				log.error(f"AutoTTS: Error speaking preview sample with synth '{synthId}': {e}")

		if not spoken:
			try:
				speech.speak([sampleText])
			except Exception:
				pass

	def _onTest(self, event):
		synthId = self._getSelectedSynthId()
		cacheKey = synthId or "__default__"
		hadVoicesBefore = cacheKey in self._voiceListCache and len(self._voiceListCache.get(cacheKey, [])) > 1
		self._speakPreviewSample()
		if not hadVoicesBefore:
			if cacheKey in self._voiceListCache:
				del self._voiceListCache[cacheKey]
			self._loadVoicesForSelectedSynth()

	def _onOK(self, event):
		langCode = self._getSelectedLangCode()
		if not langCode:
			wx.MessageBox(
				_("Enter a valid BCP-47 language code, for example en, sw-KE, fil-PH or ckb-IQ."),
				_("Invalid language code"),
				wx.OK | wx.ICON_WARNING,
				parent=self,
			)
			return
		synthId = self._getSelectedSynthId()
		voiceIdx = self.voiceChoice.GetSelection()
		voiceId = self.currentVoices[voiceIdx][0] if 0 <= voiceIdx < len(self.currentVoices) else None
		profileName = self._getSelectedProfileName()
		useCustomProsody = self.customProsodyCheck.GetValue()

		self.result = LanguageVoiceConfig(
			lang=langCode,
			synth=synthId,
			voice=voiceId if voiceId else None,
			sendLang=self.sendLangCheck.GetValue(),
			enabled=self.profileEnabledCheck.GetValue(),
			profile=profileName,
			useCustomProsody=useCustomProsody,
			customRate=self.rateSlider.GetValue() if useCustomProsody else -1,
			customPitch=self.pitchSlider.GetValue() if useCustomProsody else -1,
			customVolume=self.volumeSlider.GetValue() if useCustomProsody else -1,
		)
		self.EndModal(wx.ID_OK)

	def _onCancel(self, event=None):
		for synthId, state in self._originalSynthStates.items():
			_restoreSynthState(synthId, state)

		if self._previewTimer:
			self._previewTimer.Stop()

		synthId = self._getSelectedSynthId()
		synth = _getPreviewSynth(synthId)
		if synth:
			try:
				synth.cancel()
			except Exception:
				pass

		self.EndModal(wx.ID_CANCEL)


# ─────────────────────────────────────────────────────────────────────────────
# Main Settings Panel (NVDA Settings → Auto TTS)
# ─────────────────────────────────────────────────────────────────────────────

class AutoTTSSettingsPanel(SettingsPanel):
	title = _("Auto TTS for NVDA")

	def makeSettings(self, settingsSizer):
		try:
			sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

			self._voiceListCache: Dict[str, List[Tuple[str, str]]] = {}
			self._availableSynths = _getInstalledSynths()

			# ─── General Settings ───
			self.enabledCheck = sHelper.addItem(
				wx.CheckBox(self, label=_("&Enable Automatic Language Switching"))
			)
			self.enabledCheck.SetValue(bool(sharedConfig.enabled))

			self.unicodeCheck = sHelper.addItem(
				wx.CheckBox(self, label=_("&Use Unicode-based language detection"))
			)
			self.unicodeCheck.SetValue(bool(sharedConfig.useUnicodeLanguageDetection))

			self.statisticalCheck = sHelper.addItem(
				wx.CheckBox(
					self,
					label=_("Smart same-&script language detection (bundled FastText, offline)"),
				)
			)
			self.statisticalCheck.SetValue(bool(sharedConfig.useStatisticalLanguageDetection))

			self.smartUrduCheck = sHelper.addItem(
				wx.CheckBox(self, label=_("Smart &Arabic/Urdu automatic separation (Quran/Tashkeel detection)"))
			)
			self.smartUrduCheck.SetValue(bool(sharedConfig.smartUrduArabic))

			self.protectMathCheck = sHelper.addItem(
				wx.CheckBox(self, label=_("&Protect math symbols and formulas from normal language switching"))
			)
			self.protectMathCheck.SetValue(bool(sharedConfig.protectMathSymbols))

			self._mathLanguageModes = list(MATH_LANGUAGE_MODES)
			for code, cfg in sharedConfig.languages.items():
				if cfg.enabled and code not in ("current", "default"):
					self._mathLanguageModes.append((code, _getLangName(code)))
			mathLabels = [m[1] for m in self._mathLanguageModes]
			self.mathLanguageChoice = sHelper.addLabeledControl(
				_("&Math reading language:"),
				wx.Choice,
				choices=mathLabels,
			)
			mathIdx = next((i for i, (code, desc) in enumerate(self._mathLanguageModes) if code == sharedConfig.mathLanguage), 0)
			self.mathLanguageChoice.SetSelection(mathIdx)

			tagLabels = [m[1] for m in TAG_MODES]
			self.tagModeChoice = sHelper.addLabeledControl(
				_("Document &language tags:"),
				wx.Choice,
				choices=tagLabels,
			)
			tagIdx = next((i for i, (code, desc) in enumerate(TAG_MODES) if code == sharedConfig.tagMode), 0)
			self.tagModeChoice.SetSelection(tagIdx)

			# Granularity Mode
			granularityLabels = [m[1] for m in GRANULARITY_MODES]
			self.granularityChoice = sHelper.addLabeledControl(
				_("Switching &granularity:"),
				wx.Choice,
				choices=granularityLabels
			)
			granIdx = next((i for i, (c, mDesc) in enumerate(GRANULARITY_MODES) if c == sharedConfig.granularityMode), 0)
			self.granularityChoice.SetSelection(granIdx)

			# Number Mode
			numberLabels = [m[1] for m in NUMBER_MODES]
			self.numberModeChoice = sHelper.addLabeledControl(
				_("&Numbers reading voice / language:"),
				wx.Choice,
				choices=numberLabels
			)
			numIdx = next((i for i, (c, modeDesc) in enumerate(NUMBER_MODES) if c == sharedConfig.numberMode), 0)
			self.numberModeChoice.SetSelection(numIdx)

			# App Exclusions Button
			self.appExclusionsBtn = sHelper.addItem(
				wx.Button(self, label=_("&Excluded Applications (Auto-Bypass)..."))
			)
			self.appExclusionsBtn.Bind(wx.EVT_BUTTON, self.onManageExclusions)

			# ─── Language Profiles ───
			sHelper.addItem(wx.StaticText(self, label=_("Configured Language Profiles:")))

			self.profileList = sHelper.addItem(
				wx.ListBox(self, size=(400, 150), style=wx.LB_SINGLE)
			)
			self.profileList.Bind(wx.EVT_LISTBOX, self.onProfileSelectionChanged)
			self.profileList.Bind(wx.EVT_LISTBOX_DCLICK, self.onEditProfile)

			# Buttons row
			btnSizer = wx.BoxSizer(wx.HORIZONTAL)

			self.addBtn = wx.Button(self, label=_("&Add Profile..."))
			self.addBtn.Bind(wx.EVT_BUTTON, self.onAddProfile)
			btnSizer.Add(self.addBtn, 0, wx.RIGHT, 4)

			self.editBtn = wx.Button(self, label=_("&Edit..."))
			self.editBtn.Bind(wx.EVT_BUTTON, self.onEditProfile)
			btnSizer.Add(self.editBtn, 0, wx.RIGHT, 4)

			self.removeBtn = wx.Button(self, label=_("&Remove"))
			self.removeBtn.Bind(wx.EVT_BUTTON, self.onRemoveProfile)
			btnSizer.Add(self.removeBtn, 0, wx.RIGHT, 4)

			self.setDefaultBtn = wx.Button(self, label=_("Set as &Default"))
			self.setDefaultBtn.Bind(wx.EVT_BUTTON, self.onSetDefault)
			btnSizer.Add(self.setDefaultBtn, 0, wx.RIGHT, 4)

			self.resetBtn = wx.Button(self, label=_("Reset A&ll"))
			self.resetBtn.Bind(wx.EVT_BUTTON, self.onResetAll)
			btnSizer.Add(self.resetBtn, 0)

			sHelper.addItem(btnSizer)

			# ─── Backup & Profile Pack Exchange ───
			sHelper.addItem(wx.StaticLine(self))
			backupSizer = wx.BoxSizer(wx.HORIZONTAL)

			self.exportBtn = wx.Button(self, label=_("E&xport Settings..."))
			self.exportBtn.Bind(wx.EVT_BUTTON, self.onExportSettings)
			backupSizer.Add(self.exportBtn, 0, wx.RIGHT, 6)

			self.importBtn = wx.Button(self, label=_("I&mport Settings..."))
			self.importBtn.Bind(wx.EVT_BUTTON, self.onImportSettings)
			backupSizer.Add(self.importBtn, 0)

			sHelper.addItem(backupSizer)

			# Initialize profile list & button states
			self._profileLangCodes: List[str] = []
			self._refreshProfileList()

		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error building settings panel: {e}")
			except Exception:
				pass

	def onManageExclusions(self, event):
		try:
			parentDlg = self.GetTopLevelParent() or self
			dlg = AppExclusionDialog(parentDlg)
			dlg.ShowModal()
			dlg.Destroy()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error managing exclusions: {e}")
			except Exception:
				pass

	def _refreshMathLanguageChoices(self):
		self._mathLanguageModes = list(MATH_LANGUAGE_MODES)
		for code, cfg in sharedConfig.languages.items():
			if cfg.enabled and code not in ("current", "default"):
				self._mathLanguageModes.append((code, _getLangName(code)))
		self.mathLanguageChoice.Clear()
		for code, label in self._mathLanguageModes:
			self.mathLanguageChoice.Append(label)
		idx = next((i for i, (code, label) in enumerate(self._mathLanguageModes) if code == sharedConfig.mathLanguage), 0)
		self.mathLanguageChoice.SetSelection(idx)

	def onExportSettings(self, event):
		try:
			parentDlg = self.GetTopLevelParent() or self
			with wx.FileDialog(
				parentDlg,
				_("Export Auto TTS Profile Pack"),
				wildcard="Auto TTS Profile Pack (*.autotts;*.json)|*.autotts;*.json",
				style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
			) as fileDialog:
				if fileDialog.ShowModal() == wx.ID_OK:
					path = fileDialog.GetPath()
					sharedConfig.exportConfig(path)
					wx.MessageBox(
						_("Auto TTS settings and profiles exported successfully."),
						_("Export Successful"),
						wx.OK | wx.ICON_INFORMATION,
						parent=parentDlg
					)
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error exporting settings: {e}")
			except Exception:
				pass

	def onImportSettings(self, event):
		try:
			parentDlg = self.GetTopLevelParent() or self
			with wx.FileDialog(
				parentDlg,
				_("Import Auto TTS Profile Pack"),
				wildcard="Auto TTS Profile Pack (*.autotts;*.json)|*.autotts;*.json",
				style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
			) as fileDialog:
				if fileDialog.ShowModal() == wx.ID_OK:
					path = fileDialog.GetPath()
					sharedConfig.importConfig(path)
					self._voiceListCache.clear()
					self._refreshProfileList()
					self._syncActiveSynth()

					# Update UI toggles
					self.enabledCheck.SetValue(bool(sharedConfig.enabled))
					self.unicodeCheck.SetValue(bool(sharedConfig.useUnicodeLanguageDetection))
					self.statisticalCheck.SetValue(bool(sharedConfig.useStatisticalLanguageDetection))
					self.smartUrduCheck.SetValue(bool(sharedConfig.smartUrduArabic))
					self.protectMathCheck.SetValue(bool(sharedConfig.protectMathSymbols))
					self._refreshMathLanguageChoices()
					tagIdx = next((i for i, (code, desc) in enumerate(TAG_MODES) if code == sharedConfig.tagMode), 0)
					self.tagModeChoice.SetSelection(tagIdx)

					numIdx = next((i for i, (c, mDesc) in enumerate(NUMBER_MODES) if c == sharedConfig.numberMode), 0)
					self.numberModeChoice.SetSelection(numIdx)

					granIdx = next((i for i, (c, mDesc) in enumerate(GRANULARITY_MODES) if c == sharedConfig.granularityMode), 0)
					self.granularityChoice.SetSelection(granIdx)

					wx.MessageBox(
						_("Auto TTS settings and profiles imported successfully."),
						_("Import Successful"),
						wx.OK | wx.ICON_INFORMATION,
						parent=parentDlg
					)
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error importing settings: {e}")
			except Exception:
				pass

	def onProfileSelectionChanged(self, event):
		self._updateButtonStates()

	def _updateButtonStates(self):
		try:
			selIdx = self.profileList.GetSelection()
			hasSel = (selIdx != wx.NOT_FOUND and 0 <= selIdx < len(self._profileLangCodes))

			self.editBtn.Enable(hasSel)
			self.removeBtn.Enable(hasSel)

			if hasSel:
				langCode = self._profileLangCodes[selIdx]
				self.setDefaultBtn.Enable(langCode != sharedConfig.defaultLang)
			else:
				self.setDefaultBtn.Enable(False)

			self.resetBtn.Enable(len(sharedConfig.languages) > 0)
		except Exception:
			pass

	def _refreshProfileList(self, selectLangCode: Optional[str] = None):
		self.profileList.Clear()
		self._profileLangCodes = []

		langCodes = sorted(
			sharedConfig.languages.keys(),
			key=lambda c: (0 if c == sharedConfig.defaultLang else 1, _getLangName(c).lower())
		)

		selIdxToSet = wx.NOT_FOUND
		for idx, langCode in enumerate(langCodes):
			langCfg = sharedConfig.languages[langCode]
			isDefault = (langCode == sharedConfig.defaultLang)
			if isDefault:
				prefix = _("[Default] ")
			elif not langCfg.enabled:
				prefix = _("[Disabled] ")
			else:
				prefix = "    "

			langName = _getLangName(langCode)
			synthName = self._getSynthDisplayName(langCfg.synth)
			voiceDisplay = self._getVoiceDisplayName(langCfg.voice, langCfg.synth)

			label = f"{prefix}{langName} -> {synthName} -> {voiceDisplay}"
			self.profileList.Append(label)
			self._profileLangCodes.append(langCode)

			if selectLangCode and langCode == selectLangCode:
				selIdxToSet = idx

		if selIdxToSet != wx.NOT_FOUND:
			self.profileList.SetSelection(selIdxToSet)
		elif self._profileLangCodes:
			self.profileList.SetSelection(0)
		else:
			self.profileList.SetSelection(wx.NOT_FOUND)

		self._updateButtonStates()

	def _getSynthDisplayName(self, synthId: str) -> str:
		if not synthId:
			return _("Default")
		for sId, sName in self._availableSynths:
			if sId.lower() == synthId.lower():
				return sName
		return synthId

	def _getVoiceDisplayName(self, voiceId: Optional[str], synthId: str = "") -> str:
		if not voiceId:
			return _("Default Voice")
		cacheKey = synthId or "__default__"
		if cacheKey in self._voiceListCache:
			for vId, vName in self._voiceListCache[cacheKey]:
				if str(vId).lower() == str(voiceId).lower():
					return vName
		s = str(voiceId)
		if len(s) > 40:
			return "..." + s[-37:]
		return s

	def onAddProfile(self, event):
		try:
			parentDlg = self.GetTopLevelParent() or self
			dlg = ProfileEditorDialog(
				parentDlg,
				langConfig=None,
				voiceListCache=self._voiceListCache,
				availableSynths=self._availableSynths
			)
			if dlg.ShowModal() == wx.ID_OK and dlg.result:
				cfg = dlg.result
				if cfg.lang in sharedConfig.languages:
					langName = _getLangName(cfg.lang)
					if wx.MessageBox(
						_("A profile for {lang} already exists. Do you want to overwrite it?").format(lang=langName),
						_("Profile Exists"),
						wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
						parent=parentDlg
					) != wx.YES:
						dlg.Destroy()
						return
				sharedConfig.setLanguageConfig(cfg)
				if len(sharedConfig.languages) == 1:
					sharedConfig.defaultLang = cfg.lang
					sharedConfig.save()
				self._syncActiveSynth()
				self._refreshProfileList(selectLangCode=cfg.lang)
			dlg.Destroy()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error adding profile: {e}")
			except Exception:
				pass

	def onEditProfile(self, event):
		try:
			selIdx = self.profileList.GetSelection()
			if selIdx < 0 or selIdx >= len(self._profileLangCodes):
				return
			langCode = self._profileLangCodes[selIdx]
			existingCfg = sharedConfig.getLanguageConfig(langCode)

			parentDlg = self.GetTopLevelParent() or self
			dlg = ProfileEditorDialog(
				parentDlg,
				langConfig=existingCfg,
				voiceListCache=self._voiceListCache,
				availableSynths=self._availableSynths
			)
			if dlg.ShowModal() == wx.ID_OK and dlg.result:
				sharedConfig.setLanguageConfig(dlg.result)
				self._syncActiveSynth()
				self._refreshProfileList(selectLangCode=langCode)
			dlg.Destroy()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error editing profile: {e}")
			except Exception:
				pass

	def onRemoveProfile(self, event):
		try:
			selIdx = self.profileList.GetSelection()
			if selIdx < 0 or selIdx >= len(self._profileLangCodes):
				return
			langCode = self._profileLangCodes[selIdx]

			if langCode == sharedConfig.defaultLang:
				parentDlg = self.GetTopLevelParent() or self
				wx.MessageBox(
					_("Cannot remove the default profile. Set another profile as default first."),
					_("Cannot Remove"),
					wx.OK | wx.ICON_WARNING,
					parent=parentDlg
				)
				return

			langName = _getLangName(langCode)
			parentDlg = self.GetTopLevelParent() or self
			if wx.MessageBox(
				_("Remove profile for {lang}?").format(lang=langName),
				_("Remove Profile"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
				parent=parentDlg
			) == wx.YES:
				sharedConfig.removeLanguageConfig(langCode)
				self._syncActiveSynth()
				self._refreshProfileList()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error removing profile: {e}")
			except Exception:
				pass

	def onSetDefault(self, event):
		try:
			selIdx = self.profileList.GetSelection()
			if selIdx < 0 or selIdx >= len(self._profileLangCodes):
				return
			langCode = self._profileLangCodes[selIdx]

			if langCode == sharedConfig.defaultLang:
				return

			sharedConfig.defaultLang = langCode
			sharedConfig.save()
			self._syncActiveSynth()
			self._refreshProfileList(selectLangCode=langCode)

			langName = _getLangName(langCode)
			try:
				speech.speak([_("{lang} is now the default language.").format(lang=langName)])
			except Exception:
				pass
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error setting default: {e}")
			except Exception:
				pass

	def onResetAll(self, event):
		try:
			parentDlg = self.GetTopLevelParent() or self
			dlg = wx.MessageDialog(
				parentDlg,
				_("Are you sure you want to reset ALL language profiles and settings to defaults?\n"
				  "This will remove all configured profiles."),
				_("Reset All Settings"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
			)
			if dlg.ShowModal() == wx.ID_YES:
				sharedConfig.languages.clear()
				sharedConfig.scriptMapping = dict(DEFAULT_SCRIPT_MAPPINGS)
				sharedConfig.numberMode = "current"
				sharedConfig.granularityMode = "word"
				sharedConfig.smartUrduArabic = True
				sharedConfig.protectMathSymbols = True
				sharedConfig.mathLanguage = "current"
				sharedConfig.tagMode = "override"
				sharedConfig.useUnicodeLanguageDetection = True
				sharedConfig.useStatisticalLanguageDetection = True
				try:
					sharedConfig.defaultLang = get_base_language(languageHandler.getLanguage())
				except Exception:
					sharedConfig.defaultLang = ""
				sharedConfig.enabled = True
				sharedConfig.excludedApps = list(DEFAULT_EXCLUDED_APPS)
				sharedConfig.lockedLanguage = None
				sharedConfig.save(allowEmptyProfiles=True)

				self._voiceListCache.clear()

				# Reload UI
				self.enabledCheck.SetValue(True)
				self.unicodeCheck.SetValue(True)
				self.statisticalCheck.SetValue(True)
				self.smartUrduCheck.SetValue(True)
				self.protectMathCheck.SetValue(True)
				self._refreshMathLanguageChoices()
				self.tagModeChoice.SetSelection(0)
				self.numberModeChoice.SetSelection(0)
				self.granularityChoice.SetSelection(0)
				self._refreshProfileList()
				self._syncActiveSynth()

				try:
					speech.speak([_("All Auto TTS settings have been reset to defaults.")])
				except Exception:
					pass
			dlg.Destroy()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error resetting: {e}")
			except Exception:
				pass

	def _syncActiveSynth(self):
		try:
			getSynth = getattr(synthDriverHandler, "getSynth", None)
			activeSynth = getSynth() if callable(getSynth) else getattr(synthDriverHandler, "synth", None)
			if activeSynth and getattr(activeSynth, "name", "") == "autoTTS":
				targetLang = sharedConfig.defaultLang
				if targetLang not in sharedConfig.languages and sharedConfig.languages:
					targetLang = next(iter(sharedConfig.languages))
				activeSynth._voice = targetLang or getattr(activeSynth, "_voice", "en")
				# Refresh NVDA's live ring so profile additions/removals appear without
				# switching synthesizers or restarting NVDA.
				synthDriverHandler.changeVoice(activeSynth, activeSynth._voice)
		except Exception:
			pass

	def onSave(self):
		try:
			sharedConfig.enabled = self.enabledCheck.GetValue()
			sharedConfig.useUnicodeLanguageDetection = self.unicodeCheck.GetValue()
			sharedConfig.useStatisticalLanguageDetection = self.statisticalCheck.GetValue()
			sharedConfig.smartUrduArabic = self.smartUrduCheck.GetValue()
			sharedConfig.protectMathSymbols = self.protectMathCheck.GetValue()

			mathIdx = self.mathLanguageChoice.GetSelection()
			if 0 <= mathIdx < len(self._mathLanguageModes):
				sharedConfig.mathLanguage = self._mathLanguageModes[mathIdx][0]

			tagIdx = self.tagModeChoice.GetSelection()
			if 0 <= tagIdx < len(TAG_MODES):
				sharedConfig.tagMode = TAG_MODES[tagIdx][0]

			numIdx = self.numberModeChoice.GetSelection()
			if 0 <= numIdx < len(NUMBER_MODES):
				sharedConfig.numberMode = NUMBER_MODES[numIdx][0]

			granIdx = self.granularityChoice.GetSelection()
			if 0 <= granIdx < len(GRANULARITY_MODES):
				sharedConfig.granularityMode = GRANULARITY_MODES[granIdx][0]

			sharedConfig.save()
			self._syncActiveSynth()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error saving settings: {e}")
			except Exception:
				pass
