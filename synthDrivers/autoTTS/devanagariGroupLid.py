# Auto TTS for NVDA - Devanagari Group Language Disambiguation
# Covered by GNU General Public License (GPL)

import re

STRICT = frozenset(("bho", "brx", "doi", "kok", "mai", "sa"))
EXTRAS = ("ne", "bho", "brx", "doi", "mai", "kok", "sa")

LONG_MIN_WORDS = 10
HINDI_KEEP_WORDS = 5
STRICT_MIN_SCORE = 6
STRICT_MIN_LEAD = 2
SHORT_BHO_SCORE = 6

_NOT_A_BOUNDARY = r'[^\s।॥,.!?;:()\[\]{}"\'\-]'


def _bounded(pattern):
	return r"(?<!" + _NOT_A_BOUNDARY + r")" + pattern + r"(?!" + _NOT_A_BOUNDARY + r")"


def _word_markers(words, weight):
	return [(re.compile(_bounded(re.escape(w))), weight) for w in words]


def _tiered(strong, supporting):
	return _word_markers(strong, weight=3) + _word_markers(supporting, weight=1)


HINDI_WORDS = _tiered(
	strong=["है", "हैं", "था", "थी", "थे", "थीं", "नहीं"],
	supporting=["मैं", "आप", "यह", "वह", "मुझे", "तुम्हें", "कोई", "उसने", "और", "भी", "ही"],
)

MARATHI_WORDS = _tiered(
	strong=["आहे", "आहेस", "आहोत", "आहात", "आहेत", "नाही", "नको", "नाहीत"],
	supporting=[
		"मी", "आम्ही", "तुम्ही", "आपण", "माझा", "माझी", "माझे", "आपला", "आपली", "आपले",
		"काय", "पण", "साठी", "मध्ये", "आणि", "मला", "तुला", "म्हणून", "होता", "होती"
	],
)

MARATHI_ANY = re.compile(_bounded(r"(?:आहे|आहेत|आणि|आम्ही|तुम्ही|होता|होती|मला|तुला|म्हणून|नाही|नाहीत)"))

SANSKRIT_WORDS = _tiered(
	strong=["अस्ति", "सन्ति", "स्तः", "अस्मि", "असि", "स्मः", "आसीत्", "आसन्", "नास्ति"],
	supporting=[
		"अहम्", "त्वम्", "वयम्", "यूयम्", "किम्", "कुत्र", "अत्र", "तत्र",
		"इति", "एव", "भवति", "भवन्ति", "सः", "तत्", "गच्छति", "करोति", "भवान्", "भवती"
	],
)

BHOJPURI_WORDS = _tiered(
	strong=["बा", "बाड़", "बाड़े", "बानी", "नइखे", "रउरा", "रउआ"],
	supporting=["हमनी", "उनुका", "आपन", "कइसे", "केहू", "काहे", "जाले", "करेले", "होई", "रहेले"],
)

MAITHILI_WORDS = _tiered(
	strong=["अछि", "अछी", "छथि", "अहाँ", "अहाँक"],
	supporting=["तोँह", "हुनका", "हिनका", "एकरा", "सँ", "केँ", "रहथि", "होथि", "करैत"],
)

KONKANI_WORDS = _tiered(
	strong=["आसा", "आसां", "आसात", "हांव", "म्हाका", "आनी"],
	supporting=[
		"आमी", "तूं", "तुमी", "तुका", "ताका", "म्हजो", "म्हजी", "म्हजें",
		"खंय", "कितें", "कडेन", "लागीं", "जाल्यार", "देखून", "आमकां", "तुमकां"
	],
)

BODO_WORDS = _tiered(
	strong=["दं", "नङा", "नंगौ", "आरो"],
	supporting=[
		"जों", "नों", "आं", "बि", "आंनि", "जोंनि", "नोंनि",
		"मानो", "बहा", "माब्ला", "खौरां", "मोनसे", "जाबाय"
	],
)
BODO_SUFFIX = re.compile(_bounded(r"\S+नाय"))

DOGRI_WORDS = _tiered(
	strong=["ऐ", "नेईं", "कुत्थै"],
	supporting=[
		"तुस", "तुसें", "मिगी", "तुगी", "थुआड़े", "केह्", "कुन",
		"आसतै", "कन्नै", "हून", "जेकर", "साकुं", "असी", "जेह्ड़ा", "गी", "इत्थे"
	],
)

