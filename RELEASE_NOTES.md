## What's new in 1.1.0

Version 1.1.0 is a major update to Auto TTS for NVDA, bringing core audio engine optimizations, improved multilingual detection, and enhanced synthesizer stability:

- **ETI Eloquence 16kHz audio stutter fix**: Resolved audio buffer resets and end-of-utterance playback stutter on ETI Eloquence through consecutive speech chunk merging, property dirty-state checks, and excluding internal sentinel engines from duplicate trailing index markers.
- **Instant voice loading and smart voice matching**: Fixed voice list population in the settings dialog, cached voices across synthesizers for instantaneous switching without UI delay, and introduced smart language-to-voice auto-matching while strictly respecting saved profile selections.
- **Offline shared-script language disambiguation**: Added dedicated offline n-gram models and character heuristics to accurately distinguish Perso-Arabic languages (Urdu, Arabic, Persian), Devanagari languages (Hindi, Marathi, Nepali), and Bengali. Includes a pure-Python fallback for systems without native FastText binaries.
- **Enhanced number processing**: Added support for regional Unicode digits (Eastern Arabic/Urdu, Devanagari), preserved formatted numbers (decimals, dates, phone numbers) as continuous tokens, and simplified large number reading into a clean choice between Western (Millions/Billions) and Indian (Lakh/Crore) numbering systems.
- **Diagnostic activity logging**: Added lightweight activity logging to "Auto TTS log.txt" in your Documents folder with automatic privacy redaction of spoken text and a convenient shortcut under NVDA Preferences.
- **Synthesizer stability and Say All support**: Improved index forwarding for continuous reading in Say All (NVDA+DownArrow), bypassed complex language models during single-character and spelling navigation to prevent accent glitches, and added recursive engine guards.
- **NVDA 2026.3 compatibility**: Fully verified and compatible with NVDA 2026.3.

## About Auto TTS for NVDA

Auto TTS detects the language of the text NVDA reads and switches to the voice you chose for that language. It works offline and is built for mixed Urdu, Arabic and English, and it supports many other languages.

Download **autoTTS-1.1.0.nvda-addon**, open the file and restart NVDA. Then open **Preferences > Settings > Auto TTS for NVDA** (or press **NVDA+Alt+A**), add a profile for each language, and press **NVDA+Ctrl+S** to select **Auto TTS for NVDA** as your synthesizer.

Minimum NVDA version: **2023.3**. Last tested NVDA version: **2026.3**.

Author: **Raja Hamid**.
