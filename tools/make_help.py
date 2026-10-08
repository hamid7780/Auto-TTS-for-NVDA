"""Build doc/en/readme.html, the help page shown inside NVDA, from README.md.

README.md is the only place the user guide is written. This script turns the
small subset of Markdown used there into HTML so the two never drift apart.

    python tools/make_help.py          write doc/en/readme.html
    python tools/make_help.py --check  fail if the file is out of date
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MANIFEST = ROOT / "manifest.ini"
OUTPUT = ROOT / "doc" / "en" / "readme.html"

STYLE = (
    "body{font-family:Segoe UI,Arial,sans-serif;max-width:48em;margin:1em auto;"
    "padding:0 1em;line-height:1.5}"
    "table{border-collapse:collapse;width:100%}"
    "caption{text-align:left;font-weight:bold;padding:.3em 0}"
    "th,td{border:1px solid #777;padding:.4em .6em;text-align:left;vertical-align:top}"
    "code{font-family:Consolas,monospace}"
)


def manifestValue(key):
    text = MANIFEST.read_text(encoding="utf-8")
    match = re.search(r"^" + re.escape(key) + r"\s*=\s*\"?([^\"\r\n]+)\"?\s*$", text, re.M)
    if not match:
        raise SystemExit("manifest.ini has no " + key)
    return match.group(1).strip()


def inline(text):
    parts = re.split(r"(`[^`]+`)", text)
    result = []
    for part in parts:
        if len(part) > 1 and part.startswith("`") and part.endswith("`"):
            result.append("<code>" + html.escape(part[1:-1], quote=False) + "</code>")
            continue
        escaped = html.escape(part, quote=False)
        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: '<a href="' + m.group(2).replace('"', "&quot;") + '">' + m.group(1) + "</a>",
            escaped,
        )
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        result.append(escaped)
    return "".join(result)


BLOCK_START = re.compile(r"^(#{1,3} |\||- |\d+\. |```|<)")


def convert(markdown, version):
    lines = markdown.replace("\r\n", "\n").split("\n")
    out = []
    lastHeading = ""
    versionAdded = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        heading = re.match(r"(#{1,3}) (.*)", line)
        if heading:
            level = len(heading.group(1))
            lastHeading = heading.group(2).strip()
            out.append("<h%d>%s</h%d>" % (level, inline(lastHeading), level))
            if level == 1 and not versionAdded:
                out.append("<p>Version %s.</p>" % html.escape(version))
                versionAdded = True
            i += 1
            continue
        if line.startswith("<"):
            out.append(line.strip())
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            header, body = rows[0], rows[2:]
            table = ["<table>", "<caption>%s</caption>" % inline(lastHeading), "<thead><tr>"]
            table += ['<th scope="col">%s</th>' % inline(cell) for cell in header]
            table.append("</tr></thead>")
            table.append("<tbody>")
            for row in body:
                table.append("<tr>" + "".join("<td>%s</td>" % inline(cell) for cell in row) + "</tr>")
            table += ["</tbody>", "</table>"]
            out.append("\n".join(table))
            continue
        listMatch = re.match(r"(- |\d+\. )", line)
        if listMatch:
            ordered = listMatch.group(1) != "- "
            tag = "ol" if ordered else "ul"
            pattern = r"\d+\. " if ordered else r"- "
            items = []
            while i < len(lines) and re.match(pattern, lines[i]):
                item = re.sub(r"^" + pattern, "", lines[i])
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                    item += " " + lines[i].strip()
                    i += 1
                items.append("<li>%s</li>" % inline(item))
            out.append("<%s>\n%s\n</%s>" % (tag, "\n".join(items), tag))
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip() and not (paragraph and BLOCK_START.match(lines[i])):
            paragraph.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(paragraph)))
    return "\n".join(out)


def build():
    title = "Auto TTS for NVDA"
    body = convert(README.read_text(encoding="utf-8"), manifestValue("version"))
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>\n"
        % (title, STYLE, body)
    )


def main(argv):
    expected = build()
    if "--check" in argv:
        current = OUTPUT.read_text(encoding="utf-8").replace("\r\n", "\n") if OUTPUT.exists() else ""
        if current != expected:
            print("doc/en/readme.html is out of date. Run: python tools/make_help.py")
            return 1
        print("doc/en/readme.html is up to date.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print("Wrote", OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
