# Auto TTS for NVDA - Advanced Number, Date, Time & Phone Processing
# Covered by GNU General Public License (GPL)

import re
import unicodedata

# Private-Use-Area marker: unambiguous tag for reserved mobile numbers
MOBILE_MARKER = "\uE000"

# Formatted number regex supporting ASCII and all Unicode decimal digits:
# Matches dates (2026-10-17, 17/10/2026), times (11:45:07, 11:45 AM/PM),
# currencies ($100, Rs. 500), decimals (3.14159), comma-grouped numbers (1,000,000)
_DATE_TIME_REGEX = re.compile(
	r"(?<![\w])"
	r"(?:"
	r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"         # Dates: 2026-10-17, 17/10/2026, 17.10.2026
	r"|"
	r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm))?"  # Times: 11:45, 11:45:07, 11:45 AM
	r")"
	r"(?![\w])"
)

# Mobile phone number: optional +CC followed by national number (10-12 digits with optional spaces or dashes)
_MOBILE_REGEX = re.compile(r"(?<!\d)(?:(?:\+|00)(\d{1,3})[ -]?)?([0-9](?:[ -]?[0-9]){9,11})(?!\d)")

# Standard integer/decimal number: optionally comma-separated digits with optional decimal point
_NUMBER_REGEX = re.compile(r"(\d+(?:,\d+)*)(\.\d+)?")

# Reserved mobile marker regex
_RESERVED_MOBILE_REGEX = re.compile(MOBILE_MARKER + r"(\d(?: \d){9,14})")

_MOBILE_PATTERNS = {"none", "spaces", "grouped", "words", "5-5", "3-3-4", "4-3-3", "2-2-2-2-2"}
_LONG_NUMBER_MODES = {"none", "digits", "grouped", "ones", "tens", "hundreds", "group_2", "group_3", "group_4", "group_5"}
_INDIAN_LABELS = ["thousand", "lakh", "crore", "arab", "kharab", "neel", "padma", "shankh"]

_GROUPING = {
	"digits": (1, True),
	"grouped": (3, False),
	"ones": (1, False),
	"tens": (2, False),
	"hundreds": (3, False),
	"group_2": (2, True),
	"group_3": (3, True),
	"group_4": (4, True),
	"group_5": (5, True),
}


def is_digit_char(ch: str) -> bool:
	"""Returns True for any Unicode decimal digit (ASCII, Arabic, Devanagari, etc.)."""
	return unicodedata.category(ch) == "Nd"


def unicode_digits_to_ascii(text: str) -> str:
	"""Converts any regional Unicode decimal digits in text to standard ASCII digits 0-9."""
	out = []
	for ch in text:
		if unicodedata.category(ch) == "Nd":
			try:
				out.append(str(unicodedata.decimal(ch)))
			except ValueError:
				out.append(ch)
		else:
			out.append(ch)
	return "".join(out)


def _only_digits(text: str) -> str:
	return "".join(ch for ch in text if ch.isdigit())


def _group_from_right(digits: str, size: int):
	"""Splits digits into groups of size from right to left."""
	leftover = len(digits) % size
	groups = []
	if leftover > 0:
		groups.append(digits[:leftover])
	pos = leftover
	while pos < len(digits):
		groups.append(digits[pos:pos + size])
		pos += size
	return groups


def _digit_by_digit_groups(groups):
	return " ".join(" ".join(ch for ch in g) for g in groups)


def reserve_mobile(text: str, pattern: str = "spaces") -> str:
	"""
	Phase 1: Identifies mobile phone numbers and reserves them with MOBILE_MARKER
	so script segmentation does not break them apart.
	"""
	if pattern == "none" or not pattern:
		return text

	def _mark(m):
		digits = _only_digits(m.group(0))
		return MOBILE_MARKER + " ".join(digits)

	return _MOBILE_REGEX.sub(_mark, text)


