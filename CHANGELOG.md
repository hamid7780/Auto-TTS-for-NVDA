# Changelog

## 1.1.0

- Major release introducing significant audio engine improvements, enhanced language detection, and stability updates.
- Fixed ETI Eloquence 16kHz audio stuttering and buffer resets through consecutive speech chunk merging, strict property dirty-state checks, and eliminating end-of-utterance trailing marker collisions.
- Fixed voice selection in Profile Editor: cached available voices per synthesizer for instant loading, fixed the "Default Voice" bug, and added smart voice matching for selected languages while strictly preserving saved choices.
- Added offline shared-script regional language disambiguation with character heuristics and n-gram models for Perso-Arabic (Urdu, Arabic, Persian), Devanagari (Hindi, Marathi, Nepali), and Bengali.
- Added pure-Python language detection fallback if binary FastText runtimes cannot be loaded.
- Added FastText detection caching (LRU cache) to eliminate UI latency on repeated words and phrases.
- Enhanced number processing: added support for regional Unicode digits (Arabic, Urdu, Devanagari), preserved formatted numbers as single unbroken units, and simplified large numbers reading into a clean choice between Western (Millions/Billions) and Indian (Lakh/Crore) numbering systems.
- Added lightweight diagnostic activity logging to "Auto TTS log.txt" in Documents with automated privacy redaction and an NVDA Preferences menu shortcut.
- Improved synthesizer stability: reliable Say All (NVDA+DownArrow) index forwarding, FastText bypass during single-character and spelling mode, recursive synthesizer exclusion guard, and clean sub-synthesizer termination on exit.
- Tested and verified fully compatible with NVDA 2026.3.

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
