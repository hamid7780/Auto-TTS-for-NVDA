# Auto TTS for NVDA - Smart Language Detection Engine
# Covered by GNU General Public License (GPL)

import functools
import re
import unicodedata
from typing import Dict, Optional, Tuple

try:
	from speech.commands import LangChangeCommand, IndexCommand, CharacterModeCommand
except ImportError:
	class LangChangeCommand:
		def __init__(self, lang):
			self.lang = lang
		def __repr__(self):
			return f"LangChangeCommand({self.lang!r})"
		def __eq__(self, other):
			return isinstance(other, LangChangeCommand) and self.lang == other.lang
	class IndexCommand:
		def __init__(self, index):
			self.index = index
		def __repr__(self):
			return f"IndexCommand({self.index!r})"
	class CharacterModeCommand:
		def __init__(self, state=True):
			self.state = state
		def __repr__(self):
			return f"CharacterModeCommand({self.state!r})"

from .scripts import get_script
from . import statisticalDetection
from . import persoArabicLid
from . import devanagariGroupLid
from . import sharedScriptLid
from . import numberProcessing

# Set of Urdu and Persian exclusive characters that never appear in standard Arabic text
URDU_EXCLUSIVE_CHARS = frozenset({
	0x0679,  # ٹ (TTeh)
	0x0688,  # ڈ (DDal)
	0x0691,  # ڑ (RReh)
	0x06BA,  # ں (Noon Ghunna)
	0x06C1,  # ہ (Heh Goal)
	0x06C2,  # ۂ (Heh Goal with Hamza Above)
	0x06C3,  # ۃ (Teh Marbuta Goal)
	0x06BE,  # ھ (Heh Doachashmee)
	0x06D2,  # ے (Yeh Barree)
	0x06D3,  # ۓ (Yeh Barree with Hamza)
	0x067E,  # پ (Peh)
	0x0686,  # چ (Tcheh)
	0x06AF,  # گ (Gaf)
	0x0698,  # ژ (Zheh)
	0x06CC,  # ی (Farsi/Urdu Yeh)
	0x06A9,  # ک (Keheh / Urdu Kaf)
	0x0658,  # ٘ (Noon Ghunna Mark)
	0x0657,  # ٗ (Inverted Damma / Ulta Pesh)
	0x06D4,  # ۔ (Urdu Full Stop)
	0x067B,  # ٻ
	0x0680,  # ڀ
	0x0683,  # ٺ
	0x0684,  # ٽ
	0x0687,  # ڇ
	0x068A,  # ڌ
	0x068D,  # ڍ
	0x068F,  # ڎ
	0x0699,  # ڙ
	0x06A6,  # ڦ
	0x06AA,  # ګ
	0x06AB,  # ڳ
	0x06B1,  # ڱ
	0x06B3,  # ڳ
	0x06BB,  # ڻ
	0x06BC,  # ݨ
})

# Arabic-exclusive characters
ARABIC_EXCLUSIVE_CHARS = frozenset({
	0x0629,  # ة (Teh Marbuta - standard Arabic)
	0x064A,  # ي (Arabic Yeh with two dots below)
	0x0643,  # ك (Arabic Kaf with mini-kaf inside)
	0x0649,  # ى (Alef Maksura)
})

# Arabic Tashkeel, Harakat, and Quranic recitation marks
ARABIC_TASHKEEL_CHARS = frozenset({
	0x064B,  # ً (Fathatan / Do Zabar)
	0x064C,  # ٌ (Dammatan / Do Pesh)
	0x064D,  # ٍ (Kasratan / Do Zer)
	0x064E,  # َ (Fatha / Zabar)
	0x064F,  # ُ (Damma / Pesh)
	0x0650,  # ِ (Kasra / Zer)
	0x0651,  # ّ (Shadda / Tashdeed)
	0x0652,  # ْ (Sukun / Jazam)
	0x0670,  # ٰ (Superscript Alef / Khari Zabar)
	0x0653,  # ٓ (Maddah Above)
	0x0654,  # ٔ (Hamza Above)
	0x0655,  # ٕ (Hamza Below)
	*range(0x06D6, 0x06EE),
	*range(0xFE70, 0xFE75),
})

