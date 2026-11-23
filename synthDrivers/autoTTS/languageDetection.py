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
ARABIC_SCRIPT_LANGS = frozenset({"ur", "ar", "fa", "ps", "sd", "ug", "ckb", "ks", "pnb"})

# Spoken names for punctuation and symbols read on their own (a line or a typed character
# made only of symbols). Honorific signs are handled by honorific_words() below. The Urdu
# names match locale/*/symbols-autoTTS.dic, which NVDA itself uses; a test keeps them equal.
_URDU_SYMBOLS: Dict[str, str] = {
	"\u06d4": "ختمہ",           # Urdu full stop (۔)
	"\u060c": "سکتہ",           # Arabic comma (،)
	"\u061b": "وقفہ",           # Arabic semicolon (؛)
	"\u061f": "سوالیہ نشان",     # Arabic question mark (؟)
	"\u066a": "فیصد",           # Arabic percent sign (٪)
	"\u060d": "تاریخ کا نشان",    # Date separator (؍)
	"\u0601": "سن",             # Year sign (؁)
	"\u060f": "مصرع",           # Misra sign (؏)
	"\u060e": "نظم نشان",        # Poetic verse sign (؎)
	"\u0614": "تخلص",           # Takhallus sign (ؔ)
	".": "ختمہ",
	",": "سکتہ",
	"?": "سوالیہ نشان",
	"!": "فجائیہ",
	":": "رابطہ",
	"-": "ڈیش",
}

SPOKEN_SYMBOLS: Dict[str, Dict[str, str]] = {
	"ur": _URDU_SYMBOLS,
	# Shahmukhi Punjabi uses the Urdu punctuation and its names.
	"pa-pk": _URDU_SYMBOLS,
	"pa-arab": _URDU_SYMBOLS,
	"pnb": _URDU_SYMBOLS,
	"ar": {
		"\u060c": "فاصلة",           # Arabic comma (،)
		"\u061b": "فاصلة منقوطة",    # Arabic semicolon (؛)
		"\u061f": "علامة استفهام",    # Arabic question mark (؟)
		"\u06d4": "نقطة",            # Full stop (۔)
		".": "نقطة",
		",": "فاصلة",
		"?": "علامة استفهام",
		"!": "علامة تعجب",
		":": "نقطتان",
	},
	"fa": {
		"\u060c": "ویرگول",
		"\u061b": "نقطه ویرگول",
		"\u061f": "علامت سوال",
		"\u06d4": "نقطه",
		".": "نقطه",
	},
	"ps": {
		"\u06d4": "ټکی",
		"\u060c": "کامې",
		"\u061f": "پوښتنې نښه",
		".": "ټکی",
	},
	"sd": {
		"\u06d4": "ختمو",
		"\u060c": "اُبتو ڪاما",
		"\u061f": "سوالي نشان",
		".": "ختمو",
	},
	"hi": {
		"\u0964": "पूर्ण विराम",      # Danda (।)
		"\u0965": "दीर्घ विराम",      # Double Danda (॥)
		".": "पूर्ण विराम",
		",": "अल्पविराम",
		"?": "प्रश्नवाचक चिह्न",
		"!": "विस्मयादिबोधक चिह्न",
		":": "उपविराम",
	},
	"pa": {
		"\u0964": "ਡੰਡੀ",           # Dandi (।)
		"\u0965": "ਦੋ ਡੰਡੀਆਂ",       # Double Dandi (॥)
		".": "ਡੰਡੀ",
		",": "ਕਾਮਾ",
		"?": "ਪ੍ਰਸ਼ਨ ਚਿੰਨ੍ਹ",
	},
	"pa-in": {
		"\u0964": "ਡੰਡੀ",
		"\u0965": "ਦੋ ਡੰਡੀਆਂ",
		".": "ਡੰਡੀ",
		",": "ਕਾਮਾ",
		"?": "ਪ੍ਰਸ਼ਨ ਚਿੰਨ੍ਹ",
	},
}


