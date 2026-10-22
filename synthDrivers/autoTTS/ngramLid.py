# Auto TTS for NVDA - Pure-Python Character N-gram Language Identifier
# Covered by GNU General Public License (GPL)

import json
import re
import unicodedata

_SCRIPT_KEEP = {
	"dev": "ऀ-ॿ",
	"perso": "؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿",
	"beng": "ঀ-৿",
}


class NgramModel:
	def __init__(self, data):
		self.group = data["group"]
		self.langs = list(data["langs"])
		self.orders = [int(n) for n in data["orders"]]
		self.scale = float(data["scale"])
		self.floor = {int(n): v for n, v in data["floor"].items()}
		self.grams = data["grams"]
		self._index = {l: i for i, l in enumerate(self.langs)}
		keep = _SCRIPT_KEEP.get(self.group, "")
		self._clean = re.compile(f"[^{keep}\\s]") if keep else re.compile(r"")
		self._marks = re.compile(r"[।॥۔]")

	@classmethod
	def load(cls, path):
		with open(path, "r", encoding="utf-8") as f:
			return cls(json.load(f))

	def normalize(self, text):
		text = unicodedata.normalize("NFC", str(text)).replace("‌", "").replace("‍", "")
		text = self._clean.sub(" ", text)
		text = self._marks.sub(" ", text)
		return re.sub(r"\s+", " ", text).strip()

	def scores(self, text, candidates=None):
		"""Mean log-probability per n-gram for candidate languages; higher is better."""
		text = self.normalize(text)
		langs = [l for l in (candidates or self.langs) if l in self._index]
		idx = [self._index[l] for l in langs]
		if not text or not idx:
			return {}
		padded = " " + text + " "
		total = [0.0] * len(idx)
		count = 0
		grams = self.grams
		for n in self.orders:
			floor = self.floor.get(n, -9.0)
			for i in range(len(padded) - n + 1):
				v = grams.get(padded[i:i + n])
				count += 1
				if v is None:
					for k, j in enumerate(idx):
						total[k] += floor[j]
				else:
					for k, j in enumerate(idx):
						total[k] += v[j]
		scale = self.scale * max(1, count)
		return {l: total[k] / scale for k, l in enumerate(langs)}

	def best(self, text, candidates=None):
		"""Returns (best_language, margin_to_second_best)."""
		s = sorted(self.scores(text, candidates).items(), key=lambda kv: -kv[1])
		if not s:
			return None, 0.0
		return s[0][0], (s[0][1] - s[1][1] if len(s) > 1 else 9.0)

	def decide(self, text, candidates, default, tau=0.2):
		"""Returns best language if margin >= tau; otherwise returns default."""
		lang, margin = self.best(text, candidates)
		if lang is None:
			return default
		return lang if (lang == default or margin >= tau) else default