QURANIC_MARKS = frozenset(range(0x06D6, 0x06EE))

# Eastern Arabic and Arabic-Indic digit codepoints
EASTERN_ARABIC_DIGIT_RANGE = range(0x06F0, 0x06FA)  # ۰۱۲۳۴۵۶۷۸۹
ARABIC_INDIC_DIGIT_RANGE = range(0x0660, 0x066A)    # ٠١٢٣٤٥٦٧٨٩
ALL_ARABIC_DIGITS = frozenset(EASTERN_ARABIC_DIGIT_RANGE) | frozenset(ARABIC_INDIC_DIGIT_RANGE)

DEVANAGARI_DIGITS = frozenset(range(0x0966, 0x0970))  # ०१२३४५६७८९
BENGALI_DIGITS = frozenset(range(0x09E6, 0x09F0))     # ০১২৩৪৫৬৭৮৯

# Greek alphabet codepoints (used in math variables and formulas)
GREEK_LETTERS = frozenset(range(0x0370, 0x03FF)) | frozenset(range(0x1F00, 0x2000)) | frozenset(range(0x1D6A8, 0x1D7CC))
MATH_SYMBOLS = frozenset("+-−*/×÷=<>≤≥≈≠±√∞∑∏∫∂∆∇^‰%")

# Recognized Arabic-script based languages
ARABIC_SCRIPT_LANGS = frozenset({"ur", "ar", "fa", "ps", "sd", "ug", "ckb", "ks"})

# ISO 639-3 to 639-1 mappings
ISO_639_3_TO_2: Dict[str, str] = {
	"eng": "en", "urd": "ur", "ara": "ar", "hin": "hi", "fas": "fa",
	"per": "fa", "pus": "ps", "fra": "fr", "fre": "fr", "deu": "de",
	"ger": "de", "spa": "es", "ita": "it", "por": "pt", "rus": "ru",
	"zho": "zh", "chi": "zh", "jpn": "ja", "kor": "ko", "tur": "tr",
	"vie": "vi", "tam": "ta", "tel": "te", "pan": "pa", "guj": "gu",
	"kan": "kn", "mal": "ml", "ben": "bn", "sin": "si", "tha": "th",
	"mya": "my", "heb": "he", "ell": "el", "gre": "el", "swe": "sv",
	"nld": "nl", "dut": "nl", "pol": "pl", "ukr": "uk", "ron": "ro",
	"rum": "ro", "ces": "cs", "cze": "cs", "hun": "hu", "dan": "da",
	"fin": "fi", "nor": "no", "ind": "id", "msa": "ms", "may": "ms",
	"snd": "sd", "aze": "az", "bul": "bg", "cat": "ca", "hrv": "hr",
	"kat": "ka", "lav": "lv", "lit": "lt", "nep": "ne", "srp": "sr",
	"slk": "sk", "slv": "sl", "swa": "sw",
}

DEFAULT_SCRIPT_MAPPINGS: Dict[str, str] = {
	"Latin": "en",
	"Cyrillic": "ru",
	"Arabic": "ur",
	"Devanagari": "hi",
	"Han": "zh",
	"Hiragana": "ja",
	"Katakana": "ja",
	"Hangul": "ko",
	"Hebrew": "he",
	"Bengali": "bn",
	"Gurmukhi": "pa",
	"Greek": "el",
	"Gujarati": "gu",
	"Oriya": "or",
	"Tamil": "ta",
	"Telugu": "te",
	"Kannada": "kn",
	"Malayalam": "ml",
	"Sinhala": "si",
	"Thai": "th",
	"Lao": "lo",
	"Tibetan": "bo",
	"Georgian": "ka",
	"Mongolian": "mn",
	"Khmer": "km",
	"Armenian": "hy",
	"Myanmar": "my",
	"Ethiopic": "am",
	"Thaana": "dv",
	"Bopomofo": "zh",
}


