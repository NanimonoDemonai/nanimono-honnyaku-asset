#!/usr/bin/env python3
"""
Sentence exporter (XLIFF)

Usage:
  python script/export.py INPUT_FILE [--lang xx] [--model MODEL]

- INPUT_FILE: Path to a UTF-8 text file to split into sentences.
- --lang: spaCy language code for a blank pipeline (default: "xx" for multilingual).
- --model: Optional installed spaCy model name to use (e.g., "en_core_web_sm").

Output:
  Writes an XLIFF 1.2 document to a file named 'translation.xml' in the same directory as the input file, with each sentence as a <trans-unit><source>.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import spacy


def build_nlp(lang: str = "xx", model: str | None = None):
    """Build a spaCy pipeline with sentence segmentation.

    Prefers the provided installed model; otherwise uses a blank pipeline for the language code.
    Ensures sentence boundaries exist by adding a sentencizer if needed.
    """
    nlp = spacy.load(model) if model else spacy.blank(lang)
    if "senter" not in nlp.pipe_names and "parser" not in nlp.pipe_names and "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def read_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def export_sentences(input_file: Path, lang: str = "xx", model: str | None = None) -> int:
    text = read_text(input_file)
    if not text.strip():
        return 0

    nlp = build_nlp(lang=lang, model=model)
    doc = nlp(text)

    # Collect sentences (fallback to whole text if none)
    sentences: list[str] = []
    for sent in doc.sents:
        line = sent.text.strip()
        if line:
            sentences.append(line)
    if not sentences:
        fallback = text.strip()
        if fallback:
            sentences.append(fallback)

    # Produce XLIFF 1.2 and write to translation.xml next to the input file
    from xml.sax.saxutils import escape

    source_lang = "en-US"
    target_lang = "ja"
    original = input_file.name

    lines: list[str] = []
    lines.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    lines.append("<xliff version=\"1.2\">")
    lines.append(f"  <file source-language=\"{escape(source_lang)}\" target-language=\"{escape(target_lang)}\" datatype=\"plaintext\" original=\"{escape(original)}\">")
    lines.append("    <body>")

    for i, s in enumerate(sentences, start=1):
        lines.append(f"      <trans-unit id=\"{i}\">")
        lines.append(f"        <source>{escape(s)}</source>")
        lines.append(f"        <target>{escape(s)}</target>")
        lines.append("      </trans-unit>")

    lines.append("    </body>")
    lines.append("  </file>")
    lines.append("</xliff>")

    output_path = input_file.parent / "translation.xml"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split a text file into sentences using spaCy and write XLIFF 1.2 to 'translation.xml' next to the input file")
    p.add_argument("input_file", type=Path, help="Path to input text file (UTF-8 recommended)")
    p.add_argument("--lang", default="xx", help="spaCy language code for blank pipeline (default: xx)")
    p.add_argument(
        "--model",
        default=None,
        help="Installed spaCy model name (e.g., en_core_web_sm).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    return export_sentences(ns.input_file, lang=ns.lang, model=ns.model)


if __name__ == "__main__":
    raise SystemExit(main())