NEPALI_WORDS = _tiered(
	strong=["छ", "छन्", "छैन", "छैनन्", "होइन", "हुनुहुन्छ", "हुनुहुन्न", "पनि", "थियो", "छु", "छौं"],
	supporting=[
		"म", "हामी", "तिमी", "तपाईं", "उहाँ", "यो", "त्यो", "लाई", "बाट", "हो", "हुन्",
		"हामीलाई", "जसले", "गर्दछ", "भने", "भएको", "गरेको", "गर्ने", "गर्दै", "नै", "थिए", "तर",
		"मलाई", "तिमीलाई", "उसलाई", "धेरै", "राम्रो", "नयाँ", "हिजो", "भोलि", "कस्तो", "कसरी"
	],
)
NEPALI_VERB_SUFFIX = re.compile(_bounded(r"\S+(?:न्छ|छौं|छन्|नुहोस्|हरू|हरु)"))

HINDI_MARATHI_ONLY = [pattern for pattern, _w in _word_markers([
	"है", "हैं", "में", "और", "नहीं", "क्या", "था", "थे", "थी", "मैं", "हम", "यह", "वह",
	"रहे", "रही", "रहा", "गया", "गई", "हूँ", "हूं", "आपको", "तुम", "तुम्हें", "मुझे", "ऐसी",
	"लेकिन", "कृपया", "करना", "करने", "होगा", "हुआ", "कि",
	"आहे", "आहेत", "नाही", "आणि", "मध्ये", "तुम्ही", "आम्ही", "मला", "तुला", "पण", "होते",
	"होता", "करायचे", "असे", "हे", "काल", "आहेस",
], 1)]

_SENTENCE_END = re.compile(r"(?:।|॥|[!?]|(?<!\d)\.(?!\d))+\s*")


def _score(text, markers, extra_patterns=()):
	score = hits = 0
	for pattern, weight in markers:
		if pattern.search(text):
			score += weight
			hits += 1
	for pattern in extra_patterns:
		if pattern.search(text):
			score += 3
			hits += 1
	return score, hits


def count_words(text: str) -> int:
	return sum(1 for w in re.split(r"\s+", text.strip()) if any(c.isalnum() for c in w))


def scores_for(text, candidates):
	out = {}
	for lang in candidates:
		if lang == "sa":
			out[lang] = _score(text, SANSKRIT_WORDS)
		elif lang == "bho":
			out[lang] = _score(text, BHOJPURI_WORDS)
		elif lang == "mai":
			out[lang] = _score(text, MAITHILI_WORDS)
		elif lang == "kok":
			out[lang] = _score(text, KONKANI_WORDS)
		elif lang == "brx":
			out[lang] = _score(text, BODO_WORDS, (BODO_SUFFIX,))
		elif lang == "doi":
			out[lang] = _score(text, DOGRI_WORDS)
		elif lang == "ne":
			score, hits = _score(text, NEPALI_WORDS, (NEPALI_VERB_SUFFIX,))
			penalty = 3 * sum(1 for p in HINDI_MARATHI_ONLY if p.search(text))
			out[lang] = (max(0, score - penalty), hits)
		elif lang == "mr":
			out[lang] = _score(text, MARATHI_WORDS)
		elif lang == "hi":
			out[lang] = _score(text, HINDI_WORDS)
	return out


def _split_sentences(text):
	parts, start = [], 0
	for m in _SENTENCE_END.finditer(text):
		parts.append(text[start:m.end()])
		start = m.end()
	if start < len(text):
		parts.append(text[start:])
	return [p for p in parts if p.strip()]


def _required_score(words):
	if words <= 40:
		return 4
	if words <= 120:
		return 6
	return 8


def _lead(scores, label):
	others = [v[0] for k, v in scores.items() if k != label and k in EXTRAS]
	return scores[label][0] - (max(others) if others else 0)


def _weak_label(sentence, extras):
	scores = scores_for(sentence, extras)
	if not scores:
		return None
	ranked = sorted(scores.items(), key=lambda kv: kv[1][0], reverse=True)
	best, (best_score, _hits) = ranked[0]
	second = ranked[1][1][0] if len(ranked) > 1 else 0
	if best_score >= 3 and best_score > second:
		return best
	return None


def _verify(group, label, extras):
	words = count_words(group)
	scores = scores_for(group, extras)
	score, hits = scores[label]
	lead = _lead(scores, label)
	required = STRICT_MIN_SCORE if label in STRICT else _required_score(words)
	return words >= LONG_MIN_WORDS and score >= required and hits >= 2 and lead >= STRICT_MIN_LEAD


def segment_extras(text, enabled):
	extras = [l for l in EXTRAS if l in enabled]
	if not extras:
		return [(text, None)]
	sents = _split_sentences(text)
	if not sents:
		return [(text, None)]
	weak = [_weak_label(s, extras) for s in sents]
	out, pending = [], []

	def flush():
		if pending:
			out.append(("".join(pending), None))
			pending.clear()

	i = 0
	while i < len(sents):
		label = weak[i]
		if label is None:
			pending.append(sents[i])
			i += 1
			continue
		j, parts = i, []
		while j < len(sents) and weak[j] == label:
			parts.append(sents[j])
			j += 1
		group = "".join(parts)
		if _verify(group, label, extras):
			flush()
			out.append((group, label))
		else:
			pending.append(group)
		i = j
	flush()
	return out


