# Auto TTS for NVDA - Clean Voice & Variant Labels
# Covered by GNU General Public License (GPL)

import re
from collections import OrderedDict

try:
	import languageHandler
	from synthDriverHandler import VoiceInfo
except ImportError:
	class languageHandler:
		@staticmethod
		def getLanguageDescription(code):
			return code
	class VoiceInfo:
		def __init__(self, id, displayName, language=None):
			self.id = id
			self.displayName = displayName
			self.language = language

_TRAILING_NUMBER = re.compile(r"(\d+)(?:\s*\([^)]*\))?\s*$")


def _englishLanguageName(code):
	try:
		return languageHandler.getLanguageDescription(str(code).replace("-", "_")) or code
	except Exception:
		return code


def _googleLabel(synth, variantId, info):
	speaker = synth.catalog.speaker_for_voice(variantId)
	kind = "Google Natural" if "seanet" in getattr(speaker, "packageId", "").lower() else "Chrome OS"
	parts = [kind]
	if getattr(speaker, "gender", None):
		parts.append(speaker.gender)
	speakerName = getattr(speaker, "name", "")
	match = _TRAILING_NUMBER.search(speakerName)
	if match:
		parts.append(f"voice {match.group(1)}")
	parts.append(_englishLanguageName(getattr(speaker, "language", "")))
	return ", ".join(parts)


_LABELLERS = {
	"googlettsfornvda": _googleLabel,
	"googleTtsForNvda": _googleLabel,
}


def labelledVariants(synth):
	"""
	Returns synth.availableVariants with English prefix descriptions where known.
	"""
	variants = getattr(synth, "availableVariants", OrderedDict())
	if not variants:
		return OrderedDict()

	synthName = getattr(synth, "name", "")
	labeller = _LABELLERS.get(synthName)
	if labeller is None:
		return variants

	out = OrderedDict()
	for variantId, info in variants.items():
		try:
			label = labeller(synth, variantId, info)
			out[variantId] = VoiceInfo(
				info.id,
				f"{label}: {info.displayName}",
				getattr(info, "language", None)
			)
		except Exception:
			out[variantId] = info
	return out
