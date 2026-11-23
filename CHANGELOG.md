# Changelog

## 1.2.0

- Fixed silent symbol lines: a line, or a character you move to or type, that holds only symbols such as `؟`, `۔` or `؎` is now read by name in the language of its script with every synthesizer, including eSpeak NG. Punctuation inside a sentence is no longer switched to another voice.
- Fixed honorific signs: `ؐ ؑ ؒ ؓ` and the ligatures `ﷲ ﷺ ﷻ ﷽` are always read as the words they stand for, alone or inside a sentence. A sign after a space or after an English word is no longer silent.
- Fixed names of symbols being spelled letter by letter while moving by character.
- Fixed text in the same language as the end of the previous utterance being read with the default voice when NVDA did not interrupt speech in between.
- Fixed rate, pitch and volume changes from the synthesizer settings ring not being heard until the language changed, for profiles with custom rate, pitch and volume.
- Fixed the settings panel starting a second copy of a synthesizer that was already speaking, and never closing the copies it made. Test Speech now also stops Auto TTS speech before playing.
- Fixed Reset All saving before every setting was reset, and resetting number settings to values different from a new installation.
- Fixed Arabic and Persian dates being read with Urdu month names.
- Fixed a Say All chunk at a slow speech rate being cut off by the safety timer, and paused speech being skipped.
- NVDA's role and state names (link, button, checked) are no longer sent to the FastText model, so they keep the right voice.
- NVDA now looks up symbols and character descriptions in the correct regional table for profiles such as `ur-PK` and `pa-PK`, instead of falling back to English.
- The Urdu and Punjabi symbol dictionary is registered the way NVDA supports for add-ons, and appears in NVDA's speech settings as "Auto TTS Urdu and Punjabi symbols".
- The activity log is written in the background, so logging no longer delays speech. The log header now shows the real add-on version.
- Rewrote Arabic-script detection. A sentence is judged as a whole, so Arabic sentences and the Basmala are no longer partly read as Urdu, and a quoted Arabic phrase inside Urdu still gets the Arabic voice. Persian, Pashto and Sindhi profiles are now used: before, letters these languages share with Urdu sent all of them to Urdu. Urdu typed on an Arabic keyboard stays Urdu.
- Fixed sentence and line mode reading an Urdu sentence with two English words in English: languages are now counted by words, not letters.
- Fixed Auto TTS telling NVDA that speech had finished while more of the utterance was still queued.
- Fixed a possible freeze with SAPI5 voices and timers created on a synthesizer's audio thread: completion reports are now handled on NVDA's main thread.
- Relative pitch, rate and volume changes (such as the higher pitch for capitals) are measured against the voice that speaks, without changing NVDA's own speech classes.
- Rate, pitch and volume changes from the settings ring are saved once after you stop changing them, not on every key press.
- Every configured synthesizer and the shared-script language models are now started shortly after NVDA starts, so the first switch to another voice does not wait for them.
- The language lock is now also in NVDA's synthesizer settings ring and Voice settings.
- Added a labeled Urdu, Arabic, Persian, Pashto, Sindhi and mixed-language test corpus.
- Removed unused code and left-over files, and restored regression tests that had been deleted.

## 1.1.2

- Differentiated Punjabi scripts: separated Punjabi (Gurmukhi) (India) and Punjabi (Shahmukhi) (Pakistan) with clear native naming in settings and language selection.
- Fixed symbol routing during typing and deletion: language-specific punctuation and symbols (such as Urdu khatma `۔`, Arabic comma `،`, and question mark `؟`) now correctly route to the matching language synthesizer rather than remaining silent or falling back to English.
- Added dedicated Date reading format options: dates (e.g. 2026-11-17, 17/11/2026) can now be spoken with localized month names, as digits, or left to synthesizer default.
- Added dedicated Other numbers format options: separate control for general numbers (synthesizer default, spaced digits, or grouped clusters).
- Fixed mobile phone number matching: refined mobile regex so dates, timestamps, and 4-digit years are never incorrectly matched or read as spaced digits.
- Tested and verified fully compatible with NVDA 2026.3.1.

## 1.1.1

- Fixed NVDA Add-on Store crash: moved configuration file from `addons\autoTTS.json` to `autoTTS.json` in NVDA's user configuration folder, preventing collisions with NVDA's internal Add-on Store cache. Existing user profiles are automatically migrated and the conflicting file is cleanly removed.
- Fixed mixed-language speech routing: resolved an issue where pre-warming during English playback could cause subsequent Urdu or secondary language chunks to be dropped or routed to the wrong synthesizer.
- Optimized activity log: reduced maximum log size to 1 MB with automated rotation, and silenced background speech events when text logging is disabled.

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
