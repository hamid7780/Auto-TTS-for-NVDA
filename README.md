# Auto TTS for NVDA

Auto TTS switches between your configured voices and synthesizers while NVDA
reads multilingual text. Give each language its own voice, rate, pitch and
volume, then read mixed-language content without manually switching voices.

- **Author:** Raja Hamid
- **Version:** 1.0.0
- **Release channel:** Stable
- **Minimum NVDA version:** 2023.3
- **Last tested NVDA version declared in the manifest:** 2026.1.1
- **License:** GNU General Public License, version 2; bundled components have
  their own licenses listed in [third-party notices](THIRD_PARTY_NOTICES.txt).

[Download the latest release](https://github.com/hamid7780/autoTTS/releases/latest)
| [Report a problem](https://github.com/hamid7780/autoTTS/issues)
| [Changelog](CHANGELOG.md)

## Features

- A synthesizer and voice profile for each language, with optional custom
  rate, pitch and volume.
- Mixed-script switching in the original text order, including Urdu/English.
- Urdu/Arabic detection using script-specific characters and Quranic marks.
- Word, sentence and line detection modes.
- Bundled offline fastText detection for configured languages that share a
  script, such as English/French/Spanish and Russian/Ukrainian.
- Confidence and context checks to avoid unnecessary switching for short
  samples, URLs, email addresses, paths and code-like filenames.
- A choice to detect language from text or trust document language tags.
- Math-language and number-language settings.
- Temporary language lock, application exclusions, and accessible test speech.
- Settings import/export and recovery backups.
- NVDA settings-ring support for configured profiles and their prosody.

## Install

1. Download `autoTTS-1.0.0.nvda-addon` from the
   [release page](https://github.com/hamid7780/autoTTS/releases/tag/v1.0.0).
   GitHub's source-code ZIP is for developers and cannot be installed as an add-on.
2. Open the `.nvda-addon` file and follow NVDA's installation prompts.
3. Restart NVDA.
4. Open **NVDA menu > Preferences > Settings > Auto TTS**, or press
   **NVDA+Alt+A**, to configure your language profiles.
5. Open NVDA's **Select Synthesizer** dialog with **NVDA+Ctrl+S**, choose
   **Auto TTS for NVDA**, and confirm.

Install additional synthesizer add-ons and voices separately before choosing
them in Auto TTS. eSpeak NG is available as a fallback. Users do not need to
install Python, fastText or a separate language model.

If you used a development package with a higher version number, NVDA may treat
1.0.0 as a downgrade. Export your Auto TTS settings first, then follow NVDA's
prompts to replace the package. The add-on ID remains `autoTTS`, and settings
remain outside the package directory.

## Configure language profiles

1. Add a profile for each language you want to use, for example English and Urdu.
2. Assign each profile an installed synthesizer and one of its voices.
3. Enable custom prosody for profile-specific rate, pitch and volume.
   Otherwise the profile uses the underlying synthesizer's settings.
4. Choose your usual language as the default. A fresh installation initially
   follows NVDA's language.
5. Keep **Word-by-Word** for several writing scripts in one sentence.
   Try sentence or line mode when switching is too frequent.
6. Use **Detect from text** for unreliable document language tags, or
   **Trust document language tags** for correctly tagged content.
7. Use **Test Speech** to check the profiles, then save settings.

Offline same-script detection only selects enabled profiles. It does not
create profiles or download voices. Very short or ambiguous text may keep
the current language. Arabic-script text uses dedicated Urdu/Arabic rules.

Math follows the currently speaking language by default; you can select an
enabled profile for math instead. Number-language behavior is configurable.
Excluded applications use the selected default profile without automatic
switching. Common editors and terminals are excluded initially; edit the
exclusions list if you want switching in those applications.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| NVDA+Alt+A | Open Auto TTS settings |
| NVDA+Shift+L | Toggle automatic language switching |
| NVDA+Alt+L | Choose a language profile to lock, or unlock |
| NVDA+Ctrl+T | Announce Auto TTS status and language lock |
| NVDA+Ctrl+Left/Right | Select a synthesizer settings-ring item |
| NVDA+Ctrl+Up/Down | Change the selected settings-ring value |

Reassign shortcuts under **NVDA menu > Preferences > Input gestures > Auto TTS**.
Language lock lasts only for the current session. The ring lists configured
profiles; custom prosody edits apply to the selected profile, and other prosody
edits apply to its underlying synthesizer.

## Settings, privacy and troubleshooting

Settings are in `addons/autoTTS.json` inside NVDA's user configuration directory.
The previous complete settings are kept in `autoTTS.json.bak`. Auto TTS can
recover profiles from missing, corrupt or unexpectedly empty settings.
Use **Export Settings** for a separate `.autotts` or JSON backup and
**Import Settings** to restore it.

Language identification runs locally. Auto TTS does not download a model or
upload text for detection. A selected third-party synthesizer may use an online
service; its network behavior and privacy policy still apply.

If the wrong voice speaks, check that Auto TTS is the active synthesizer, the
profile is enabled, language lock is off, the app is not excluded, and the
voice supports the language. If same-script detection cannot load, Unicode
and document-tag routing remain available. Sequential mixed-synth speech
depends on reliable completion notifications from the underlying drivers.

For bug reports, include NVDA and Auto TTS versions, synthesizers, voices,
relevant settings, sample text and reproduction steps. Remove private content
from samples and logs before posting.

## Build and test

Contributors need Python 3.7 or later. The regression suite and packager use
the standard library:

```powershell
python -m unittest discover -s tests -v
python build.py
```

On Windows, `./build.ps1` is equivalent. The output is
`autoTTS-1.0.0.nvda-addon` and a SHA-256 checksum file in the project directory.
Use `python build.py --output-dir dist` to select another output directory.
The version and filename come from `manifest.ini`.

GitHub Actions runs regression tests and actual bundled-model smoke checks on
Python 3.7 x86, 3.11 x86 and 3.13 x64, corresponding to the included NVDA runtime
generations. Successful version-tag builds publish an add-on and checksum in
GitHub Releases. See [publishing](docs/PUBLISHING.md).

Standalone tests use NVDA stubs. Hands-on verification remains necessary for
reading by line, Say All, rapid navigation, cancellation, math output, settings
dialogs, the settings ring and third-party voices. Compatibility metadata is
retained from the existing project; release preparation does not establish
testing on every declared NVDA version.

## Contributing and licenses

Open an issue for bugs or larger changes. Include reproduction steps and
relevant regression coverage with code changes. Never commit user settings,
credentials or generated release packages.

Auto TTS source is distributed under [GPL version 2](LICENSE.txt). The bundled
fastText prediction runtime uses the MIT License, and `lid.176.ftz` uses
CC BY-SA 3.0. [Third-party notices](THIRD_PARTY_NOTICES.txt) include attribution,
sources and license links. [Review notes](docs/CODE_REVIEW.md) document the
release review and remaining manual checks.