# Arabic-script honorific signs and ligatures. Each one stands for whole words, so it is always read
# as those words, wherever it appears and whichever synthesizer speaks it. Synthesizers either skip
# these characters or know them only in some voices, and a lone combining sign such as U+0611 has no
# base letter at all, so leaving them to the synthesizer produced silence.
_URDU_HONORIFICS: Dict[str, str] = {
	"ؐ": "صلی اللہ علیہ وسلم",
	"ؑ": "علیہ السلام",
	"ؒ": "رحمۃ اللہ علیہ",
	"ؓ": "رضی اللہ عنہ",
	"ﷲ": "اللہ",
	"ﷺ": "صلی اللہ علیہ وسلم",
	"ﷻ": "جل جلالہ",
	"﷽": "بسم اللہ الرحمٰن الرحیم",
}
_ARABIC_HONORIFICS: Dict[str, str] = {
	"ؐ": "صلى الله عليه وسلم",
	"ؑ": "عليه السلام",
	"ؒ": "رحمة الله عليه",
	"ؓ": "رضي الله عنه",
	"﷽": "بسم الله الرحمن الرحيم",
}
# The other Arabic ligatures of words (U+FDF0-U+FDFB) are read through their compatibility
# decomposition, which Unicode defines as the spelled-out words.
_WORD_LIGATURES = range(0xFDF0, 0xFDFC)
HONORIFIC_CHARS = frozenset(_URDU_HONORIFICS) | frozenset(_ARABIC_HONORIFICS) | frozenset(map(chr, _WORD_LIGATURES))


def is_arabic_script_lang(lang: Optional[str]) -> bool:
	"""Whether a language tag is written in Arabic script (including Shahmukhi Punjabi)."""
	if not lang:
		return False
	normFull, baseLang = normalize_language_code(lang)
	return baseLang in ARABIC_SCRIPT_LANGS or normFull in ("pa-pk", "pa-arab")


def _uses_urdu_spelling(lang: str) -> bool:
	normFull, baseLang = normalize_language_code(lang)
	return baseLang in ("ur", "pnb") or normFull in ("pa-pk", "pa-arab")


def honorific_words(char: str, lang: str) -> Optional[str]:
	"""The words an honorific sign or word ligature stands for, in the spelling of `lang`."""
	if char not in HONORIFIC_CHARS:
		return None
	if _uses_urdu_spelling(lang) and char in _URDU_HONORIFICS:
		return _URDU_HONORIFICS[char]
	if char in _ARABIC_HONORIFICS:
		return _ARABIC_HONORIFICS[char]
	words = unicodedata.normalize("NFKC", char)
	return words if words != char else None


def expand_honorifics(text: str, lang: str) -> str:
	"""Replace honorific signs and word ligatures with the words they stand for.
	Only applies to Arabic-script languages; any other run is returned unchanged."""
	if not text or not is_arabic_script_lang(lang) or not any(ch in HONORIFIC_CHARS for ch in text):
		return text
	pieces = []
	for ch in text:
		words = honorific_words(ch, lang)
		pieces.append(f" {words} " if words else ch)
	result = re.sub(r" {2,}", " ", "".join(pieces))
	return result.strip() if text == text.strip() else result


def has_content(text: str) -> bool:
	"""Whether text contains a letter or digit, i.e. anything a synthesizer reads as words."""
	return any(unicodedata.category(c)[0] in "LN" for c in text)


def to_nvda_locale(lang: Optional[str]) -> str:
	"""Convert a BCP-47 style tag (ur-pk) to NVDA's locale form (ur_PK).
	NVDA's symbol and character tables are looked up by this form; a hyphenated
	tag silently falls back to the English tables."""
	normFull, _baseLang = normalize_language_code(lang)
	parts = normFull.split("-")
	if len(parts) == 1:
		return parts[0]
	region = parts[-1]
	if len(region) == 2 or region.isdigit():
		return "_".join(parts[:-1] + [region.upper()])
	return "_".join(parts)


def get_spoken_symbol(char: str, lang: str) -> Optional[str]:
	"""Return the spoken name of a punctuation mark or symbol in the target language."""
	if not char or not lang:
		return None
	words = honorific_words(char, lang)
	if words:
		return words
	normFull, baseLang = normalize_language_code(lang)
	lang_dict = SPOKEN_SYMBOLS.get(normFull) or SPOKEN_SYMBOLS.get(baseLang)
	if lang_dict and char in lang_dict:
		return lang_dict[char]
	try:
		import characterProcessing
		desc = characterProcessing.processSpeechSymbol(to_nvda_locale(lang), char)
		if desc and desc.strip() and desc != char:
			return desc.strip()
	except Exception:
		pass
	return None


