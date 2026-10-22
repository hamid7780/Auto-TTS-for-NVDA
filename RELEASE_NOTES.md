## What's new in 1.1.0

- **Fixed speech queue deadlocks and dropped speech**: Typing rapidly (such as typing space followed by a symbol or dot), navigating lists, or switching between languages (e.g. English followed by Urdu or Hindi) no longer silences speech or freezes the speech queue.
- **Fixed ETI Eloquence 16kHz audio stuttering**: Consecutive speech chunks using the same voice are now merged into a single call, and voice properties are only reassigned when they actually change to prevent internal buffer resets.
- **Fixed voice auto-selection in Profile Editor**: Configured voices (such as American English) and synthesizer defaults are strictly preserved rather than arbitrarily defaulting to British English.
- **Simplified number reading**: Consolidated large number settings into a single clean choice between Western standard (Millions, Billions) and Indian system (Lakh, Crore), with full support for regional Unicode digits.
- **Improved shared-script regional language detection**: Added offline character heuristics and n-gram models for Perso-Arabic (Urdu, Arabic, Persian), Devanagari (Hindi, Marathi, Nepali), and Bengali.
- **Diagnostic activity logging**: Added lightweight diagnostic logging with privacy redaction and an NVDA Preferences shortcut for quick access.

## About Auto TTS for NVDA

Auto TTS detects the language of the text NVDA reads and switches to the voice you chose for that language. It works offline and is built for mixed Urdu, Arabic and English, and it supports many other languages.

Download **autoTTS-1.1.0.nvda-addon**, open the file and restart NVDA. Then open **Preferences > Settings > Auto TTS for NVDA** (or press **NVDA+Alt+A**), add a profile for each language, and press **NVDA+Ctrl+S** to select **Auto TTS for NVDA** as your synthesizer.

Minimum NVDA version: **2023.3**. Last tested NVDA version: **2026.2**.

Author: **Raja Hamid**.
