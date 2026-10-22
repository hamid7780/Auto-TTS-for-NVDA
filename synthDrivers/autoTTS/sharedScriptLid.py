# Auto TTS for NVDA - Shared-Script Language Identification (Devanagari, Perso-Arabic, Bengali)
# Covered by GNU General Public License (GPL)

import os
import re
import threading
import time

try:
	from . import activityLog
except ImportError:
	class activityLog:
		@staticmethod
		def write(cat, msg): pass
		@staticmethod
		def writeException(cat, msg): pass

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lidModels")
GROUP_FILES = {"dev": "lid_dev.json", "perso": "lid_perso.json", "beng": "lid_beng.json"}

GROUP_ORDER = {
	"dev": ("hi", "mr", "ne", "bho", "mai", "kok", "sa"),
	"perso": ("ur", "ar", "sd", "fa"),
	"beng": ("bn", "as"),
}
DEV_EXTRAS = ("brx", "doi", "ks")

MIN_WORDS = {"dev": 6, "perso": 2, "beng": 2}


def _tau(group: str, words: int) -> float:
	if group == "dev":
		return 0.30 if words < 12 else 0.25
	if group == "perso":
		return 0.10
	return 0.10


_models = {}
_loading = set()
_failed = set()
_lock = threading.Lock()
_cache = {}
_CACHE_MAX = 512

_END = re.compile(r"[।॥?!؟۔\n]|(?<!\d)\.(?=\s|$)")


def _load(group: str):
	started = time.time()
	try:
		from . import ngramLid
		modelPath = os.path.join(MODEL_DIR, GROUP_FILES[group])
		if not os.path.isfile(modelPath):
			return
		model = ngramLid.NgramModel.load(modelPath)
		with _lock:
			_models[group] = model
		activityLog.write("LID", f"model '{group}' loaded in {int((time.time() - started) * 1000)} ms")
	except Exception:
		with _lock:
			_failed.add(group)
		activityLog.writeException("ERROR", f"LID model '{group}' could not be loaded")
	finally:
		with _lock:
			_loading.discard(group)


def _ensure(group: str):
	"""Returns the model if loaded; triggers background thread loading if not."""
	with _lock:
		model = _models.get(group)
		if model is not None or group in _failed or group in _loading:
			return model
		_loading.add(group)
	try:
		threading.Thread(target=_load, args=(group,), name=f"autoTTS-lid-{group}", daemon=True).start()
	except Exception:
		with _lock:
			_loading.discard(group)
			_failed.add(group)
	return None


def candidates(group: str, enabled: set) -> list:
	return [l for l in GROUP_ORDER.get(group, ()) if l in enabled]


def preload(enabled: set):
	"""Preloads models for enabled shared-script languages."""
	for group in GROUP_ORDER:
		if len(candidates(group, enabled)) >= 2:
			_ensure(group)


def _chunks(text: str):
	out, last = [], 0
	for m in _END.finditer(text):
		out.append((text[last:m.end()], True))
		last = m.end()
	if last < len(text):
		out.append((text[last:], False))
	return out


def _decide(group: str, model, cands: list, text: str, previous: str):
	norm = model.normalize(text)
	words = len(norm.split())
	default = cands[0] if cands else "hi"
	if words < MIN_WORDS.get(group, 2):
		lang = previous if previous in cands else default
		return lang, f"ngram: short ({words}w) -> {lang}", True, words, None

	if group == "beng" and "as" in cands and ("ৰ" in text or "ৱ" in text):
		return "as", "ngram: Assamese character -> as", False, words, None

	key = (group, tuple(cands), norm)
	hit = _cache.get(key)
	if hit is None:
		scores = model.scores(norm, cands)
		ranked = sorted(scores.items(), key=lambda kv: -kv[1])
		hit = (ranked[0][0], ranked[0][1] - ranked[1][1], scores) if ranked else (None, 0.0, {})
		if len(_cache) >= _CACHE_MAX:
			_cache.clear()
		_cache[key] = hit

	best, margin, scores = hit
	tau = _tau(group, words)
	if best is None:
		return default, f"ngram: no result -> {default}", True, words, None
	if best == default or margin >= tau:
		return best, f"ngram: best={best} margin={margin:.2f} >= tau={tau:.2f}", False, words, scores
	return default, f"ngram: margin={margin:.2f} < tau={tau:.2f} -> {default}", True, words, scores


def resolve_segment(text: str, script_name: str, enabled: set) -> str:
	"""
	Quick entry point for deciding a single segment or sentence of shared script.
	Returns best language code.
	"""
	group_map = {"Devanagari": "dev", "Arabic": "perso", "Bengali": "beng"}
	group = group_map.get(script_name)
	if not group:
		return None

	cands = candidates(group, enabled)
	if len(cands) <= 1:
		return cands[0] if cands else None

	# Special fast heuristics
	if group == "beng" and "as" in cands and any(c in text for c in "ৰৱ"):
		return "as"
	if group == "perso":
		from . import persoArabicLid
		res = persoArabicLid.classify(text)
		if res and res in cands:
			return res

	model = _ensure(group)
	if model is not None:
		try:
			cands_in_model = [c for c in cands if c in model.langs]
			if len(cands_in_model) >= 2:
				best, margin, _ = _decide(group, model, cands_in_model, text, cands_in_model[0])
				if best:
					return best
		except Exception:
			pass

	# Heuristic fallback if model not loaded
	if group == "dev":
		from . import devanagariGroupLid
		pieces = devanagariGroupLid.segment(text, enabled, whole_string=True)
		if pieces:
			return pieces[0][1]
	return cands[0]
