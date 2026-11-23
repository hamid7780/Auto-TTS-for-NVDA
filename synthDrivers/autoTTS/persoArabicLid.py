# Auto TTS for NVDA - Arabic-script language identification
# (Urdu, Arabic, Persian, Pashto, Sindhi; Shahmukhi Punjabi reads as Urdu)
# Covered by GNU General Public License (GPL)
"""Decide which Arabic-script language a word or clause is written in.

Each word is scored from letters that only some of these languages use. A clause takes
the language its words agree on; a statistical model is asked only when no word carries
a letter that settles it. Inside a clause, a run of words is given another language only
on real evidence (one decisive word, or two weaker ones), so a single borrowed word never
splits a sentence, while a quoted Arabic phrase inside Urdu still gets the Arabic voice.
"""

import re
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

# Decisive letters. Each set holds letters normal text in the other languages never uses.
URDU_LETTERS = frozenset("ٹڈڑںھہۂۃےۓ")  # ٹ ڈ ڑ ں ھ ہ ۂ ۃ ے ۓ
PASHTO_LETTERS = frozenset("ټځڅډړږښګڼۍې")  # ټ ځ څ ډ ړ ږ ښ ګ ڼ ۍ ې
# Sindhi-only letters. ٻ ڄ ڳ ڻ are left out: Saraiki and Shahmukhi Punjabi use them too.
SINDHI_LETTERS = frozenset("ٺٽٿڀڃڇڊڌڍڏڙڦڪڱ")
ARABIC_LETTERS = frozenset("ةىإ")  # ة ى إ

# Weaker evidence.
NON_ARABIC_LETTERS = frozenset("پچژگکی")  # پ چ ژ گ ک ی: Urdu, Persian, Pashto...
ARABIC_FORMS = frozenset("يكأ")  # ي ك أ: Arabic, but also Urdu typed on an Arabic keyboard
HARAKAT = frozenset(map(chr, list(range(0x064B, 0x0653)) + [0x0670]))
QURANIC_MARKS = frozenset(map(chr, range(0x06D6, 0x06EE)))
ZWNJ = "‌"

# Very common words that, on their own, lean one way.
ARABIC_WORDS = frozenset((
	"بسم", "الله", "لله", "والله", "بالله", "إن", "إنا", "أن", "في", "على", "عن", "مع", "إلى", "الى",
	"رب", "يا", "قال", "هذا", "ذلك", "التي", "الذي", "كان", "ثم",
))
PERSIAN_WORDS = frozenset((
	"است", "نیست", "هست", "این", "آن", "را", "به", "برای", "می", "بود", "شد", "هم", "چه", "آنها", "اینجا",
))

_TOKEN = re.compile(r"\S+")
_STRIP = re.compile("[" + "".join(sorted(HARAKAT | QURANIC_MARKS)) + ZWNJ + "ـ]")

STRONG = 2
WEAK = 1
# A word whose only hint is ي ك or أ: Arabic, unless the text is Urdu typed on an Arabic
# keyboard, or Sindhi or Pashto, which write the Arabic yeh themselves.
KEYBOARD_FORMS = "ar-forms"
URDU_FAMILY = "ur"  # Urdu and anything written like it (Shahmukhi Punjabi, Saraiki); the caller picks the profile


def word_evidence(word: str) -> Tuple[Optional[str], int]:
	"""(language, strength) for one word; (None, 0) when the word could belong to any of them."""
	letters = set(word)
	if letters & PASHTO_LETTERS:
		return "ps", STRONG
	if letters & SINDHI_LETTERS:
		return "sd", STRONG
	if letters & URDU_LETTERS:
		return "ur", STRONG
	if letters & ARABIC_LETTERS or letters & QURANIC_MARKS or sum(c in HARAKAT for c in word) >= 2:
		return "ar", STRONG
	bare = _STRIP.sub("", word)
	if bare in PERSIAN_WORDS or (ZWNJ in word and letters & NON_ARABIC_LETTERS):
		return "fa", WEAK
	if letters & NON_ARABIC_LETTERS:
		return "xa", WEAK  # not Arabic, otherwise undecided
	if bare in ARABIC_WORDS or (bare.startswith("ال") and len(bare) >= 4):
		return "ar", WEAK
	if letters & ARABIC_FORMS:
		return KEYBOARD_FORMS, WEAK
	return None, 0


