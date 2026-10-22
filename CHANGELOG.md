# Changelog

## 1.1.0

- Fixed speech queue deadlocks and dropped speech during rapid typing (e.g. typing space then dot), list navigation, and language transitions (e.g. English followed by Urdu or Hindi).
- Fixed ETI Eloquence 16kHz audio stuttering and buffer resets by introducing consecutive speech chunk merging and dirty-state property checks.
- Fixed Voice combo box in profile editor dialog so saved voices (such as American English) and synthesizer native configured voices are strictly respected rather than arbitrarily defaulting to British English.
- Simplified large numbers reading options into a clean two-choice dropdown (Western Million/Billion vs Indian Lakh/Crore) and streamlined number settings.
- Added offline shared-script regional language disambiguation for Perso-Arabic (Urdu, Arabic, Persian), Devanagari (Hindi, Marathi, Nepali), and Bengali with character heuristics and n-gram models.
- Added pure-Python language detection fallback if binary FastText runtimes are unavailable.
- Added continuous lightweight diagnostic activity logging to Auto TTS log.txt with privacy redaction and NVDA Preferences menu shortcut.

## 1.0.1

- Fixed a long freeze when reading very long Arabic-script lines in line or sentence mode.
- Text containing slashes, such as "and/or" or "km/h", is language-detected again.
- Corrected the Japanese and Italian Test Speech sentences.
- Replaced the Unicode script dictionary with a compact range table to cut memory use and NVDA startup time.
- Removed unused code and the unused PowerShell build wrapper.
- Added regression tests and documented known limitations.

## 1.0.0

Initial release.

- Automatic language detection and voice switching for multilingual text.
- Per-language synthesizer, voice, speech rate, pitch and volume settings.
- Urdu/Arabic-aware detection and offline language identification.
- Word, sentence and line detection modes.
- Language lock, application exclusions, and math and number language settings.
- Settings import/export and keyboard shortcuts.
