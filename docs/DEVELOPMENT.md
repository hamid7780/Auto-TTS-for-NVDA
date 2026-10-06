# Development

Auto TTS requires Python 3.7 or later for source checks and packaging.

## Build and test

Run from the repository directory:

```powershell
python -m unittest discover -s tests -v
python build.py
```

The build creates a versioned `.nvda-addon` package and SHA-256 checksum.
The version and filename are read from `manifest.ini`.
Use `python build.py --output-dir dist` to select an output directory.

GitHub Actions runs the regression suite and bundled language-model checks on
Windows with Python 3.7 x86, 3.11 x86 and 3.13 x64. Version tags publish releases
after these checks pass. See [Publishing](PUBLISHING.md).

## Verification

Automated tests cover language routing, speech ordering, profile settings,
configuration persistence and packaging. NVDA APIs are stubbed in the standalone
suite. Test changes inside NVDA as appropriate, including Say All, cancellation,
settings dialogs, keyboard shortcuts and transitions between synthesizers.

## Contributions

Include reproduction steps and relevant regression coverage with bug fixes.
Do not commit local user settings, credentials or generated packages.
