# Auto TTS for NVDA

Auto TTS automatically detects the language of text and switches between the
voices selected for each language. It helps NVDA read multilingual content,
including Urdu, Arabic and English.

[Download Auto TTS 1.0.0](https://github.com/hamid7780/autoTTS/releases/download/v1.0.0/autoTTS-1.0.0.nvda-addon)

## Features

- Choose a synthesizer and voice for each language.
- Set speech rate, pitch and volume for individual languages.
- Read mixed-language text with automatic voice switching.
- Use offline language detection or document language settings.
- Lock speech to one language, exclude applications, and import or export settings.

## Installation and setup

1. Download and open the add-on file, then follow NVDA's installation prompts.
2. Restart NVDA.
3. Open **NVDA menu > Preferences > Settings > Auto TTS**.
4. Add your language profiles, select their voices, and choose a default language.
5. Press **NVDA+Ctrl+S** and select **Auto TTS for NVDA** as the synthesizer.

Additional synthesizers and voices must be installed separately. Use **Test
Speech** in Auto TTS settings to check your selection.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| NVDA+Alt+A | Open Auto TTS settings |
| NVDA+Shift+L | Turn automatic language switching on or off |
| NVDA+Alt+L | Lock speech to a language or unlock it |
| NVDA+Ctrl+T | Announce Auto TTS status |

Shortcuts can be changed under **Preferences > Input gestures > Auto TTS**.

## Support

If a voice does not switch as expected, check that its language profile is
enabled, language lock is off, and the application is not excluded.
Some editors and terminals are excluded by default; this can be changed in settings.

[Report a problem](https://github.com/hamid7780/autoTTS/issues)
or view the [changelog](CHANGELOG.md). Include your NVDA version and the voices
used when reporting a problem.

## Compatibility and license

- Minimum NVDA version: **2023.3**
- Last tested NVDA version: **2026.1.1**
- Author: **Raja Hamid**

Licensed under [GNU GPL version 2](LICENSE.txt).
Bundled component licenses are listed in [third-party notices](THIRD_PARTY_NOTICES.txt).
Developer instructions are available in [Development](docs/DEVELOPMENT.md).
