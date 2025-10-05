#!/usr/bin/env python3
"""
Extract target strings from an XLIFF file and print them.

Usage:
  python script/extract.py INPUT_XLIFF [--sep SEP] [--no-empty]

- INPUT_XLIFF: Path to an XLIFF 1.x/2.x file (UTF-8 recommended).
- --sep: Separator between targets in output (default: newline). Use "\0" for NUL.
- --no-empty: Skip empty targets.

The script prints only the <target> contents in document order to stdout.
It is namespace-agnostic and will pick up <target> elements regardless of XLIFF version.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


def find_targets(root: ET.Element) -> list[str]:
    """Return the text content of all <target> elements in document order.

    This function is namespace-agnostic and concatenates all text fragments
    within each <target> (including nested inline tags) via itertext().
    Leading/trailing whitespace is stripped, and internal newlines are preserved.
    """
    targets: list[str] = []
    # .//{*}target will match any namespace
    for el in root.findall('.//{*}target'):
        text = ''.join(el.itertext())
        targets.append(text.strip())
    return targets


essential_stdin_encoding_fixed = False


def ensure_stdout_utf8() -> None:
    # Ensure we can print UTF-8 even if the environment encoding is limited.
    global essential_stdin_encoding_fixed
    if essential_stdin_encoding_fixed:
        return
    try:
        if sys.stdout.encoding is None or sys.stdout.encoding.lower().replace('-', '') != 'utf8':
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        # Best effort; if reconfigure is not available, continue.
        pass
    essential_stdin_encoding_fixed = True



def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract <target> texts from an XLIFF file and print them.")
    p.add_argument('input_file', type=Path, help='Path to XLIFF file (e.g., translation.xml)')
    p.add_argument('--sep', default='\n', help='Separator between targets (default: newline). Use \\0 for NUL.')
    p.add_argument('--no-empty', action='store_true', help='Skip empty targets')
    return p.parse_args(argv)



def main(argv: list[str] | None = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)

    input_path: Path = ns.input_file
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 2

    try:
        tree = ET.parse(input_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML: {e}", file=sys.stderr)
        return 2

    targets = find_targets(root)

    if ns.no_empty:
        targets = [t for t in targets if t.strip()]

    sep = ns.sep
    if sep == "\\0":
        sep = "\0"
    elif sep == "\\n":
        sep = "\n"
    elif sep == "\\t":
        sep = "\t"

    # Write output to tgt.txt next to the input file
    output_path = input_path.parent / 'tgt.txt'
    try:
        with output_path.open('w', encoding='utf-8', newline='') as f:
            f.write(sep.join(targets))
            # Always end with a newline for terminal friendliness when sep isn't newline
            if not sep.endswith('\n'):
                f.write('\n')
    except Exception as e:
        print(f"Error: Failed to write to {output_path}: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
