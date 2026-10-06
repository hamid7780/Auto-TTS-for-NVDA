# Release review: 1.0.0

Reviewed the speech routing and completion logic, language detection, settings
persistence, settings import/export, profile lifecycle and package contents.
This is a source review with standalone automated checks; it is not a claim
that every underlying synthesizer has been tested inside NVDA.

## Findings addressed

- A corrupt or structurally invalid primary settings file prevented recovery
  from a valid backup. Load now validates each candidate independently and
  recovers populated backup profiles. Save preserves the healthy backup when
  repairing an invalid primary file.
- Malformed imported profile values could partially replace live settings
  before an exception. Profiles are now parsed before any live settings change.
- Saves after Reset All could be refused because the previous backup still
  contained profiles. An explicit reset remains intentional across later saves
  and reloads. Explicit removal of a final profile also persists.
- An imported profile could select autoTTS itself as a child synthesizer,
  recursively constructing routing drivers. The child factory now rejects that
  route and lets the normal fallback path run.
- The old packager hard-coded a development filename and had no bundled NVDA
  help entry. Packaging now derives names from the manifest, includes accessible
  HTML help and licenses, excludes caches, and writes SHA-256 checksums.

Each behavioral fix has regression coverage. The GitHub workflow additionally
loads the actual native runtimes and model in supported Windows Python versions.

## Verification boundaries

The original compatibility metadata (NVDA 2023.3 minimum, 2026.1.1 last tested)
is retained. The preparation environment uses Python 3.14, which is not one of
the bundled native detector ABIs. Local routing/persistence tests use NVDA stubs;
native smoke checks must run on Python 3.7 x86, 3.11 x86 and 3.13 x64 in CI.

Before claiming compatibility with additional NVDA versions, perform hands-on
checks for reading by line, Say All, rapid arrow navigation, cancellation,
math/MathCAT output, profile dialogs, language lock, import/export, settings-ring
edits and transitions between actual installed synthesizers. In particular,
third-party synth completion behavior and Google TTS runtime behavior require
real NVDA verification.