@functools.lru_cache(maxsize=2048)
def normalize_language_code(lang: Optional[str]) -> Tuple[str, str]:
	"""Normalizes any language code into (normalized_full_tag, base_lang_code). Cached."""
	if not lang:
		return ("en", "en")

	cleaned = str(lang).strip().lower().replace("_", "-")
	parts = cleaned.split("-")
	primary = parts[0]

	if primary in ISO_639_3_TO_2:
		primary = ISO_639_3_TO_2[primary]
		parts[0] = primary

	normalized_full = "-".join(parts)
	base_lang = primary
	return (normalized_full, base_lang)


@functools.lru_cache(maxsize=2048)
def get_base_language(lang: Optional[str]) -> str:
	"""Returns 2-letter base language code for any dialect tag. Cached."""
	return normalize_language_code(lang)[1]


@functools.lru_cache(maxsize=2048)
def classify_arabic_segment(text: str, default_lang: str = "ur", current_lang: Optional[str] = None) -> str:
	"""
	Accurately classifies Arabic-script text as Urdu or Arabic with zero GIL latency via LRU cache.
	Checks Quranic marks -> Urdu letter forms -> Arabic exclusive letters -> Tashkeel density.
	"""
	if not text:
		return default_lang or "ur"

	has_urdu = any(ord(c) in URDU_EXCLUSIVE_CHARS for c in text)
	has_arabic_exclusive = any(ord(c) in ARABIC_EXCLUSIVE_CHARS for c in text)
	has_quranic = any(ord(c) in QURANIC_MARKS for c in text)

	if has_quranic:
		return "ar"
	if has_urdu and not has_arabic_exclusive:
		return "ur"
	if has_arabic_exclusive and not has_urdu:
		return "ar"

	tashkeel_count = sum(1 for c in text if ord(c) in ARABIC_TASHKEEL_CHARS)
	letter_count = sum(1 for c in text if ord(c) not in ARABIC_TASHKEEL_CHARS and not c.isspace())

	if tashkeel_count > 0:
		is_tanween_word = (tashkeel_count == 1 and any(ord(c) == 0x064B for c in text))
		is_single_vowel = (tashkeel_count == 1 and letter_count >= 2)

		if (is_tanween_word or is_single_vowel) and not has_arabic_exclusive:
			target = default_lang if default_lang in ARABIC_SCRIPT_LANGS else "ur"
			return target

		if letter_count > 0 and (tashkeel_count >= 3 or (tashkeel_count / letter_count) >= 0.35):
			return "ar"

	if has_urdu:
		return "ur"
	if has_arabic_exclusive:
		return "ar"

	if current_lang and current_lang in ARABIC_SCRIPT_LANGS:
		return current_lang
	if default_lang and default_lang in ARABIC_SCRIPT_LANGS:
		return default_lang
	return "ur"


@functools.lru_cache(maxsize=2048)
def get_char_type(c: str, protect_math: bool = True) -> str:
	"""Determines script / category for a single character with math variable protection. Cached."""
	category = unicodedata.category(c)
	cp = ord(c)
	if category.startswith("M") or unicodedata.combining(c) > 0:
		return "mark"
	if category.startswith("N"):
		return "number"
	if category.startswith("Z"):
		return "space"
	if protect_math and (cp in GREEK_LETTERS or c in MATH_SYMBOLS):
		return "math"
	if category.startswith("P") or category.startswith("S"):
		return "punct"
	return get_script(cp)


def _single_text_script(text: str, protect_math: bool = True) -> Optional[str]:
	"""Return the sole writing script in text, ignoring neutral characters."""
	scripts = set()
	for character in text:
		charType = get_char_type(character, protect_math=protect_math)
		if charType in ("mark", "number", "space", "punct", "math", "Common", "Inherited"):
			continue
		scripts.add(charType)
		if len(scripts) > 1:
			return None
	return next(iter(scripts), None)


