# Auto TTS for NVDA - Smart Voice Matching & Virtual Synth Filtering
# Covered by GNU General Public License (GPL)

from collections import OrderedDict
from typing import Optional, List, Tuple

VIRTUAL_SYNTHS = frozenset(("autotts", "nvdaallinone", "multilang", "silence", "autoTTS", "nvdaAllInOne", "MultiLang"))

# Some engines tag a language with different primary codes or dialect tags.
_ALIASES = {
	"bho": ("bho", "bh"),
	"zh": ("zh", "cmn", "yue", "yue-hk", "zho", "chinese"),
	"he": ("he", "iw", "heb", "hebrew"),
	"ja": ("ja", "jpn", "japanese"),
	"ko": ("ko", "kor", "korean"),
	"ur": ("ur", "urd", "urdu"),
	"ar": ("ar", "ara", "arabic"),
	"en": ("en", "eng", "enu", "english"),
	"hi": ("hi", "hin", "hindi"),
	"mr": ("mr", "mar", "marathi"),
	"bn": ("bn", "ben", "bengali"),
	"pa": ("pa", "pan", "punjabi"),
	"gu": ("gu", "guj", "gujarati"),
	"ta": ("ta", "tam", "tamil"),
	"te": ("te", "tel", "telugu"),
	"kn": ("kn", "kan", "kannada"),
	"ml": ("ml", "mal", "malayalam"),
	"as": ("as", "asm", "assamese"),
	"fa": ("fa", "fas", "per", "persian", "farsi"),
	"ps": ("ps", "pus", "pashto"),
	"es": ("es", "spa", "esp", "spanish"),
	"fr": ("fr", "fra", "fre", "french"),
	"de": ("de", "deu", "ger", "german"),
	"ru": ("ru", "rus", "russian"),
	"it": ("it", "ita", "italian"),
	"pt": ("pt", "por", "portuguese"),
	"tr": ("tr", "tur", "turkish"),
}

AUTO_SYNTH_ORDER = (
	"ibmeci",
	"vocalizer_expressive2",
	"googleTtsForNvda",
	"eloquence",
	"oneCore",
	"sapi5",
	"espeak",
)


def _accepted(langCode: Optional[str]) -> Tuple[str, ...]:
	lang = (langCode or "").strip().lower().replace("_", "-").split("-")[0]
	return _ALIASES.get(lang, (lang,)) if lang else ()


def _primary(code: Optional[str]) -> str:
	if not code:
		return ""
	cleaned = str(code).strip().lower().replace("_", "-")
	return cleaned.split("-")[0]


def synthSortKey(synthId: str, displayName: str = ""):
	"""Sorting order: prioritized TTS engines first, then NVDA natural order."""
	sId = (synthId or "").lower()
	for idx, name in enumerate(AUTO_SYNTH_ORDER):
		if sId == name.lower():
			return (idx, displayName.lower())
	return (len(AUTO_SYNTH_ORDER), displayName.lower())


def voiceMatchesLanguage(voiceId: str, info, langCode: str) -> Optional[bool]:
	"""
	Returns True if voice matches langCode, False if voice definitely belongs
	to a different language, or None if no language information is exposed.
	"""
	accepted = _accepted(langCode)
	if not accepted:
		return None

	# 1. Check VoiceInfo.language attribute
	voiceLang = getattr(info, "language", None)
	if voiceLang:
		primary = _primary(voiceLang)
		if primary in accepted:
			return True

	# 2. Check voice ID (e.g. Eloquence "enu", "eng", eSpeak "en", OneCore "en-US")
	if voiceId:
		vidLower = str(voiceId).lower()
		vidPrimary = _primary(vidLower)
		if vidPrimary in accepted:
			return True
		for alias in accepted:
			if vidLower == alias or vidLower.startswith(f"{alias}_") or vidLower.startswith(f"{alias}-"):
				return True
			if f"_{alias}" in vidLower or f"-{alias}" in vidLower:
				return True

	# 3. Check display name
	dispName = getattr(info, "displayName", None) or getattr(info, "name", "")
	if dispName:
		dLower = str(dispName).lower()
		for alias in accepted:
			if f"({alias})" in dLower or f"[{alias}]" in dLower:
				return True
			if len(alias) >= 3 and alias in dLower:
				return True

	return False if voiceLang else None


def voicesForLanguage(synth, langCode: str) -> List[Tuple[str, object]]:
	"""
	Returns [(voiceId, VoiceInfo)] matching langCode on synth.
	If the synth exposes no language info or none match, returns all voices.
	"""
	try:
		avail = getattr(synth, "availableVoices", {})
		allVoices = list(avail.items()) if isinstance(avail, dict) else []
	except Exception:
		return []

	if not allVoices:
		return []

	matching = [(vid, info) for vid, info in allVoices if voiceMatchesLanguage(vid, info, langCode)]
	return matching if matching else allVoices


def hasMatchingVoice(synth, langCode: str) -> bool:
	try:
		avail = getattr(synth, "availableVoices", {})
		if not avail or not isinstance(avail, dict):
			return False
		return any(voiceMatchesLanguage(vid, info, langCode) for vid, info in avail.items())
	except Exception:
		return False


def defaultVoiceFor(synth, langCode: str, preferred: Optional[str] = None) -> Optional[str]:
	"""
	Resolves the best default voice for a language on a synth:
	preferred -> first matching voice -> current voice -> first available voice.
	"""
	candidates = voicesForLanguage(synth, langCode)
	if not candidates:
		return None
	cMap = dict(candidates)
	if hasMatchingVoice(synth, langCode):
		if preferred and preferred in cMap:
			return preferred
		return candidates[0][0]
	try:
		current = getattr(synth, "voice", None)
		if current and current in cMap:
			return current
	except Exception:
		pass
	return candidates[0][0]


def usableVoice(synth, storedVoice: Optional[str], langCode: str, preferred: Optional[str] = None) -> Optional[str]:
	"""
	Returns storedVoice if valid and exists on synth; otherwise resolves defaultVoiceFor.
	"""
	avail = getattr(synth, "availableVoices", {})
	if storedVoice and storedVoice in avail:
		return storedVoice
	return defaultVoiceFor(synth, langCode, preferred)


def variantsForVoice(synth, voiceId: Optional[str]):
	"""
	Returns available variants for voiceId. Handles synths like Google TTS
	where availableVariants depends on the active voice.
	"""
	from . import voiceLabels
	if not getattr(synth, "isSupported", lambda s: False)("variant"):
		return OrderedDict()

	savedVoice = None
	savedVariant = None
	try:
		savedVoice = getattr(synth, "voice", None)
		savedVariant = getattr(synth, "variant", None)
	except Exception:
		pass

	try:
		if voiceId and savedVoice != voiceId and hasattr(synth, "voice"):
			synth.voice = voiceId
		return voiceLabels.labelledVariants(synth)
	finally:
		if savedVoice is not None and savedVoice != voiceId and hasattr(synth, "voice"):
			try:
				synth.voice = savedVoice
				if savedVariant is not None and hasattr(synth, "variant"):
					synth.variant = savedVariant
			except Exception:
				pass
