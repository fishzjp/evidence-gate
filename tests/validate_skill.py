#!/usr/bin/env python3
"""Skill structural validation.

Checks that the repo is a valid, self-contained skill:
  1. SKILL.md exists and its YAML frontmatter has name / description / version
  2. description follows the "Use when..." trigger convention
  3. every relative file path referenced by SKILL.md actually exists
     (references/, examples/, scripts/, docs/, tests/)

Exit code: 0 valid, 1 invalid.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"


def main() -> int:
    errors, warnings = [], []
    if not SKILL.exists():
        print("INVALID: SKILL.md not found at repo root")
        return 1
    text = SKILL.read_text(encoding="utf-8")

    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        print("INVALID: SKILL.md has no YAML frontmatter block")
        return 1
    fm = m.group(1)

    name = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    desc = re.search(r"^description:\s*(.+)", fm, re.MULTILINE)
    version = re.search(r"^version:\s*(\S+)", fm, re.MULTILINE)
    if not name:
        errors.append("frontmatter missing 'name'")
    if not desc:
        errors.append("frontmatter missing 'description'")
    elif not desc.group(1).strip().lower().startswith("use when"):
        warnings.append("description should start with 'Use when...' "
                        "(trigger convention)")
    if not version:
        errors.append("frontmatter missing 'version'")
    else:
        script_ver = re.search(
            r"__version__\s*=\s*\"([^\"]+)\"",
            (ROOT / "scripts" / "gate_check.py").read_text(encoding="utf-8"))
        if script_ver and script_ver.group(1) != version.group(1):
            errors.append(f"version mismatch: SKILL.md={version.group(1)} "
                          f"gate_check.py={script_ver.group(1)}")

    # every markdown-relative path mentioned in SKILL.md must exist
    body = text[m.end():]
    for ref in set(re.findall(r"`((?:references|examples|scripts|docs|tests|"
                              r"benchmark)/[A-Za-z0-9_./-]+)`", body)):
        if not (ROOT / ref).exists():
            errors.append(f"SKILL.md references missing path: {ref}")

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"INVALID: {e}")
        return 1
    print(f"OK: skill valid (name={name.group(1) if name else '?'}, "
          f"version={version.group(1) if version else '?'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
