# Auto TTS for NVDA - bundled offline fastText language identification
# Covered by GNU General Public License (GPL)

import os
import re
import sys
import threading
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
_cache = OrderedDict()
_CACHE_LIMIT = 512

# These are intentionally broad script families, not a claim that every
# language is written exclusively in the listed script.  They only decide
# whether statistical detection is useful for a piece of already segmented
# text.  The model still makes the actual language decision.
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
}

# A bare "/" only starts a protected path when it is not inside a word, so
# ordinary text such as "and/or" or "km/h" is still language-detected.
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
			if _RUNTIME_DIR not in sys.path:
				sys.path.insert(0, _RUNTIME_DIR)
			import fasttext
			_model = fasttext.load_model(_MODEL_PATH)
			log.debug("AutoTTS: bundled fastText language model loaded")
		except Exception as error:
			# Detection is an enhancement.  A missing/incompatible binary must never
			# stop speech; Unicode and document-tag detection remain available.
			log.warning(f"AutoTTS: fastText unavailable; using Unicode detection: {error}")
	return _model


def _prepare_text(text: str) -> Optional[Tuple[str, int]]:
	cleaned = " ".join(str(text).replace("\x00", " ").split())
	if not cleaned or _PROTECTED_RE.search(cleaned):
		return None
	words = _WORD_RE.findall(cleaned)
	letterCount = sum(len(word) for word in words)
	# One-word language guesses are the main cause of voice thrashing.  Clear
	# cross-script single words are already handled without this model.
	if len(words) < 2 or letterCount < 6:
		return None
	return cleaned, len(words)


def detect_language(
	text: str,
	allowedLanguages: Dict[str, str],
	minimumConfidence: float = 0.65,
	minimumMargin: float = 0.12,
) -> Optional[str]:
	"""
	Return a configured profile tag, or None when the guess is unsafe.

	Only the model's overall top result is accepted.  We never select a weak
	lower-ranked prediction merely because it happens to have a profile.
	"""
	prepared = _prepare_text(text)
	if not prepared or not allowedLanguages:
		return None
	cleaned, wordCount = prepared
	cacheKey = (cleaned, tuple(sorted(allowedLanguages.items())), minimumConfidence, minimumMargin)
	if cacheKey in _cache:
		_cache.move_to_end(cacheKey)
		return _cache[cacheKey]

	model = _load_model()
	result = None
	if model is not None:
		try:
			labels, probabilities = model.predict(cleaned, k=2)
			if labels and probabilities:
				language = str(labels[0])
				if language.startswith(_LABEL_PREFIX):
					language = language[len(_LABEL_PREFIX):]
				language = language.lower()
				confidence = float(probabilities[0])
				second = float(probabilities[1]) if len(probabilities) > 1 else 0.0
				# Two-word samples need stronger evidence than normal phrases.
				required = max(minimumConfidence, 0.78 if wordCount == 2 else minimumConfidence)
				if (
					language in allowedLanguages
					and confidence >= required
					and confidence - second >= minimumMargin
				):
					result = allowedLanguages[language]
		except Exception as error:
			log.debug(f"AutoTTS: fastText prediction failed: {error}")

	_cache[cacheKey] = result
	_cache.move_to_end(cacheKey)
	while len(_cache) > _CACHE_LIMIT:
		_cache.popitem(last=False)
	return result


def is_available() -> bool:
	"""Return whether the bundled runtime and model can be loaded."""
	return _load_model() is not None
