# Changelog

## 1.0.0

First public release. The public version sequence starts at 1.0.0.

- Automatic multilingual speech routing with per-language synthesizers, voices
  and optional custom rate, pitch and volume.
- Urdu/Arabic-aware rules, mixed-script detection and configurable word,
  sentence and line granularity.
- Offline fastText language identification with bundled runtimes for Python
  3.7 x86, 3.11 x86 and 3.13 x64; confidence and context safeguards for short
  or ambiguous samples.
- Document language-tag policy, math and number routing, application exclusions,
  session-only language lock, test speech, and settings import/export.
- Ordered speech chunks, index forwarding, cancellation safeguards and
  synthesizer prewarming for high-latency voices.
- Settings-ring support for configured profiles and their prosody.
- Recover profiles from missing, corrupt, invalid or unexpectedly empty
  settings, preserving a healthy backup during recovery.
- Validate imported profiles before changing live settings; preserve intentional
  resets across subsequent saves and persist removal of a final profile.
- Reject recursive Auto TTS child synthesizers in imported configurations.
- Accessible bundled help, version-driven packaging, SHA-256 checksums, and
  automated GitHub checks and tagged releases.
