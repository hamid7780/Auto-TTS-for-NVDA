# Auto TTS for NVDA - Perso-Arabic Language Disambiguation (Urdu vs Arabic)
# Covered by GNU General Public License (GPL)

import re

# Urdu and Persian-exclusive letter forms that never appear in standard Arabic
URDU_CHARS = frozenset("کیہےھٹڈڑں۔گچپژٻڀٺٽڇڌڍڎڙڦګڳڱڻݨ")

# Arabic-exclusive letter forms and Tashkeel marks
ARABIC_CHARS = frozenset("كيةىهأإؤًٌٍ")

_ARTICLE_PREFIXES = ("ال", "لل", "بال", "وال", "فال", "كال", "ولل", "فلل")
_NON_LETTERS = re.compile(r"[^\w]+", re.UNICODE)


def evidence(text: str):
	"""Returns (urdu_letter_count, arabic_letter_count)."""
	ur = ar = 0
	for ch in text:
		if ch in URDU_CHARS:
			ur += 1
		elif ch in ARABIC_CHARS:
			ar += 1
	return ur, ar


def soft_arabic_words(text: str) -> int:
	"""Count of words of 4+ characters beginning with an Arabic joined definite article."""
	n = 0
	for w in _NON_LETTERS.split(text):
		if len(w) >= 4 and w.startswith(_ARTICLE_PREFIXES):
			n += 1
	return n


def classify(text: str):
	"""
	Returns 'ur' or 'ar' based on letter forms and prefixes, or None if no evidence exists.
	"""
	ur, ar = evidence(text)
	if ur > ar:
		return "ur"
	if ar > ur:
		return "ar"
	if ur == 0 and soft_arabic_words(text) > 0:
		return "ar"
	return None


def split(text: str):
	"""
	Splits mixed Urdu/Arabic text word-by-word into [(piece_text, 'ur'|'ar')].
	Words lacking evidence inherit their neighbor's language.
	"""
	tokens = re.findall(r"\S+\s*", text)
	n = len(tokens)
	if n == 0:
		return [(text, "ur")]

	raw = []
	for tok in tokens:
		u, a = evidence(tok)
		if u > a:
			raw.append("U")
		elif a > u:
			raw.append("A")
		elif u == 0 and soft_arabic_words(tok) > 0:
			raw.append("A")
		else:
			raw.append("N")

	if all(r == "N" for r in raw):
		return [(text, "ur")]

	lab = [""] * n
	w = 0
	while w < n:
		if raw[w] != "N":
			lab[w] = raw[w]
			w += 1
			continue
		e = w
		while e < n and raw[e] == "N":
			e += 1
		left = raw[w - 1] if w > 0 else raw[e]
		right = raw[e] if e < n else left
		left_count = (e - w) if left == right else (e - w + 1) // 2
		for q in range(w, e):
			lab[q] = left if q - w < left_count else right
		w = e

	groups = []
	for i in range(n):
		if groups and groups[-1][0] == lab[i]:
			groups[-1][2] = i + 1
			if raw[i] != "N":
				groups[-1][3] += 1
		else:
			groups.append([lab[i], i, i + 1, 1 if raw[i] != "N" else 0])

	while len(groups) > 1:
		idx = next((k for k, g in enumerate(groups) if g[3] < 2), -1)
		if idx < 0:
			break
		g = groups[idx]
		prev = groups[idx - 1] if idx > 0 else None
		nxt = groups[idx + 1] if idx + 1 < len(groups) else None
		if prev is None:
			to_prev = False
		elif nxt is None:
			to_prev = True
		else:
			to_prev = (prev[2] - prev[1]) >= (nxt[2] - nxt[1])
		if to_prev:
			prev[2] = g[2]
			prev[3] += g[3]
		else:
			nxt[1] = g[1]
			nxt[3] += g[3]
		del groups[idx]
		j = 0
		while j < len(groups) - 1:
			if groups[j][0] == groups[j + 1][0]:
				groups[j][2] = groups[j + 1][2]
				groups[j][3] += groups[j + 1][3]
				del groups[j + 1]
			else:
				j += 1

	return [("".join(tokens[g[1]:g[2]]), "ar" if g[0] == "A" else "ur") for g in groups]
