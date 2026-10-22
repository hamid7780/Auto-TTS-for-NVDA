# Auto TTS for NVDA - bundled offline fastText language identification
# Covered by GNU General Public License (GPL)

import os
import re
import sys
import threading
import functools
from collections import OrderedDict
from typing import Dict, Optional, Tuple

try:
	from logHandler import log
except ImportError:
	class log:
		@staticmethod
		def debug(message): pass
		@staticmethod
		def warning(message): pass

_ADDON_DIR = os.path.dirname(__file__)
_RUNTIME_DIR = os.path.join(_ADDON_DIR, "fasttext_runtime")
_MODEL_PATH = os.path.join(_ADDON_DIR, "models", "lid.176.ftz")
_LABEL_PREFIX = "__label__"
_model = None
_loadAttempted = False
_loadLock = threading.Lock()
_CACHE_LIMIT = 2048

# Script family hints to constrain candidate languages (Script-Gated Whitelist)
LANGUAGE_SCRIPT_HINTS = {
	"Arabic": {
		"ar", "azb", "bal", "ckb", "dv", "fa", "glk", "ks", "ku", "lrc",
		"mzn", "pa", "ps", "sd", "ug", "ur",
	},
	"Bengali": {"as", "bn"},
	"Cyrillic": {
		"ab", "av", "ba", "be", "bg", "ce", "cv", "kk", "ky", "mk", "mn",
		"os", "ru", "sah", "sr", "tg", "tt", "uk",
	},
	"Devanagari": {"bh", "bho", "doi", "hi", "mai", "mr", "ne", "sa"},
	"Ethiopic": {"am", "ti"},
	"Greek": {"el"},
	"Gurmukhi": {"pa"},
	"Han": {"ja", "wuu", "yue", "zh"},
	"Hebrew": {"he", "yi"},
	"Latin": {
		"af", "als", "an", "ast", "az", "bar", "bcl", "be-tarask", "bi", "br",
		"bs", "ca", "ceb", "co", "cs", "cy", "da", "de", "diq", "eml", "en",
		"eo", "es", "et", "eu", "fi", "fj", "fo", "fr", "frr", "fy", "ga",
		"gd", "gl", "gn", "gv", "hr", "ht", "hu", "ia", "id", "ie", "ilo",
		"io", "is", "it", "jbo", "jv", "kg", "la", "lb", "li", "lij", "lmo",
		"lt", "lv", "mg", "min", "ms", "mt", "nap", "nds", "nl", "nn", "no",
		"nrm", "oc", "om", "pam", "pl", "pms", "pt", "qu", "rm", "ro", "sc",
		"scn", "sco", "sk", "sl", "so", "sq", "su", "sv", "sw", "tl", "tr",
		"uz", "vec", "vi", "vo", "war", "wa", "xh", "yo", "zea", "zu",
	},
	"Tamil": {"ta"},
	"Telugu": {"te"},
	"Kannada": {"kn"},
	"Malayalam": {"ml"},
	"Gujarati": {"gu"},
}

_PROTECTED_RE = re.compile(
	r"(?:https?://|www\.|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|"
	r"(?:[A-Za-z]:\\|(?<!\w)/)[^\s]+|\b\w+\.(?:com|org|net|exe|dll|py|js|json|html)\b)",
	re.IGNORECASE,
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def languages_for_script(languageMap: Dict[str, str], script: str) -> Dict[str, str]:
	"""Return enabled model-language -> configured-profile mappings for script."""
	hints = LANGUAGE_SCRIPT_HINTS.get(script)
	if not hints:
		return {}
	return {
		base: profile
		for base, profile in languageMap.items()
		if base in hints
	}


def _load_model():
	global _model, _loadAttempted
	if _model is not None or _loadAttempted:
		return _model
	with _loadLock:
		if _model is not None or _loadAttempted:
			return _model
		_loadAttempted = True
		try:
			if os.path.isdir(_RUNTIME_DIR) and _RUNTIME_DIR not in sys.path:
				sys.path.insert(0, _RUNTIME_DIR)
			if os.path.isfile(_MODEL_PATH):
				import fasttext
				_model = fasttext.load_model(_MODEL_PATH)
				log.debug("AutoTTS: bundled fastText language model loaded successfully")
			else:
				log.warning("AutoTTS: fastText model file missing; using pure-Python heuristics")
		except Exception as error:
			# Pure-Python fallback ensures no crashes occur if fasttext native library fails to load
			log.warning(f"AutoTTS: fastText unavailable; fallback to pure-Python heuristics: {error}")
			_model = None
	return _model


def _prepare_text(text: str) -> Optional[Tuple[str, int]]:
	cleaned = " ".join(str(text).replace("\x00", " ").split())
	if not cleaned or _PROTECTED_RE.search(cleaned):
		return None
	words = _WORD_RE.findall(cleaned)
	letterCount = sum(len(word) for word in words)
	# Single characters or very short 1-word text (under 6 chars) should never be processed
	# by statistical ML to avoid voice thrashing during letter typing or spelling.
	if len(words) < 2 or letterCount < 6:
		return None
	return cleaned, len(words)


@functools.lru_cache(maxsize=2048)
def _predict_cached(
	cleaned: str,
	allowed_items: Tuple[Tuple[str, str], ...],
	wordCount: int,
	minimumConfidence: float,
	minimumMargin: float,
) -> Optional[str]:
	model = _load_model()
	if model is None:
		return None

	allowedLanguages = dict(allowed_items)
	try:
		labels, probabilities = model.predict(cleaned, k=2)
		if labels and probabilities:
			language = str(labels[0])
			if language.startswith(_LABEL_PREFIX):
				language = language[len(_LABEL_PREFIX):]
			language = language.lower()
			confidence = float(probabilities[0])
			second = float(probabilities[1]) if len(probabilities) > 1 else 0.0

			required = max(minimumConfidence, 0.78 if wordCount == 2 else minimumConfidence)
			if (
				language in allowedLanguages
				and confidence >= required
				and (confidence - second) >= minimumMargin
			):
				return allowedLanguages[language]
	except Exception as error:
		log.debug(f"AutoTTS: fastText prediction failed: {error}")
	return None


def detect_language(
	text: str,
	allowedLanguages: Dict[str, str],
	minimumConfidence: float = 0.65,
	minimumMargin: float = 0.12,
) -> Optional[str]:
	"""
	Return a configured profile tag, or None when statistical guess is unsafe or unavailable.
	Thread-safe with LRU caching up to 2048 items.
	"""
	prepared = _prepare_text(text)
	if not prepared or not allowedLanguages:
		return None
	cleaned, wordCount = prepared

	allowed_items = tuple(sorted(allowedLanguages.items()))
	return _predict_cached(cleaned, allowed_items, wordCount, minimumConfidence, minimumMargin)


def is_available() -> bool:
	"""Return whether the bundled runtime and model can be loaded."""
	return _load_model() is not None
