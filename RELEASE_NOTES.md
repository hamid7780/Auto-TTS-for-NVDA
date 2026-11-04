## What's new in 1.1.1

Version 1.1.1 is a maintenance release resolving an NVDA Add-on Store collision, fixing mixed-language speech playback, and optimizing diagnostic logs:

- **NVDA Add-on Store crash fix**: Moved user settings from `addons\autoTTS.json` to `autoTTS.json` in the NVDA user configuration folder. Previously, NVDA's Add-on Store mistook `autoTTS.json` for its own store cache, causing an unhandled KeyError when opening the store. Existing settings are automatically migrated and the conflicting file is cleanly removed.
- **Mixed-language speech switching fix**: Fixed an issue where reading mixed-language text (such as English followed by Urdu) caused the secondary language to be dropped or routed to the wrong synthesizer due to pre-warming state collisions.
- **Activity log optimization**: Capped log size at 1 MB with automatic rotation, and silenced redundant background speech events when text logging is disabled.

## About Auto TTS for NVDA

Auto TTS detects the language of the text NVDA reads and switches to the voice you chose for that language. It works offline and is built for mixed Urdu, Arabic and English, and it supports many other languages.

Download **autoTTS-1.1.1.nvda-addon**, open the file and restart NVDA. Then open **Preferences > Settings > Auto TTS for NVDA** (or press **NVDA+Alt+A**), add a profile for each language, and press **NVDA+Ctrl+S** to select **Auto TTS for NVDA** as your synthesizer.

Minimum NVDA version: **2023.3**. Last tested NVDA version: **2026.3**.

Author: **Raja Hamid**.