def _disambiguate_shared_script(
	text: str,
	script: str,
	candidates: Dict[str, str],
	default_lang: str,
) -> Optional[str]:
	"""
	Script-gated character heuristics & n-gram disambiguation for shared scripts
	(Perso-Arabic, Devanagari, Bengali).
	"""
	enabled_codes = set(candidates.keys())

	# 1. Perso-Arabic (Urdu, Arabic, Persian, Sindhi)
	if script == "Arabic":
		# First check Urdu-exclusive characters
		if any(ord(c) in URDU_EXCLUSIVE_CHARS for c in text):
			if "ur" in candidates:
				return candidates["ur"]
		# Check Bengali-style Assamese / Arabic letters via persoArabicLid
		res = persoArabicLid.classify(text)
		if res and res in candidates:
			return candidates[res]
		resolved = sharedScriptLid.resolve_segment(text, "Arabic", enabled_codes)
		if resolved and resolved in candidates:
			return candidates[resolved]
		return candidates.get("ur", candidates.get("ar", default_lang))

	# 2. Devanagari (Hindi, Marathi, Nepali, Bhojpuri, etc.)
	if script == "Devanagari":
		# Check if multiple Devanagari languages are enabled
		dev_candidates = [c for c in ("hi", "mr", "ne", "bho", "mai", "sa", "kok") if c in candidates]
		if len(dev_candidates) >= 2:
			resolved = sharedScriptLid.resolve_segment(text, "Devanagari", enabled_codes)
			if resolved and resolved in candidates:
				return candidates[resolved]
			pieces = devanagariGroupLid.segment(text, enabled_codes, whole_string=True)
			if pieces and pieces[0][1] in candidates:
				return candidates[pieces[0][1]]
		return candidates.get("hi", next(iter(candidates.values()), default_lang))

	# 3. Bengali vs Assamese
	if script == "Bengali":
		if "as" in candidates and any(c in text for c in "ৰৱ"):
			return candidates["as"]
		if "bn" in candidates:
			return candidates["bn"]

	return None


def _statistical_target(
	text: str,
	script: Optional[str],
	fallbackLanguage: str,
	languageMap: Optional[Dict[str, str]],
	detector=None,
	characterMode: bool = False,
) -> Optional[str]:
	"""
	Script-Gated Whitelist & Character Heuristics layer above FastText.
	Single characters or characterMode always bypass FastText.
	"""
	if not script or not languageMap:
		return None

	# Character Mode or very short Latin text: always bypass FastText to prevent foreign letter spelling
	clean_text = text.strip()
	if characterMode or len(clean_text) <= 2:
		return fallbackLanguage

	candidates = statisticalDetection.languages_for_script(languageMap, script)
	if not candidates:
		return None

	# If all candidates resolve to the same profile, no detection needed
	if all(profile == fallbackLanguage for profile in candidates.values()):
		return None

	# 1. Script-Gated Heuristics for shared scripts
	shared_result = _disambiguate_shared_script(text, script, candidates, fallbackLanguage)
	if shared_result:
		return shared_result

	# 2. FastText ML detection for Latin, Cyrillic, and other scripts
	detect = detector or statisticalDetection.detect_language
	return detect(text, candidates)


# Formatted number regex (dates, times, decimals, phone numbers)
_FORMATTED_NUMBER_RE = re.compile(
	r"(?:"
	r"\+?\d{1,4}[- ]\d{2,4}[- ]\d{3,4}(?:[- ]\d{1,4})?"  # Phone numbers
	r"|"
	r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"                   # Dates
	r"|"
	r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm))?"  # Time
	r"|"
	r"\d+(?:,\d+)*(?:\.\d+)?"                            # Commas / decimals
	r")"
)


