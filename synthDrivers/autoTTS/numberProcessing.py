# Auto TTS for NVDA - Advanced Number, Date, Time & Phone Processing
# Covered by GNU General Public License (GPL)

import re

# Private-Use-Area marker: unambiguous tag for reserved mobile numbers
MOBILE_MARKER = "\uE000"
# Private-Use-Area marker: unambiguous tag for reserved dates
DATE_MARKER = "\uE001"

MONTHS_EN = [
	"", "January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"
]
MONTHS_UR = [
	"", "جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون",
	"جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"
]

# Standard dates (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY)
_DATE_REGEX = re.compile(
	r"(?<![\w])"
	r"(?:"
	r"((?:19|20)\d{2})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])"
	r"|"
	r"(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.]((?:19|20)\d{2})"
	r")"
	r"(?![\w])"
)

_RESERVED_DATE_REGEX = re.compile(DATE_MARKER + r"(\d{4})\|(\d{1,2})\|(\d{1,2})\|([a-z]+)\|([/.-])")

# Mobile phone number: optional +CC followed by national mobile number (10-12 digits with optional spaces or dashes).
# Must strictly match valid phone formats and never match dates (YYYY-MM-DD or DD/MM/YYYY) or general 4-digit numbers.
_MOBILE_REGEX = re.compile(
	r"(?<![\w])"
	r"(?:(?:\+|00)[1-9]\d{0,2}[ -]?)?"
	r"(?:0\d{2,3}[ -]?\d{3}[ -]?\d{4}|0\d{2,3}[ -]?\d{6,8}|03\d{2}[ -]?\d{7}|3\d{2}[ -]?\d{7}|[6-9]\d{4}[ -]?\d{5}|0\d{9,10})"
	r"(?![\w/.-])"
)

# Standard integer/decimal number: optionally comma-separated digits with optional decimal point
_NUMBER_REGEX = re.compile(r"(\d+(?:,\d+)*)(\.\d+)?")

# Reserved mobile marker regex
_RESERVED_MOBILE_REGEX = re.compile(MOBILE_MARKER + r"(\d(?: \d){9,14})")

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
		if pattern == "spaces":
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


def reserve_dates(text: str, mode: str = "default") -> str:
	"""
	Phase 1: Identifies dates and marks them with DATE_MARKER so they are not
	broken up or misidentified by mobile or script segmentation.
	"""
	if mode == "default" or not mode:
		return text

	def _mark(m):
		orig = m.group(0)
		sep = "/" if "/" in orig else ("." if "." in orig else "-")
		if m.group(1):
			y, mo, d = m.group(1), m.group(2), m.group(3)
			order = "ymd"
		else:
			d, mo, y = m.group(4), m.group(5), m.group(6)
			order = "dmy"
		return f"{DATE_MARKER}{y}|{mo}|{d}|{order}|{sep}"

	return _DATE_REGEX.sub(_mark, text)


def expand_reserved_dates(text: str, mode: str = "default", lang: str = "en") -> str:
	"""
	Phase 2: Expands DATE_MARKER into the user-selected date format.
	"""
	if DATE_MARKER not in text:
		return text

	def _expand(m):
		y, mo_str, d_str, order, sep = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
		y_int, mo_int, d_int = int(y), int(mo_str), int(d_str)
		if mode == "default":
			if order == "ymd":
				return f"{y}{sep}{mo_str}{sep}{d_str}"
			return f"{d_str}{sep}{mo_str}{sep}{y}"

		# Urdu month names are also used in Shahmukhi Punjabi; Arabic and Persian name
		# the months differently, so they keep the English names their voices read.
		tag = (lang or "en").lower().replace("_", "-")
		months = MONTHS_UR if tag.split("-")[0] in ("ur", "pnb") or tag in ("pa-pk", "pa-arab") else MONTHS_EN
		mname = months[mo_int] if 1 <= mo_int <= 12 else mo_str

		if mode == "day_month_name_year":
			return f"{d_int} {mname} {y_int}"
		elif mode == "month_name_day_year":
			return f"{mname} {d_int}, {y_int}"
		elif mode == "day_month_year":
			return f"{d_int} {mo_int} {y_int}"
		elif mode == "year_month_day":
			return f"{y_int} {mo_int} {d_int}"
		return m.group(0)

	return _RESERVED_DATE_REGEX.sub(_expand, text)


def rewrite_other_numbers(text: str, mode: str = "default", crore_lakh: bool = True) -> str:
	"""
	Formats general/other numbers according to chosen format.
	- 'default': Synthesizer default reading (standard integers/numbers left alone).
	- 'digits': Individual spaced digits (e.g. 1 2 3 4).
	- 'grouped': Grouped in clusters of 3 digits.
	"""
	if mode == "default" or not mode or mode == "none":
		return text

	def _rewrite(m):
		matched = m.group(0)
		if MOBILE_MARKER in matched or DATE_MARKER in matched:
			return matched
		int_part = m.group(1)
		frac_part = m.group(2) or ""
		digits = _only_digits(int_part)
		if not digits:
			return matched
		if crore_lakh and 6 <= len(digits) <= 9:
			return matched
		if mode == "digits":
			return " ".join(digits) + frac_part
		elif mode == "grouped":
			groups = _group_from_right(digits, 3)
			return " ".join(groups) + frac_part
		return matched

	return _NUMBER_REGEX.sub(_rewrite, text)


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


def rewrite_long_numbers(text: str, mode: str = "grouped", min_digits: int = 5, crore_lakh: bool = True) -> str:
	"""
	Groups long digit strings (IDs, account numbers, etc.) according to chosen mode.
	If crore_lakh is enabled, skips 6-9 digit numbers so they can be read as lakh/crore.
	"""
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
