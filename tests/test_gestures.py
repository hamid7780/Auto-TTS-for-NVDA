"""The add-on's default keyboard shortcuts must not take over NVDA's own commands."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keyboard commands that NVDA 2026.3.1 assigns to NVDA+modifier+letter, from its user guide
# and the gesture maps in its program files. The add-on store rejects add-ons that reuse them.
NVDA_COMMANDS = {
	"nvda+alt+c", "nvda+alt+j", "nvda+alt+k", "nvda+alt+l", "nvda+alt+m", "nvda+alt+r",
	"nvda+alt+s", "nvda+alt+t",
	"nvda+control+1", "nvda+control+2", "nvda+control+a", "nvda+control+b", "nvda+control+c",
	"nvda+control+d", "nvda+control+f", "nvda+control+g", "nvda+control+k", "nvda+control+m",
	"nvda+control+o", "nvda+control+p", "nvda+control+r", "nvda+control+s", "nvda+control+t",
	"nvda+control+u", "nvda+control+v", "nvda+control+w", "nvda+control+x",
	"nvda+control+alt+t",
	"nvda+shift+a", "nvda+shift+b", "nvda+shift+c", "nvda+shift+d", "nvda+shift+f",
	"nvda+shift+i", "nvda+shift+l", "nvda+shift+m", "nvda+shift+n", "nvda+shift+o",
	"nvda+shift+r", "nvda+shift+s", "nvda+shift+w", "nvda+shift+z",
}


def normalize(gesture):
	"""Order modifiers the same way whatever order they were written in."""
	keys = gesture.lower().replace("ctrl", "control").split("+")
	return "+".join(sorted(keys[:-1]) + keys[-1:])


class GestureTests(unittest.TestCase):
	def test_default_gestures_do_not_reuse_nvda_commands(self):
		source = (ROOT / "globalPlugins" / "autoTTS" / "__init__.py").read_text(encoding="utf-8")
		gestures = re.findall(r'gesture\s*=\s*"kb:([^"]+)"', source)
		self.assertEqual(len(gestures), 4)
		taken = {normalize(g) for g in NVDA_COMMANDS}
		for gesture in gestures:
			self.assertNotIn(normalize(gesture), taken, gesture)
		self.assertEqual(len({normalize(g) for g in gestures}), len(gestures))


if __name__ == "__main__":
	unittest.main()