def classify_short(text, enabled):
	cands = [l for l in ("mr", "ne", "bho") if l in enabled]
	if not cands:
		return None
	scores = scores_for(text, set(cands) | {"hi", "mr"})
	hi = scores.get("hi", (0, 0))[0]
	mr = scores.get("mr", (0, 0))[0]
	ne = scores.get("ne", (0, 0))[0]
	bho = scores.get("bho", (0, 0))[0]
	if "mr" in cands and mr >= 3 and mr - hi >= 3 and mr > max(ne, bho):
		return "mr"
	if "bho" in cands and bho >= SHORT_BHO_SCORE and scores.get("bho", (0, 0))[1] >= 2 and bho - max(hi, mr, ne) >= 3:
		return "bho"
	if "ne" in cands and ne >= 5 and scores.get("ne", (0, 0))[1] >= 2 and ne - max(hi, mr, bho) >= 3:
		return "ne"
	return None


def _split_clauses(text):
	parts = []
	for s in _split_sentences(text):
		start = 0
		for m in re.finditer(r"[,;:—–]\s+", s):
			parts.append(s[start:m.end()])
			start = m.end()
		if start < len(s):
			parts.append(s[start:])
	windows = []
	for p in parts:
		tokens = re.findall(r"\S+\s*", p)
		if len(tokens) <= 14:
			windows.append(p)
			continue
		k = 0
		while k < len(tokens):
			end = min(k + 8, len(tokens))
			if len(tokens) - end < 4:
				end = len(tokens)
			windows.append("".join(tokens[k:end]))
			k = end
	out = []
	for p in windows:
		if out and count_words(p) < 3:
			out[-1] += p
		else:
			out.append(p)
	return [p for p in out if p.strip()]


def _chunk_language(chunk):
	scores = scores_for(chunk, ["hi", "mr"])
	hi, mr = scores["hi"][0], scores["mr"][0]
	if mr >= 3 and mr > hi:
		return "mr"
	if hi >= 3 and hi > mr:
		return "hi"
	return None


def split_hindi_marathi(text, whole_string=False):
	words = count_words(text)
	if words < LONG_MIN_WORDS + HINDI_KEEP_WORDS:
		if whole_string:
			scores = scores_for(text, ["hi", "mr"])
			hi, mr = scores["hi"][0], scores["mr"][0]
			if mr >= 3 and mr - hi >= 3:
				return [(text, "mr")]
		return [(text, "hi")]
	if not MARATHI_ANY.search(text):
		return [(text, "hi")]
	chunks = _split_clauses(text)
	langs = [_chunk_language(c) for c in chunks]
	prev = None
	for i, l in enumerate(langs):
		if l is None:
			langs[i] = prev
		else:
			prev = l
	nxt = None
	for i in range(len(langs) - 1, -1, -1):
		if langs[i] is None:
			langs[i] = nxt
		else:
			nxt = langs[i]
	groups = []
	for c, l in zip(chunks, langs):
		l = l or "hi"
		w = count_words(c)
		if groups and groups[-1][0] == l:
			groups[-1][1] += c
			groups[-1][2] += w
		else:
			groups.append([l, c, w])
	changed = True
	while changed and len(groups) > 1:
		changed = False
		for i, g in enumerate(groups):
			minimum = HINDI_KEEP_WORDS if g[0] == "hi" else LONG_MIN_WORDS
			if g[2] < minimum:
				g[0] = groups[i - 1][0] if i > 0 else groups[i + 1][0]
				merged = []
				for x in groups:
					if merged and merged[-1][0] == x[0]:
						merged[-1][1] += x[1]
						merged[-1][2] += x[2]
					else:
						merged.append(x)
				groups = merged
				changed = True
				break
	return [(g[1], g[0]) for g in groups]


def segment(text, enabled, whole_string=False):
	"""
	Main entry for Devanagari segmentation.
	Returns [(text_piece, lang_code)].
	"""
	hi_on, mr_on = "hi" in enabled, "mr" in enabled
	words = count_words(text)
	default = "hi" if hi_on else ("mr" if mr_on else "hi")

	if words < LONG_MIN_WORDS:
		lang = classify_short(text, enabled) if whole_string else None
		if lang is not None:
			return [(text, lang)]
		elif hi_on and mr_on:
			return split_hindi_marathi(text, whole_string)
		else:
			return [(text, default)]
	else:
		result = []
		for seg_text, label in segment_extras(text, enabled):
			if label is not None:
				result.append((seg_text, label))
			elif hi_on and mr_on:
				result.extend(split_hindi_marathi(seg_text, whole_string and seg_text == text))
			else:
				result.append((seg_text, default))
		return result
