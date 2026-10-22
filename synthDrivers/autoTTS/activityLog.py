# Auto TTS for NVDA - Continuous Activity Log & Diagnostics
# Covered by GNU General Public License (GPL)

import os
import sys
import threading
import time

try:
	import globalVars
except ImportError:
	class globalVars:
		class appArgs:
			secure = False
			configPath = ""

_MAX_BYTES = 20 * 1024 * 1024           # 20 MB normal log
_MAX_BYTES_DETAILED = 100 * 1024 * 1024  # 100 MB when 'include the spoken text' is on
_MAX_TEXT = 400

_lock = threading.Lock()
_path = None
_headerWritten = False
_building = False
_enabled = None
_includeText = None

FOLDER_NAME = "Auto TTS"
LOG_NAME = "Auto TTS log.txt"


def _documentsFolder():
	"""The user's real Documents folder (follows OneDrive redirection if active)."""
	try:
		import ctypes
		# FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
		guid = (ctypes.c_ubyte * 16)(
			0xD0, 0x9A, 0xD3, 0xFD, 0x8F, 0x23, 0xAF, 0x46,
			0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7
		)
		out = ctypes.c_wchar_p()
		if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
			path = out.value
			ctypes.windll.ole32.CoTaskMemFree(out)
			if path:
				return path
	except Exception:
		pass
	return os.path.join(os.path.expanduser("~"), "Documents")


def logFolder():
	bases = [
		_documentsFolder(),
		getattr(globalVars.appArgs, "configPath", None),
		os.environ.get("TEMP"),
	]
	for base in bases:
		if not base:
			continue
		folder = os.path.join(base, FOLDER_NAME)
		try:
			os.makedirs(folder, exist_ok=True)
			return folder
		except OSError:
			continue
	return None


def openFolder():
	"""Opens the log directory in Windows Explorer."""
	folder = logFolder()
	if folder and os.path.isdir(folder):
		try:
			os.startfile(folder)
			return True
		except Exception:
			pass
	return False


def _logPath():
	global _path
	if _path is None:
		folder = logFolder()
		_path = os.path.join(folder, LOG_NAME) if folder else None
	return _path


def isSecure():
	try:
		return bool(getattr(globalVars.appArgs, "secure", False))
	except Exception:
		return False


def isEnabled():
	global _enabled
	if isSecure():
		return False
	if _enabled is None:
		try:
			from .configManager import sharedConfig
			_enabled = getattr(sharedConfig, "loggingEnabled", True)
		except Exception:
			_enabled = True
	return _enabled


def setEnabled(value):
	global _enabled
	_enabled = bool(value)


def includeText():
	global _includeText
	if _includeText is None:
		try:
			from .configManager import sharedConfig
			_includeText = getattr(sharedConfig, "logIncludeText", False)
		except Exception:
			_includeText = False
	return _includeText


def setIncludeText(value):
	global _includeText
	_includeText = bool(value)


def _maxBytes():
	try:
		return _MAX_BYTES_DETAILED if includeText() else _MAX_BYTES
	except Exception:
		return _MAX_BYTES


def describeText(text):
	"""Anonymized description of text for privacy: character count, word count, scripts."""
	import re
	import unicodedata
	scripts = {}
	digits = punct = symbols = emoji = spaces = other = 0
	for ch in str(text):
		cat = unicodedata.category(ch)
		if ch.isspace():
			spaces += 1
		elif cat.startswith("L") or cat.startswith("M"):
			try:
				name = unicodedata.name(ch).split(" ")[0].lower()
			except ValueError:
				name = "unknown"
			scripts[name] = scripts.get(name, 0) + 1
		elif cat == "Nd":
			digits += 1
		elif cat.startswith("P"):
			punct += 1
		elif cat == "So" and (ord(ch) >= 0x2190 or ord(ch) >= 0x1F000):
			emoji += 1
		elif cat.startswith("S"):
			symbols += 1
		else:
			other += 1
	parts = [f"{len(str(text))} chars", f"{len(str(text).split())} words"]
	if scripts:
		parts.append("letters: " + ", ".join(f"{k} {v}" for k, v in sorted(scripts.items(), key=lambda kv: -kv[1])[:4]))
	if digits:
		runs = [len(m) for m in re.findall(r"\d+", str(text))]
		parts.append(f"digits {digits} in runs {runs[:6]}")
	if punct:
		parts.append(f"punctuation {punct}")
	if symbols:
		parts.append(f"symbols {symbols}")
	if emoji:
		parts.append(f"emoji {emoji}")
	return "<" + "; ".join(parts) + ">"


def clip(text):
	if not includeText():
		return describeText(text)
	s = repr(text)
	return s if len(s) <= _MAX_TEXT else s[:_MAX_TEXT] + f"...(+{len(s) - _MAX_TEXT} chars)"