def uses_arabic_keyboard_forms(evidence: Iterable[Tuple[str, Optional[str], int]]) -> bool:
	"""Urdu typed on an Arabic keyboard mixes ي/ك into words that also carry Urdu letters.
	In such a text ي and ك say nothing about Arabic."""
	return any(lang == "ur" and set(word) & ARABIC_FORMS for word, lang, _strength in evidence)


def _forms_count_as_arabic(evidence, candidates) -> bool:
	return not uses_arabic_keyboard_forms(evidence) and not ({"sd", "ps"} & set(candidates))


def resolve_clause(
	text: str,
	candidates: Sequence[str],
	detector: Optional[Callable[[str], Optional[str]]] = None,
	ngram: Optional[Callable[[str], Optional[str]]] = None,
) -> Optional[str]:
	"""The language of an Arabic-script clause, as a base code ("ur" meaning the Urdu family).
	`candidates` are the base codes the user has profiles for. None means the letters gave
	no evidence and no model could decide."""
	evidence = [(w,) + word_evidence(w) for w in _TOKEN.findall(text)]
	strong = {}
	weak = {}
	for _word, lang, strength in evidence:
		if lang is None:
			continue
		table = strong if strength == STRONG else weak
		table[lang] = table.get(lang, 0) + 1
	for lang in ("ps", "sd"):
		if strong.get(lang) and lang in candidates:
			return lang
	if not strong and len(evidence) >= 3:
		# No decisive letter: a statistical model on the whole clause beats weak hints.
		for model in (detector, ngram):
			if model is not None:
				decided = model(text)
				if decided in candidates:
					return decided
	arabicScore = STRONG * strong.get("ar", 0) + weak.get("ar", 0)
	if _forms_count_as_arabic(evidence, candidates):
		arabicScore += weak.get(KEYBOARD_FORMS, 0)
	otherScore = STRONG * (strong.get("ur", 0) + strong.get("ps", 0) + strong.get("sd", 0)) + weak.get("fa", 0) + weak.get("xa", 0)
	if arabicScore > otherScore:
		return "ar"
	if strong.get("ur"):
		return URDU_FAMILY
	if otherScore:
		return "fa" if weak.get("fa") and "fa" in candidates else URDU_FAMILY
	return None


def word_languages(words: Sequence[str], clauseLang: str, candidates: Sequence[str] = ("ur", "ar")) -> List[str]:
	"""The language of each word of a clause whose language is `clauseLang`.
	Only a run with real evidence for another language leaves the clause language:
	Arabic needs one decisive word or two weaker ones; inside Arabic, another language
	needs a decisive word. A run is trimmed to its first and last evidence word, so the
	plain words around a quotation stay with the sentence."""
	evidence = [(w,) + word_evidence(w) for w in words]
	if _forms_count_as_arabic(evidence, candidates):
		evidence = [(w, "ar" if lang == KEYBOARD_FORMS else lang, s) for w, lang, s in evidence]
	else:
		evidence = [(w, None, 0) if lang == KEYBOARD_FORMS else (w, lang, s) for w, lang, s in evidence]
	result = [clauseLang] * len(words)
	clauseIsArabic = clauseLang == "ar"

	def isOther(lang, strength):
		if lang is None:
			return None  # neutral: may sit inside a run
		if clauseIsArabic:
			return lang != "ar" and strength == STRONG
		return lang == "ar"

	i = 0
	while i < len(words):
		if not isOther(evidence[i][1], evidence[i][2]):
			i += 1
			continue
		# Grow a run over other-language and neutral words.
		end = i
		j = i
		while j < len(words):
			state = isOther(evidence[j][1], evidence[j][2])
			if state is False:
				break
			if state:
				end = j
			j += 1
		run = evidence[i:end + 1]
		if clauseIsArabic:
			langs = [lang for _w, lang, s in run if lang not in (None, "ar") and s == STRONG]
			target = max(set(langs), key=langs.count)
			accept = True
		else:
			target = "ar"
			strongCount = sum(1 for _w, lang, s in run if lang == "ar" and s == STRONG)
			weakCount = sum(1 for _w, lang, s in run if lang == "ar" and s == WEAK)
			accept = strongCount >= 1 or weakCount >= 2
		if accept:
			for k in range(i, end + 1):
				result[k] = target
		i = end + 1
	return result


def classify(text: str) -> Optional[str]:
	"""'ur' or 'ar' for a piece of text, or None without evidence (Urdu/Arabic only)."""
	return resolve_clause(text, ("ur", "ar"))
