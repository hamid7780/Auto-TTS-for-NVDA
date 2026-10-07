# Changelog

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