def processMemoryMB():
	"""Working-set size of the NVDA process in MB."""
	try:
		import ctypes
		from ctypes import wintypes

		class PMC(ctypes.Structure):
			_fields_ = [
				("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
				("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
				("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
				("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
				("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)
			]

		pmc = PMC()
		pmc.cb = ctypes.sizeof(PMC)
		handle = ctypes.windll.kernel32.GetCurrentProcess()
		if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
			return round(pmc.WorkingSetSize / 1048576, 1)
	except Exception:
		pass
	return None


def _systemInfoLines():
	lines = []

	def add(label, getter):
		try:
			value = getter()
		except Exception as e:
			value = f"<unavailable: {e!r}>"
		lines.append(f"  {label}: {value}")

	import platform

	lines.append("--- Auto TTS Add-on ---")
	add("Add-on version", lambda: "1.0.3")
	add("Add-on folder", lambda: os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

	lines.append("--- NVDA Environment ---")
	def nvdaVersion():
		try:
			import buildVersion
			return f"{buildVersion.version} ({getattr(buildVersion, 'version_year', '?')}.{getattr(buildVersion, 'version_major', '?')})"
		except Exception:
			return "unknown"
	add("NVDA version", nvdaVersion)
	add("Python", lambda: f"{sys.version.split()[0]} {platform.architecture()[0]} ({'64' if sys.maxsize > 2**32 else '32'}-bit)")
	def nvdaLanguage():
		try:
			import languageHandler
			return f"NVDA UI language={languageHandler.getLanguage()} windows={languageHandler.getWindowsLanguage()}"
		except Exception:
			return "unknown"
	add("Language", nvdaLanguage)

	lines.append("--- Synthesizers ---")
	def synths():
		try:
			import synthDriverHandler
			curr = synthDriverHandler.getSynth()
			cName = curr.name if curr else None
			avail = ", ".join(i for i, _n in synthDriverHandler.getSynthList())
			return f"current={cName}; available={avail}"
		except Exception as e:
			return str(e)
	add("Synthesizers", synths)
	return lines


def _header():
	global _building
	lines = [
		"=" * 78,
		time.strftime("Auto TTS Activity Log -- session started %Y-%m-%d %H:%M:%S"),
		"This log describes speech routing, detected languages, and child synthesizers.",
		"Sensitive text is protected by default unless 'Include Spoken Text' is enabled.",
		"=" * 78,
	]
	_building = True
	try:
		lines.extend(_systemInfoLines())
	except Exception as e:
		lines.append(f"  <system information failed: {e!r}>")
	finally:
		_building = False
	lines.append("=" * 78)
	return "\n".join(lines) + "\n"


def _append(path, text):
	with open(path, "a", encoding="utf-8") as f:
		f.write(text)


def write(category, message):
	"""Writes a line to the activity log with timestamp and category."""
	global _headerWritten
	try:
		if _building or not isEnabled():
			return
		timestamp = time.strftime("%Y-%m-%d %H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
		threadName = threading.current_thread().name[:12]
		line = f"{timestamp} [{threadName}] {category:<8} {message}\n"
		with _lock:
			path = _logPath()
			if path is None:
				return
			try:
				if os.path.getsize(path) > _maxBytes():
					old = path[:-4] + " (previous).txt"
					if os.path.exists(old):
						os.remove(old)
					os.replace(path, old)
					_headerWritten = False
			except OSError:
				pass
			if not _headerWritten:
				_headerWritten = True
				_append(path, _header())
			_append(path, line)
	except Exception:
		pass


def writeException(category, message):
	"""Logs message plus the current exception's full traceback."""
	import traceback
	write(category, f"{message}\n{traceback.format_exc()}")


def describeSequence(seq):
	"""One-line summary of an NVDA speech sequence."""
	parts = []
	try:
		for item in seq:
			if isinstance(item, str):
				parts.append(clip(item))
			else:
				name = type(item).__name__
				if name == "LangChangeCommand":
					parts.append(f"<lang={getattr(item, 'lang', None)}>")
				elif name == "IndexCommand":
					parts.append(f"<idx={getattr(item, 'index', None)}>")
				elif name == "CharacterModeCommand":
					parts.append(f"<charMode={getattr(item, 'state', True)}>")
				else:
					parts.append(f"<{name}>")
	except Exception as e:
		parts.append(f"<describe failed: {e}>")
	return " ".join(parts)


def describeSynth(synth):
	"""Real child synth's current voice/variant/rate/pitch/volume."""
	out = []
	try:
		for attr in ("name", "voice", "variant", "rate", "pitch", "volume"):
			try:
				if hasattr(synth, attr):
					val = getattr(synth, attr)
					out.append(f"{attr}={val!r}")
			except Exception:
				pass
	except Exception:
		pass
	return " ".join(out)
