# Development

Auto TTS needs Python 3.7 or later for the checks and for packaging. Nothing has to be installed from PyPI.

## Layout

| Path | Purpose |
| --- | --- |
| `synthDrivers/autoTTS/` | The synthesizer driver, language detection, configuration and the bundled fastText runtime |
| `globalPlugins/autoTTS/` | Keyboard shortcuts and the settings panel |
| `tests/` | Standalone test suite. NVDA is replaced by small stand-ins. |
| `tools/` | `make_help.py` builds the in-NVDA help page, `check_runtime.py` checks the bundled runtime |
| `build.py` | Builds the `.nvda-addon` package and its SHA-256 file |
| `docs/` | These development and publishing notes |

## Build and test

Run these from the repository folder:

```powershell
python -m unittest discover -s tests -v
python build.py
```

The build writes a versioned `.nvda-addon` file and a `.sha256` file next to `build.py`. The name and version come from `manifest.ini`. Use `python build.py --output-dir dist` to write them somewhere else. Both file types are ignored by git.

## The help page

The user guide is written once, in `README.md`. The page that NVDA shows from the add-on manager, `doc/en/readme.html`, is generated from it:

```powershell
python tools/make_help.py
```

Run this after every change to `README.md` or the version in `manifest.ini`. A test fails if the generated page is out of date.

## Checks

The tests cover language routing, speech ordering, profile settings, saved configuration, packaging, and that the documents agree with the manifest and the code. GitHub Actions runs them on Windows with Python 3.7 x86, 3.11 x86 and 3.13 x64, which match the three NVDA runtimes the add-on supports.

The tests cannot replace trying the package in NVDA. Before a release, install it and try Say All, cancelling speech with key presses, the settings dialogs, the shortcuts, and switching between synthesizers.

## Timing

When speech seems to start late, set NVDA's logging level to Debug. The driver then writes a line such as `AutoTTS: cancel took 4.2 ms (2 synths)` for any call that takes 3 ms or more.

## Contributing

Describe how to reproduce a bug, and add a test when you fix one. Do not commit local settings, credentials or built packages. Releases are described in [Publishing](PUBLISHING.md).