def expand_spoken_symbols(text: str, lang: str) -> str:
	"""Read every symbol of a symbol-only text by name in the target language.

	The caller decides when text is isolated (a line or character consisting only of
	symbols). Text containing any letter or digit is returned unchanged: punctuation
	inside a sentence shapes intonation and must never be read aloud by name."""
	if not text or not text.strip() or has_content(text):
		return text
	parts = []
	replaced_any = False
	for ch in text:
		if ch.isspace():
			continue
		spoken = get_spoken_symbol(ch, lang)
		if spoken:
			replaced_any = True
		parts.append(spoken or ch)
	return " ".join(parts) if replaced_any else text

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


def _urdu_family_profile(curLang: Optional[str], defaultLang: Optional[str], urduProfile: Optional[str]) -> str:
	"""The profile for Urdu-family text: the current or default language when it is an
	Arabic-script language other than Arabic (Urdu, Shahmukhi Punjabi...), else Urdu."""
	for lang in (curLang, defaultLang):
		if lang and is_arabic_script_lang(lang) and get_base_language(lang) not in ("ar", "fa", "ps", "sd"):
			return lang
	if urduProfile and is_arabic_script_lang(urduProfile):
		return urduProfile
	return "ur"


def arabic_script_profile(
	base: Optional[str],
	curLang: Optional[str],
	defaultLang: Optional[str],
	candidates: Optional[Dict[str, str]] = None,
	urduProfile: Optional[str] = None,
) -> str:
	"""Map a decision of persoArabicLid (a base code, or None) to the profile that reads it."""
	candidates = candidates or {}
	if base in (None, persoArabicLid.URDU_FAMILY):
		if base is None:
			# No evidence at all: stay with an Arabic-script language already in use.
			for lang in (curLang, defaultLang):
				if lang and is_arabic_script_lang(lang):
					return lang
		return _urdu_family_profile(curLang, defaultLang, urduProfile or candidates.get("ur"))
	return candidates.get(base, base)


def arabic_script_candidates(statisticalLanguages: Optional[Dict[str, str]]) -> Dict[str, str]:
	"""Base code -> profile for the user's Arabic-script profiles."""
	return {
		base: profile
		for base, profile in (statisticalLanguages or {}).items()
		if is_arabic_script_lang(profile) or base in ARABIC_SCRIPT_LANGS
	}


def resolve_arabic_text(
	text: str,
	candidates: Dict[str, str],
	detector=None,
	useStatistics: bool = True,
) -> Optional[str]:
	"""The base language (persoArabicLid codes) of an Arabic-script clause, using letters
	first and the statistical models only when the letters do not settle it."""
	bases = tuple(sorted(set(candidates) | {"ur", "ar"}))
	modelDetector = ngram = None
	if useStatistics and len(candidates) >= 2:
		detect = detector or statisticalDetection.detect_language
		identity = {base: base for base in candidates}
		modelDetector = lambda clause: detect(clause, identity)  # noqa: E731
		enabled = set(candidates)
		ngram = lambda clause: sharedScriptLid.model_decision(clause, "Arabic", enabled)  # noqa: E731
	return persoArabicLid.resolve_clause(text, bases, modelDetector, ngram)


@functools.lru_cache(maxsize=2048)
def classify_arabic_segment(text: str, default_lang: str = "ur", current_lang: Optional[str] = None) -> str:
	"""Urdu or Arabic for a piece of Arabic-script text (letter evidence only)."""
	decided = persoArabicLid.resolve_clause(text, ("ur", "ar"))
	return arabic_script_profile(decided, current_lang, default_lang)


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
	# Punctuation and symbols never start a language run of their own, even when Unicode
	# assigns them a script (Urdu ۔ and ؟ are Arabic-script): inside text they belong to the
	# surrounding words, and a symbol-only text is routed by symbol_only_language().
	if category[0] in "PS":
		return "punct"
	return get_script(cp)


