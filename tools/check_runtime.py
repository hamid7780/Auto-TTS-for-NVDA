"""Check the real bundled detector in a supported Windows Python runtime."""

from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synthDrivers.autoTTS import statisticalDetection


def main():
    if not statisticalDetection.is_available():
        raise RuntimeError("Bundled fastText runtime or language model failed to load")
    samples = {
        "en": "This is a complete English sentence about reading books and using a computer every day.",
        "fr": "Cette phrase est ecrite en francais et parle de la lecture des livres dans une bibliotheque.",
    }
    for expected, sample in samples.items():
        actual = statisticalDetection.detect_language(sample, {"en": "en", "fr": "fr"})
        if actual != expected:
            raise RuntimeError("Expected {} detection, got {}".format(expected, actual))
    print("Bundled model smoke check passed: Python {} {}".format(
        platform.python_version(), platform.architecture()[0]))


if __name__ == "__main__":
    main()
