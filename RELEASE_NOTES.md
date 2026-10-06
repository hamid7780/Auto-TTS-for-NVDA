Auto TTS 1.0.0 is the first public release of a multilingual synthesizer and
voice manager for NVDA. The public version sequence starts at 1.0.0.

Configure a synthesizer and voice for each language, with optional custom
rate, pitch and volume. Includes mixed-script switching, Urdu/Arabic-aware
rules, offline same-script detection, language lock, application exclusions,
math routing, settings import/export and recovery safeguards.

Download **autoTTS-1.0.0.nvda-addon**, open it with NVDA and restart NVDA.
Configure profiles under **NVDA Settings > Auto TTS**, then select
**Auto TTS for NVDA** with **NVDA+Ctrl+S**. Python is not required for users.

Minimum NVDA version: **2023.3**. Last tested version declared in the manifest:
**2026.1.1**. Install additional synthesizers and voices separately.

The review fixed settings recovery, backup preservation, invalid profile imports,
saves following explicit resets, and recursive child routes. Automated checks
cover routing and persistence, plus native detection on the bundled runtime
generations. Hands-on NVDA and third-party voice testing remains separate.

Users of higher-numbered development packages should export settings before
replacing their package with 1.0.0. A SHA-256 checksum is attached for verifying
the download. GitHub's source archives are for developers.
