# Auto TTS for NVDA - Smart Language Detection Engine
# Covered by GNU General Public License (GPL)

import unicodedata
import re
from typing import Tuple, Optional, Dict

try:
	from speech.commands import LangChangeCommand, IndexCommand
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

from .scripts import get_script
from . import statisticalDetection

# Set of Urdu-exclusive characters that do NOT appear in standard Arabic text
URDU_EXCLUSIVE_CHARS = {
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
}

# Arabic-exclusive characters
ARABIC_EXCLUSIVE_CHARS = {
	0x0629,  # ة (Teh Marbuta - standard Arabic)
	0x064A,  # ي (Arabic Yeh with two dots below)
	0x0643,  # ك (Arabic Kaf with mini-kaf inside)
	0x0649,  # ى (Alef Maksura)
}

# Arabic Tashkeel, Harakat, and Quranic recitation marks
ARABIC_TASHKEEL_CHARS = {
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
}

QURANIC_MARKS = set(range(0x06D6, 0x06EE))

# Eastern Arabic and Arabic-Indic digit codepoints
EASTERN_ARABIC_DIGIT_RANGE = range(0x06F0, 0x06FA)  # ۰۱۲۳۴۵۶۷۸۹
ARABIC_INDIC_DIGIT_RANGE = range(0x0660, 0x066A)    # ٠١٢٣٤٥٦٧٨٩
ALL_ARABIC_DIGITS = set(EASTERN_ARABIC_DIGIT_RANGE) | set(ARABIC_INDIC_DIGIT_RANGE)

# Greek alphabet codepoints (used in math variables and formulas)
GREEK_LETTERS = set(range(0x0370, 0x03FF)) | set(range(0x1F00, 0x2000)) | set(range(0x1D6A8, 0x1D7CC))
MATH_SYMBOLS = set("+-−*/×÷=<>≤≥≈≠±√∞∑∏∫∂∆∇^‰%")

# Recognized Arabic-script based languages
ARABIC_SCRIPT_LANGS = {"ur", "ar", "fa", "ps", "sd", "ug", "ckb", "ks"}

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
	"Syriac": "syr",
	"Cherokee": "chr",
	"Canadian_Aboriginal": "iu",
	"Tagalog": "tl",
	"Hanunoo": "hnn",
	"Buhid": "bku",
	"Tagbanwa": "tbw",
	"Limbu": "lif",
	"Tai_Le": "tdd",
	"New_Tai_Lue": "khb",
	"Buginese": "bug",
	"Balinese": "ban",
	"Sundanese": "su",
	"Lepcha": "lep",
	"Ol_Chiki": "sat",
	"Vai": "vai",
	"Bamum": "bax",
	"Javanese": "jv",
	"Meetei_Mayek": "mni",
	"Nko": "nqo",
	"Lisu": "lis",
	"Miao": "hmn",
	"Chakma": "ccp",
	"Saurashtra": "saz",
	"Takri": "doi",
	"Adlam": "ff",
	"Hanifi_Rohingya": "rhg",
	"Nyiakeng_Puachue_Hmong": "hmn",
	"Pahawh_Hmong": "hmn",
	"Tangsa": "nst",
	"Toto": "txo",
	"Wancho": "nnp",
	"Nag_Mundari": "unr",
	"Dogra": "doi",
	"Masaram_Gondi": "gon",
	"Gunjala_Gondi": "gon",
	"Tifinagh": "ber",
	"Yi": "ii",
	"Kayah_Li": "eky",
	"Tai_Tham": "nod",
	"Tai_Viet": "blt",
	"Mro": "mro",
	"Medefaidrin": "dmf",
	"Warang_Citi": "hoc",
	"Osmanya": "so",
}


def normalize_language_code(lang: Optional[str]) -> Tuple[str, str]:
	"""Normalizes any language code into (normalized_full_tag, base_lang_code)."""
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


def get_base_language(lang: Optional[str]) -> str:
	"""Returns 2-letter base language code for any dialect tag."""
	return normalize_language_code(lang)[1]


def classify_arabic_segment(text: str, default_lang: str = "ur", current_lang: str = None) -> str:
	"""Accurately classifies Arabic-script text as Urdu or Arabic."""
	if not text:
		return default_lang or "ur"

	has_urdu = any(ord(c) in URDU_EXCLUSIVE_CHARS for c in text)
	has_arabic_exclusive = any(ord(c) in ARABIC_EXCLUSIVE_CHARS for c in text)
	has_quranic = any(ord(c) in QURANIC_MARKS for c in text)

	if has_quranic or (has_arabic_exclusive and not has_urdu):
		return "ar"
	if has_urdu and not has_arabic_exclusive:
		return "ur"

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