def expand_reserved_mobile(text: str, pattern: str = "spaces") -> str:
	"""
	Phase 2: Expands MOBILE_MARKER into spoken grouped digits.
	"""
	if pattern == "none" or not pattern:
		return text.replace(MOBILE_MARKER, "")

	def _expand(m):
		full = "".join(ch for ch in m.group(1) if ch.isdigit())
		if pattern == "spaces" or pattern == "words":
			return " ".join(full)
		elif pattern == "grouped":
			if len(full) == 11 and full.startswith("0"):
				return full[:4] + " " + full[4:]
			elif len(full) >= 10:
				return full[:5] + " " + full[5:]
			return " ".join(full)
		# Hyphenated patterns like 5-5
		try:
			sizes = [int(s) for s in pattern.split("-")]
			res = []
			pos = 0
			for s in sizes:
				res.append(full[pos:pos + s])
				pos += s
			if pos < len(full):
				res.append(full[pos:])
			return " ".join(res)
		except Exception:
			return " ".join(full)

	return _RESERVED_MOBILE_REGEX.sub(_expand, text)


def _group_long_numbers(text: str, mode: str, accept_func):
	if mode == "none" or mode not in _GROUPING:
		return text
	group_size, digit_by_digit = _GROUPING[mode]

	def _rewrite(m):
		int_part = m.group(1)
		frac_part = m.group(2) or ""
		digits = _only_digits(int_part)
		if not accept_func(len(digits)):
			return m.group(0)
		groups = _group_from_right(digits, group_size)
		grouped = _digit_by_digit_groups(groups) if digit_by_digit else " ".join(groups)
		return grouped + frac_part

	return _NUMBER_REGEX.sub(_rewrite, text)


def rewrite_long_numbers(text: str, mode: str = "grouped", min_digits: int = 5, crore_lakh: bool = True, crore_lakh_enabled: bool = None) -> str:
	"""
	Groups long digit strings (IDs, account numbers, etc.) according to chosen mode.
	If crore_lakh is enabled, skips 6-9 digit numbers so they can be read as lakh/crore.
	"""
	if crore_lakh_enabled is not None:
		crore_lakh = crore_lakh_enabled
	return _group_long_numbers(
		text,
		mode,
		lambda n: n >= min_digits and not (crore_lakh and 6 <= n <= 9)
	)


def rewrite_deferred_long_numbers(text: str, mode: str = "group_5", min_digits: int = 10) -> str:
	"""Groups 6-9 digit numbers on non-English runs when crore_lakh is enabled."""
	return _group_long_numbers(text, mode, lambda n: 6 <= n <= 9 and n >= min_digits)


def _format_indian_integer(int_part_raw: str) -> str:
	int_part = int_part_raw.lstrip("0") or "0"
	if len(int_part) <= 3:
		return int_part
	last3 = int_part[-3:]
	rest = int_part[:-3]
	pairs = []
	while rest:
		take = 2 if len(rest) >= 2 else 1
		pairs.insert(0, rest[-take:])
		rest = rest[:-take]
	parts = []
	for i, pair in enumerate(pairs):
		label_idx = len(pairs) - 1 - i
		if label_idx >= len(_INDIAN_LABELS):
			continue
		label = _INDIAN_LABELS[label_idx]
		value = int(pair) if pair else 0
		if value != 0:
			parts.append(f"{value} {label}")
	last3_value = int(last3) if last3 else 0
	if last3_value != 0:
		parts.append(str(last3_value))
	return " ".join(parts) if parts else "0"


def rewrite_crore_lakh(text: str, enabled: bool = True) -> str:
	"""
	Formats 6-9 digit numbers into Indian lakh/crore format for English runs.
	"""
	if not enabled:
		return text

	def _rewrite(m):
		int_part = m.group(1)
		frac_part = m.group(2) or ""
		digits = _only_digits(int_part)
		if not (6 <= len(digits) <= 9):
			return m.group(0)
		return _format_indian_integer(digits) + frac_part

	return _NUMBER_REGEX.sub(_rewrite, text)