def _split_by_char_type(text: str, protect_math: bool):
	"""Split text into runs of the same character type.
	A combining mark joins the letter before it. A mark with no letter before it (a lone
	honorific sign such as ؑ after a space) takes its own script, so it is still routed to a
	language that can read it instead of being glued to whitespace or punctuation."""
	runs = []
	curr_type = None
	curr_chars = []
	for c in text:
		ctype = get_char_type(c, protect_math=protect_math)
		if ctype == "mark":
			if curr_type not in (None, "space", "punct", "number", "math", "Common", "Inherited"):
				curr_chars.append(c)
				continue
			script = get_script(ord(c))
			ctype = script if script not in ("Common", "Inherited") else "punct"
		if ctype == curr_type:
			curr_chars.append(c)
			continue
		if curr_chars:
			runs.append((curr_type, "".join(curr_chars)))
		curr_type = ctype
		curr_chars = [c]
	if curr_chars:
		runs.append((curr_type, "".join(curr_chars)))
	return runs


# Languages that write the danda (। ॥) as their full stop.
_DANDA_LANGS = frozenset({"hi", "mr", "ne", "sa", "bho", "mai", "kok", "pa", "bn", "as", "or"})


def symbol_only_language(
	text: str,
	curLang: str,
	defaultLang: str,
	scriptSettings: Dict[str, str],
	keyboardLang: Optional[str] = None,
) -> Optional[str]:
	"""Choose the language for text made only of symbols, marks and spaces.

	A symbol that belongs to one writing system (Urdu ۔ ؟ ؎, an honorific sign, the
	Devanagari danda) is read in a language of that script, preferring the current and
	then the default language when they already use it. A symbol shared by every script
	(? or -) follows the keyboard language while typing, else stays in the current language."""
	script = None
	for ch in text:
		candidate = get_script(ord(ch))
		if candidate not in ("Common", "Inherited"):
			script = candidate
			break
	if script is None:
		return keyboardLang or None
	if script == "Arabic":
		for lang in (curLang, defaultLang):
			if is_arabic_script_lang(lang):
				return lang
		mapped = scriptSettings.get("Arabic", "ur")
		return mapped if is_arabic_script_lang(mapped) else "ur"
	if script == "Devanagari" and any(ch in "।॥" for ch in text):
		for lang in (curLang, defaultLang):
			if lang and get_base_language(lang) in _DANDA_LANGS:
				return lang
	mapped = scriptSettings.get(script)
	if not mapped:
		return None
	if curLang and get_base_language(curLang) == get_base_language(mapped):
		return curLang
	return mapped


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
	detector=None,
) -> Optional[str]:
	"""
	Script-gated character heuristics & n-gram disambiguation for shared scripts
	(Perso-Arabic, Devanagari, Bengali).
	"""
	enabled_codes = set(candidates.keys())

	# 1. Perso-Arabic (Urdu, Arabic, Persian, Pashto, Sindhi)
	if script == "Arabic":
		decided = resolve_arabic_text(text, arabic_script_candidates(candidates), detector)
		return arabic_script_profile(decided, default_lang, default_lang, candidates)

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
	shared_result = _disambiguate_shared_script(text, script, candidates, fallbackLanguage, detector)
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
	currentLang=None,
	activeKeyboardLang=None,
	protectedTexts=None,
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

	arabicCandidates = arabic_script_candidates(statisticalLanguages)
	curLang = currentLang or defaultLang
	if curLang != defaultLang:
		# The caller routes untagged text to the default language, so continuing in the
		# previous utterance's language must be stated, or text that needs no switch of its
		# own (more Urdu after Urdu) would be read by the default voice.
		yield LangChangeCommand(curLang)
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

		# A text with no letters or digits (a line holding only ؟ or ؑ, or one typed symbol)
		# is routed by the script its symbols belong to.
		if not has_content(item):
			if not item.isspace():
				targetLang = symbol_only_language(
					item,
					curLang,
					defaultLang,
					scriptSettings,
					keyboardLang=activeKeyboardLang if characterModeActive else None,
				)
				if targetLang and targetLang != curLang:
					flushed = flush()
					if flushed:
						yield flushed
					curLang = targetLang
					yield LangChangeCommand(curLang)
			buffer.append(item)
			continue

		# NVDA's own words (role and state names such as "link" or "button") are never
		# statistically scored: one short word is too little evidence and was often misread
		# as another language written in the same script.
		itemUsesStatistics = useStatisticalDetection and not (
			protectedTexts and item.strip().lower() in protectedTexts
		)
		arabicStatistics = itemUsesStatistics and not characterModeActive

		def arabicProfile(base):
			return arabic_script_profile(
				base, curLang, defaultLang, arabicCandidates,
				arabicCandidates.get("ur") or scriptSettings.get("Arabic"),
			)

		# Sentence / Line granularity modes
		if granularityMode in ("sentence", "line"):
			if granularityMode == "line":
				units = re.findall(r"[^\n]*\n|[^\n]+$", item)
			else:
				units = re.findall(r".*?(?:[.!?。！？۔؟;:]+(?:\s+|$)|\n|$)", item)
				units = [unit for unit in units if unit]

			for unit in units:
				# One vote per word, not per character: four short Urdu words must outvote
				# two long English ones in "ہم نے Facebook پر post کیا".
				counts = {}
				arabicCandidate = None
				for ctype, _run in _split_by_char_type(unit, protectMathSymbols):
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
							if smartUrduArabic:
								arabicText = " ".join(r for t, r in _split_by_char_type(unit, protectMathSymbols) if t == "Arabic")
								arabicCandidate = arabicProfile(
									resolve_arabic_text(arabicText, arabicCandidates, statisticalDetector, arabicStatistics)
								)
							else:
								arabicCandidate = scriptSettings.get("Arabic", "ur")
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
				if itemUsesStatistics and not characterModeActive and len(unit.strip()) > 2:
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
			arabicHandledByLetters = smartUrduArabic and clauseScript == "Arabic"
			if itemUsesStatistics and not characterModeActive and len(clause.strip()) > 2 and not arabicHandledByLetters:
				clauseTarget = _statistical_target(
					clause,
					clauseScript,
					unicodeFallback,
					statisticalLanguages,
					statisticalDetector,
					characterMode=characterModeActive,
				)

			# Formatted numbers, dates and times stay single atomic tokens.
			clauseSegments = []
			lastPos = 0
			for nm in _FORMATTED_NUMBER_RE.finditer(clause):
				start, end = nm.span()
				clauseSegments.extend(_split_by_char_type(clause[lastPos:start], protectMathSymbols))
				clauseSegments.append(("number", nm.group(0)))
				lastPos = end
			clauseSegments.extend(_split_by_char_type(clause[lastPos:], protectMathSymbols))

			# Arabic-script words: decide the clause from all its words together, then let
			# only a run with real evidence (a quoted Arabic phrase) take another language.
			arabicTargets = {}
			arabicIndexes = [i for i, (stype, _text) in enumerate(clauseSegments) if stype == "Arabic"]
			if smartUrduArabic and arabicIndexes:
				words = [clauseSegments[i][1] for i in arabicIndexes]
				clauseBase = resolve_arabic_text(" ".join(words), arabicCandidates, statisticalDetector, arabicStatistics)
				fallback = clauseBase or persoArabicLid.URDU_FAMILY
				wordBases = persoArabicLid.word_languages(words, fallback, tuple(set(arabicCandidates) | {"ur", "ar"}))
				for i, wordBase in zip(arabicIndexes, wordBases):
					arabicTargets[i] = arabicProfile(clauseBase if wordBase == fallback else wordBase)
			for i, (stype, stext) in enumerate(clauseSegments):
				segments.append((stype, stext, clauseScript, clauseTarget, arabicTargets.get(i)))

		for stype, stext, clauseScript, clauseTarget, arabicTarget in segments:
			if stype in ("space", "punct", "Common", "Inherited"):
				if characterModeActive and activeKeyboardLang and stype != "space":
					targetLang = activeKeyboardLang
					if targetLang != curLang:
						flushed = flush()
						if flushed:
							yield flushed
						curLang = targetLang
						yield LangChangeCommand(curLang)
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
				if arabicTarget:
					targetLang = arabicTarget
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
