# Auto TTS for NVDA - Global Plugin
# Covered by GNU General Public License (GPL)

try:
	import wx
	import gui
	from gui.settingsDialogs import NVDASettingsDialog
	import globalPluginHandler
	from scriptHandler import script
	import ui
	import addonHandler
	import languageHandler
	import synthDriverHandler
	from logHandler import log
	addonHandler.initTranslation()
except ImportError:
	class globalPluginHandler:
		class GlobalPlugin:
			def __init__(self): pass
			def terminate(self): pass
	def script(*args, **kwargs):
		def decorator(func): return func
		return decorator
	def _(s): return s
	class log:
		@staticmethod
		def exception(msg): pass

from .settingsPanel import AutoTTSSettingsPanel, _getLangName
from synthDrivers.autoTTS.configManager import sharedConfig


class LanguageLockDialog(wx.SingleChoiceDialog):
	"""Accessible dialog for quickly locking Auto TTS to a specific language profile."""

	def __init__(self, parent, choices, clientData, currentSelection=0):
		super().__init__(
			parent,
			_("Select a language profile to lock Auto TTS into.\n"
			  "All text will be read with this voice until you press NVDA+Alt+L again:"),
			_("Lock Auto TTS Language"),
			choices,
		)
		self.clientData = clientData
		if 0 <= currentSelection < len(choices):
			self.SetSelection(currentSelection)
		self.CentreOnScreen()

	def getSelectedLangCode(self) -> str:
		idx = self.GetSelection()
		if 0 <= idx < len(self.clientData):
			return self.clientData[idx]
		return "en"


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""
	Global plugin for Auto TTS for NVDA.
	Provides settings category registration, customizable input gestures under 'Auto TTS' category,
	quick settings shortcut (NVDA+Alt+A), language lock (NVDA+Alt+L), toggle (NVDA+Shift+L),
	and first-run onboarding prompt.
	"""

	scriptCategory = _("Auto TTS")

	def __init__(self):
		super().__init__()
		# Register Settings Panel Category in NVDA Settings Dialog (NVDA+Ctrl+G)
		try:
			if AutoTTSSettingsPanel not in NVDASettingsDialog.categoryClasses:
				NVDASettingsDialog.categoryClasses.append(AutoTTSSettingsPanel)
		except Exception:
			pass

		# First run onboarding prompt
		if getattr(sharedConfig, "firstRun", False):
			sharedConfig.firstRun = False
			sharedConfig.save()
			try:
				wx.CallAfter(self._showFirstRunPrompt)
			except Exception:
				pass

		# Let NVDA finish startup, then prepare configured asynchronous runtimes.
		# This removes the first multi-second gap when switching from a local English
		# synth to Google TTS without starting any speech or changing the active voice.
		try:
			wx.CallLater(750, self._prewarmActiveAutoTTS)
		except Exception:
			pass

	def terminate(self):
		"""Cleans up settings category when add-on is unloaded or reloaded."""
		try:
			if AutoTTSSettingsPanel in NVDASettingsDialog.categoryClasses:
				NVDASettingsDialog.categoryClasses.remove(AutoTTSSettingsPanel)
		except Exception:
			pass
		super().terminate()

	def _prewarmActiveAutoTTS(self):
		try:
			synth = synthDriverHandler.getSynth()
			if getattr(synth, "name", "") == "autoTTS":
				synth._prewarmConfiguredHighLatencySynths()
		except Exception:
			pass

	def _showFirstRunPrompt(self):
		"""Presents a first-run prompt asking user if they want to configure Auto TTS now."""
		try:
			mainFrame = getattr(gui, "mainFrame", None)
			if wx.MessageBox(
				_("Welcome to Auto TTS for NVDA!\n\n"
				  "Would you like to open Auto TTS settings now to configure your language profiles and synthesizers?"),
				_("Auto TTS Setup"),
				wx.YES_NO | wx.ICON_QUESTION,
				parent=mainFrame
			) == wx.YES:
				wx.CallAfter(self._openSettings)
		except Exception:
			pass

	def _openSettings(self):
		"""Opens the NVDA Settings dialog directly focused on the Auto TTS category."""
		try:
			import gui
			from gui.settingsDialogs import NVDASettingsDialog
			mainFrame = getattr(gui, "mainFrame", None)
			if mainFrame:
				gui.mainFrame.popupSettingsDialog(NVDASettingsDialog, initialCategory=AutoTTSSettingsPanel)
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error opening settings panel: {e}")
			except Exception:
				pass

	@script(
		gesture="kb:NVDA+alt+a",
		description=_("Opens the Auto TTS settings dialog directly"),
		category=_("Auto TTS")
	)
	def script_openAutoTTSSettings(self, gesture):
		"""Opens NVDA Settings directly at the Auto TTS category."""
		wx.CallAfter(self._openSettings)

	@script(
		gesture="kb:NVDA+shift+l",
		description=_("Toggles Auto TTS automatic language switching on and off"),
		category=_("Auto TTS")
	)
	def script_toggleAutoTTS(self, gesture):
		"""Toggles automatic language switching and announces new state."""
		sharedConfig.enabled = not sharedConfig.enabled
		sharedConfig.save()
		msg = _("Auto TTS enabled") if sharedConfig.enabled else _("Auto TTS disabled")
		try:
			ui.message(msg)
		except Exception:
			pass

	def _openLanguageLockDialog(self):
		"""Opens the Language Lock dialog asynchronously without blocking NVDA input loop."""
		try:
			allCodes = []
			defLang = sharedConfig.defaultLang
			if defLang and defLang in sharedConfig.languages and sharedConfig.languages[defLang].enabled:
				allCodes.append(defLang)
			for code in sharedConfig.languages.keys():
				if sharedConfig.languages[code].enabled and code != defLang and code not in allCodes:
					allCodes.append(code)
			if not allCodes:
				ui.message(_("No enabled Auto TTS language profiles are configured."))
				return

			choices = [f"{_getLangName(code)} ({code})" for code in allCodes]

			mainFrame = getattr(gui, "mainFrame", None)
			if mainFrame and hasattr(gui.mainFrame, "prePopup"):
				gui.mainFrame.prePopup()
			dlg = LanguageLockDialog(mainFrame, choices, allCodes, currentSelection=0)
			try:
				if dlg.ShowModal() == wx.ID_OK:
					selectedCode = dlg.getSelectedLangCode()
					sharedConfig.lockedLanguage = selectedCode
					langName = _getLangName(selectedCode)
					ui.message(_("Locked to {lang}. Press NVDA+Alt+L again to unlock.").format(lang=langName))
			finally:
				dlg.Destroy()
				if mainFrame and hasattr(gui.mainFrame, "postPopup"):
					gui.mainFrame.postPopup()
		except Exception as e:
			try:
				log.exception(f"AutoTTS: Error opening language lock dialog: {e}")
				ui.message(_("Error opening language lock dialog."))
			except Exception:
				pass

	@script(
		gesture="kb:NVDA+alt+l",
		description=_("Locks Auto TTS to a single language profile or unlocks it"),
		category=_("Auto TTS")
	)
	def script_toggleLanguageLock(self, gesture):
		"""If locked, unlocks Auto TTS; if unlocked, opens profile lock dialog."""
		if sharedConfig.lockedLanguage:
			lockedWas = sharedConfig.lockedLanguage
			sharedConfig.lockedLanguage = None
			langName = _getLangName(lockedWas)
			msg = _("Language lock disabled. Automatic switching resumed.")
			try:
				ui.message(msg)
			except Exception:
				pass
			return

		# Must use wx.CallAfter to prevent blocking the NVDA main script thread
		wx.CallAfter(self._openLanguageLockDialog)

	@script(
		gesture="kb:NVDA+control+t",
		description=_("Announces Auto TTS status and active language lock"),
		category=_("Auto TTS")
	)
	def script_announceAutoTTSStatus(self, gesture):
		"""Speaks whether Auto TTS is enabled and whether language lock is active."""
		status = _("Enabled") if sharedConfig.enabled else _("Disabled")
		lockInfo = ""
		if sharedConfig.lockedLanguage:
			lockInfo = _(" Locked to {lang}.").format(lang=_getLangName(sharedConfig.lockedLanguage))

		msg = _("Auto TTS for NVDA: {status}.{lockInfo}").format(
			status=status,
			lockInfo=lockInfo
		)
		try:
			ui.message(msg)
		except Exception:
			pass