def get_char_type(c: str, protect_math: bool = True) -> str:
	"""Determines script / category for a single character with math variable protection."""
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
	script = get_script(cp)
	return script


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


def _statistical_target(
	text: str,
	script: Optional[str],
	fallbackLanguage: str,
	languageMap: Optional[Dict[str, str]],
	detector=None,
) -> Optional[str]:
	"""Use the model only where a same-script configured alternative exists."""
	if not script or not languageMap:
		return None
	# Unicode rules are more stable for Urdu/Arabic than a statistical
	# classifier. Both languages share many words and users frequently encounter
	# mixed Arabic/Urdu code-point variants, so model guesses can cause rapid and
	# incorrect voice switching inside otherwise normal Urdu text.
	if script == "Arabic":
		return None
	candidates = statisticalDetection.languages_for_script(languageMap, script)
	if not candidates:
		return None
	# Loading and running the model cannot improve a decision when every
	# candidate already resolves to the language selected by Unicode rules.
	if all(profile == fallbackLanguage for profile in candidates.values()):
		return None
	detect = detector or statisticalDetection.detect_language
	return detect(text, candidates)


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
	Processes speechSequence, segmenting text by script and language,
	and yielding LangChangeCommands alongside preserved speech commands.
	Supports Granularity modes: 'word', 'sentence', 'line'.
	"""
	if scriptSettings is None:
		scriptSettings = dict(DEFAULT_SCRIPT_MAPPINGS)

	curLang = defaultLang
	buffer = []
	explicitLangActive = False

	def flush():
		nonlocal buffer
		if buffer:
			text = "".join(buffer)
			buffer = []
			return text
		return None

	for item in speechSequence:
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

		# Sentence/line modes intentionally keep each selected unit together.
		# Word mode below remains the best choice for Urdu/English code switching.
		if granularityMode in ("sentence", "line"):
			if granularityMode == "line":
				units = re.findall(r"[^\n]*\n|[^\n]+$", item)
			else:
				units = re.findall(r".*?(?:[.!?۔؟]+(?:\s+|$)|\n|$)", item)
				units = [unit for unit in units if unit]

			for unit in units:
				counts = {}
				# The Arabic-script decision depends on the whole unit, not on one
				# character, so compute it once. Doing it per character made long
				# lines quadratic (about 12 seconds for a 10,000 character line).
				arabicCandidate = None
				for c in unit:
					ctype = get_char_type(c, protect_math=protectMathSymbols)
					if ctype in ("mark", "space", "punct", "Common", "Inherited", "number"):
						continue
					if ctype == "Arabic":
						if arabicCandidate is None:
							arabicCandidate = classify_arabic_segment(unit, default_lang=defaultLang, current_lang=curLang) if smartUrduArabic else scriptSettings.get("Arabic", "ur")
						candidate = arabicCandidate
					elif ctype == "math":
						candidate = mathLanguage if mathLanguage not in ("current", "default") else (curLang if mathLanguage == "current" else defaultLang)
					else:
						candidate = scriptSettings.get(ctype, curLang)
					counts[candidate] = counts.get(candidate, 0) + 1
				targetLang = max(counts, key=counts.get) if counts else curLang
				if useStatisticalDetection:
					unitScript = _single_text_script(unit, protect_math=protectMathSymbols)
					statisticalTarget = _statistical_target(
						unit,
						unitScript,
						targetLang,
						statisticalLanguages,
						statisticalDetector,
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

		# Tokenize and segment string. Statistical classification is performed
		# per clause, never per isolated word, so punctuation order is preserved
		# and short ambiguous words do not make the voice oscillate.
		segments = []
		clauses = re.findall(r".*?(?:[.!?。！？۔؟;:]+(?:\s+|$)|\n|$)", item)
		clauses = [clause for clause in clauses if clause]
		for clause in clauses:
			clauseScript = _single_text_script(clause, protect_math=protectMathSymbols)
			unicodeFallback = scriptSettings.get(clauseScript, curLang) if clauseScript else curLang
			clauseTarget = None
			if useStatisticalDetection:
				clauseTarget = _statistical_target(
					clause,
					clauseScript,
					unicodeFallback,
					statisticalLanguages,
					statisticalDetector,
				)

			curr_type = None
			curr_chars = []
			for c in clause:
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
				if has_arabic_digits:
					targetLang = curLang if curLang in ARABIC_SCRIPT_LANGS else (defaultLang if defaultLang in ARABIC_SCRIPT_LANGS else "ur")
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
			else:
				if clauseTarget and clauseScript == stype:
					targetLang = clauseTarget
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
