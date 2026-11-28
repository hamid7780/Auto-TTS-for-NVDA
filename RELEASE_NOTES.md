## What's new in 1.2.1

Three keyboard shortcuts no longer clash with NVDA's own commands:

- **NVDA+Alt+Shift+A** turns automatic language switching on or off (was NVDA+Shift+L).
- **NVDA+Alt+Shift+L** locks or unlocks a language (was NVDA+Alt+L).
- **NVDA+Alt+Shift+T** says whether Auto TTS is on or locked (was NVDA+Ctrl+T).
- **NVDA+Alt+A** still opens the settings.

Keys you assigned yourself under Preferences, Input gestures are kept.

## Also in 1.2.0 (previous release)

Version 1.2.0 fixes how Auto TTS reads Urdu symbols and honorific signs, and fixes several long-standing bugs:

- **Symbols on their own are read**: a line, or a character you move to or type, that holds only symbols such as `؟`, `۔` or `؎` is read by name in the right language with every synthesizer, including eSpeak NG. Punctuation inside a sentence stays silent and no longer switches voices.
- **Honorific signs are always read**: `ؐ ؑ ؒ ؓ` and `ﷲ ﷺ ﷻ ﷽` are read as the words they stand for, alone, after an English word, or inside a sentence.
- **Settings ring changes are heard at once**: rate, pitch and volume changes for profiles with custom values apply from the next utterance.
- **Better Arabic-script detection**: whole Arabic sentences and the Basmala are read in Arabic, Arabic quotes inside Urdu get the Arabic voice, and Persian, Pashto and Sindhi profiles are finally used.
- **Language lock in the settings ring**: lock or unlock a language without opening a dialog.
- **Faster first switch**: configured synthesizers start shortly after NVDA does.
- **Correct voice after Urdu**: Urdu that follows Urdu is no longer sometimes read with the default voice.
- **Lighter settings panel**: it no longer starts a second copy of a synthesizer that is already speaking. Reset All now resets everything.
- **NVDA symbol dictionary**: Urdu and Punjabi symbol names are registered with NVDA (NVDA 2024.4 or newer) and NVDA uses the correct regional symbol tables for profiles such as `ur-PK`.
- **No more announced full stops**: `۔` and Arabic punctuation are no longer read out in the middle of Urdu sentences, and `؟` is read in Urdu when you move onto it.
- **Mis-tagged pages**: text tagged with a language you have no profile for is detected from the text, so dates no longer get foreign dash names.
- **Smoother speech with logging on**: the activity log is written in the background.

See the changelog for the full list.
