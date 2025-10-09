#!/usr/bin/env python3
"""
Sentence exporter (XLIFF)

Usage:
  python script/export.py INPUT_FILE [--lang en] [--model MODEL]

- INPUT_FILE: Path to a UTF-8 text file to split into sentences.
- --lang: spaCy language code for a blank pipeline (default: "en").
- --model: Installed spaCy model name to use (default: "en_core_web_sm").

Output:
  Writes an XLIFF 2.1 document to a file named 'translation.xml' in the same directory as the input file, with each sentence as a <unit><segment><source>.
  (Previously XLIFF 1.2 <trans-unit> was used.)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import spacy


def build_nlp(lang: str = "en", model: str | None = "en_core_web_sm"):
    """Build a spaCy pipeline with sentence segmentation.

    Prefers the provided installed model; otherwise uses a blank pipeline for the language code.
    Ensures sentence boundaries exist by adding a sentencizer if needed.
    """
    nlp = None
    if model:
        try:
            nlp = spacy.load(model)
        except Exception:
            nlp = None
    if nlp is None:
        # Fall back to a blank pipeline for the provided language (default: English)
        nlp = spacy.blank(lang or "en")
    if "senter" not in nlp.pipe_names and "parser" not in nlp.pipe_names and "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def read_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def export_sentences(input_file: Path, lang: str = "en", model: str | None = "en_core_web_sm") -> int:
    text = read_text(input_file)
    if not text.strip():
        return 0

    nlp = build_nlp(lang=lang, model=model)
    doc = nlp(text)

    # Collect sentences (fallback to whole text if none)
    sentences: list[str] = []
    for sent in doc.sents:
        line = sent.text  # Preserve original whitespace and newlines
        if line != "":
            sentences.append(line)
    if not sentences:
        fallback = text  # Preserve original whitespace and newlines
        if fallback != "":
            sentences.append(fallback)

    # Produce XLIFF 2.1 and write to translation.xml next to the input file
    from xml.sax.saxutils import escape

    source_lang = "en-US"
    target_lang = "ja"
    original = input_file.name

    # XLIFF 2.1 structure:
    # <xliff version="2.1" srcLang="..." trgLang="..." xmlns="urn:oasis:names:tc:xliff:document:2.1">
    #   <file id="f1" original="...">
    #     <unit id="1">
    #       <segment>
    #         <source xml:space="preserve">...</source>
    #         <target xml:space="preserve" state="initial">...</target>
    #       </segment>
    #     </unit>
    #   ...
    # </xliff>

    lines: list[str] = []
    lines.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    lines.append("<xliff version=\"2.1\" srcLang=\"%s\" trgLang=\"%s\">" % (escape(source_lang), escape(target_lang)))
    # Use a deterministic file id based on original name
    file_id = escape(Path(original).stem or "file1")
    lines.append(f"  <file id=\"{file_id}\" original=\"{escape(original)}\" datatype=\"plaintext\">")

    for i, s in enumerate(sentences, start=1):
        sid = escape(str(i))
        seg_text = escape(s)
        lines.append(f"    <unit id=\"{sid}\">")
        lines.append("      <segment>")
        lines.append(f"        <source>{seg_text}</source>")
        # Target is a copy of source initially; mark state initial
        lines.append(f"        <target state=\"initial\">{seg_text}</target>")
        lines.append("      </segment>")
        lines.append("    </unit>")

    lines.append("  </file>")
    lines.append("</xliff>")

    output_path = input_file.parent / "translation.xml"
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split a text file into sentences using spaCy and write XLIFF 2.1 to 'translation.xml' next to the input file")
    p.add_argument("input_file", type=Path, help="Path to input text file (UTF-8 recommended)")
    p.add_argument("--lang", default="en", help="spaCy language code for blank pipeline (default: en)")
    p.add_argument(
        "--model",
        default="en_core_web_sm",
        help="Installed spaCy model name (default: en_core_web_sm).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    return export_sentences(ns.input_file, lang=ns.lang, model=ns.model)


if __name__ == "__main__":
    raise SystemExit(main())