def addDetectedLanguageCommands(
	speechSequence,
	defaultLang="en",
	scriptSettings=None,
	smartUrduArabic=True,
	numberMode="current",
	granularityMode="word",
	protectMathSymbols=True,
	mathLanguage="current",
	tagMode="override",
	useStatisticalDetection=True,
	statisticalLanguages=None,
	statisticalDetector=None,
):
	"""
	Segments speech sequences by script and language with support for:
	- Consecutive chunk merging
	- Formatted number, date, time preservation
	- Spelling & character mode FastText bypass
	- Shared-script disambiguation (Urdu/Arabic, Hindi/Marathi/Nepali, Bengali/Assamese)
	"""
	if scriptSettings is None:
		scriptSettings = dict(DEFAULT_SCRIPT_MAPPINGS)

	curLang = defaultLang
	buffer = []
	explicitLangActive = False
	characterModeActive = False

	def flush():
		nonlocal buffer
		if buffer:
			text = "".join(buffer)
			buffer = []
			return text
		return None

	for item in speechSequence:
		if isinstance(item, CharacterModeCommand):
			characterModeActive = getattr(item, "state", True)
			flushed = flush()
			if flushed:
				yield flushed
			yield item
			continue

		if isinstance(item, LangChangeCommand):
			flushed = flush()
			if flushed:
				yield flushed
			explicitLangActive = item.lang is not None
			curLang = item.lang if explicitLangActive else defaultLang
			yield item
			continue

		elif not isinstance(item, str):
			flushed = flush()
			if flushed:
				yield flushed
			yield item
			continue

		if tagMode == "preferTags" and explicitLangActive:
			buffer.append(item)
			continue

		# Sentence / Line granularity modes
		if granularityMode in ("sentence", "line"):
			if granularityMode == "line":
				units = re.findall(r"[^\n]*\n|[^\n]+$", item)
			else:
				units = re.findall(r".*?(?:[.!?。！？۔؟;:]+(?:\s+|$)|\n|$)", item)
				units = [unit for unit in units if unit]

			for unit in units:
				counts = {}
				arabicCandidate = None
				for c in unit:
					ctype = get_char_type(c, protect_math=protectMathSymbols)
					if ctype in ("mark", "space", "punct", "Common", "Inherited"):
						continue
					if ctype == "number":
						if numberMode in ("en", "ur", "ar", "hi"):
							candidate = numberMode
						elif numberMode == "default":
							candidate = defaultLang
						else:
							candidate = curLang
					elif ctype == "Arabic":
						if arabicCandidate is None:
							arabicCandidate = (
								classify_arabic_segment(unit, default_lang=defaultLang, current_lang=curLang)
								if smartUrduArabic else scriptSettings.get("Arabic", "ur")
							)
						candidate = arabicCandidate
					elif ctype == "math":
						candidate = (
							mathLanguage if mathLanguage not in ("current", "default")
							else (curLang if mathLanguage == "current" else defaultLang)
						)
					else:
						candidate = scriptSettings.get(ctype, curLang)
					counts[candidate] = counts.get(candidate, 0) + 1

				targetLang = max(counts, key=counts.get) if counts else curLang
				if useStatisticalDetection and not characterModeActive and len(unit.strip()) > 2:
					unitScript = _single_text_script(unit, protect_math=protectMathSymbols)
					statisticalTarget = _statistical_target(
						unit,
						unitScript,
						targetLang,
						statisticalLanguages,
						statisticalDetector,
						characterMode=characterModeActive,
					)
					if statisticalTarget:
						targetLang = statisticalTarget

				if targetLang != curLang:
					flushed = flush()
					if flushed:
						yield flushed
					curLang = targetLang
					yield LangChangeCommand(curLang)
				buffer.append(unit)
			continue

		# Word / Clause Granularity Mode
		segments = []
		clauses = re.findall(r".*?(?:[.!?。！？۔؟;:]+(?:\s+|$)|\n|$)", item)
		clauses = [clause for clause in clauses if clause]

		for clause in clauses:
			clauseScript = _single_text_script(clause, protect_math=protectMathSymbols)
			unicodeFallback = scriptSettings.get(clauseScript, curLang) if clauseScript else curLang
			clauseTarget = None
			if useStatisticalDetection and not characterModeActive and len(clause.strip()) > 2:
				clauseTarget = _statistical_target(
					clause,
					clauseScript,
					unicodeFallback,
					statisticalLanguages,
					statisticalDetector,
					characterMode=characterModeActive,
				)

			# Pre-scan for formatted numbers/dates/times to prevent token fragmentation
			numMatches = list(_FORMATTED_NUMBER_RE.finditer(clause))
			lastPos = 0
			for nm in numMatches:
				start, end = nm.span()
				if start > lastPos:
					# Process text preceding the number
					sub = clause[lastPos:start]
					curr_type = None
					curr_chars = []
					for c in sub:
						ctype = get_char_type(c, protect_math=protectMathSymbols)
						if ctype == "mark":
							curr_chars.append(c)
							continue
						if ctype == curr_type:
							curr_chars.append(c)
						else:
							if curr_chars:
								segments.append((curr_type, "".join(curr_chars), clauseScript, clauseTarget))
							curr_type = ctype
							curr_chars = [c]
					if curr_chars:
						segments.append((curr_type, "".join(curr_chars), clauseScript, clauseTarget))

				# Entire formatted number as single atomic token
				segments.append(("number", nm.group(0), clauseScript, clauseTarget))
				lastPos = end

			if lastPos < len(clause):
				sub = clause[lastPos:]
				curr_type = None
				curr_chars = []
				for c in sub:
					ctype = get_char_type(c, protect_math=protectMathSymbols)
					if ctype == "mark":
						curr_chars.append(c)
						continue
					if ctype == curr_type:
						curr_chars.append(c)
					else:
						if curr_chars:
							segments.append((curr_type, "".join(curr_chars), clauseScript, clauseTarget))
						curr_type = ctype
						curr_chars = [c]
				if curr_chars:
					segments.append((curr_type, "".join(curr_chars), clauseScript, clauseTarget))

		for stype, stext, clauseScript, clauseTarget in segments:
			if stype in ("space", "punct", "Common", "Inherited"):
				buffer.append(stext)
				continue

			if stype == "number":
				has_arabic_digits = any(ord(c) in ALL_ARABIC_DIGITS for c in stext)
				has_devanagari_digits = any(ord(c) in DEVANAGARI_DIGITS for c in stext)
				has_bengali_digits = any(ord(c) in BENGALI_DIGITS for c in stext)

				if has_arabic_digits:
					targetLang = curLang if curLang in ARABIC_SCRIPT_LANGS else (defaultLang if defaultLang in ARABIC_SCRIPT_LANGS else "ur")
				elif has_devanagari_digits:
					targetLang = curLang if curLang in ("hi", "mr", "ne", "bho", "mai", "sa", "kok") else "hi"
				elif has_bengali_digits:
					targetLang = curLang if curLang in ("bn", "as") else "bn"
				elif numberMode == "current":
					buffer.append(stext)
					continue
				elif numberMode == "default":
					targetLang = defaultLang
				elif numberMode == "en":
					targetLang = "en"
				else:
					targetLang = numberMode

				if targetLang != curLang:
					flushed = flush()
					if flushed:
						yield flushed
					curLang = targetLang
					yield LangChangeCommand(curLang)
				buffer.append(stext)
				continue

			if stype == "math":
				targetLang = mathLanguage
				if targetLang == "current":
					buffer.append(stext)
					continue
				if targetLang == "default":
					targetLang = defaultLang
				if targetLang != curLang:
					flushed = flush()
					if flushed:
						yield flushed
					curLang = targetLang
					yield LangChangeCommand(curLang)
				buffer.append(stext)
				continue

			if stype == "Arabic":
				if smartUrduArabic:
					targetLang = classify_arabic_segment(stext, default_lang=defaultLang, current_lang=curLang)
				else:
					arabic_lang = scriptSettings.get("Arabic", "ur") if scriptSettings else "ur"
					targetLang = arabic_lang if arabic_lang in ARABIC_SCRIPT_LANGS else "ur"
			elif clauseTarget and clauseScript == stype:
				targetLang = clauseTarget
			elif stype == "Latin" and (characterModeActive or len(stext.strip()) <= 2):
				# Single letter / spelling mode when no clause target: never switch to foreign language
				targetLang = scriptSettings.get("Latin", defaultLang) if scriptSettings else "en"
			else:
				targetLang = scriptSettings.get(stype, curLang) if (scriptSettings and stype) else curLang

			if targetLang != curLang:
				flushed = flush()
				if flushed:
					yield flushed
				curLang = targetLang
				yield LangChangeCommand(curLang)
			buffer.append(stext)

	flushed = flush()
	if flushed:
		yield flushed
