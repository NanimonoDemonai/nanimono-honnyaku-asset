#!/usr/bin/env python3
"""Heuristic glossary extractor from XLIFF.

Extracts candidate EN terms and JA terms, attempts to align simple 1:1 pairs when a
segment contains exactly one EN candidate token and one JA candidate token.

Outputs:
  1) TSV of aligned term pairs (source_term, target_term, count, example_ids)
  2) TSV of unmatched EN terms (en_term, count, example_ids)
  3) TSV of unmatched JA terms (ja_term, count, example_ids)

Heuristics:
  EN candidate token:
    - Matches regex: (SCP|[A-Z][a-z]+|[A-Z]{2,}|[A-Z][a-z]+[A-Z][a-z]+) possibly with hyphen/digits
    - Length >= 2
    - Lowercased stoplist filtered (common function words)
  JA candidate token:
    - Continuous sequence of Kanji (>=1) OR Katakana (>=2) OR mixed Kanji/Katakana
    - Ignore purely hiragana sequences to avoid grammar particles
  Alignment:
    - Per trans-unit: if exactly one EN candidate and one JA candidate => pair count++
    - Otherwise accumulate as unmatched candidates

Usage:
  python script/extract_glossary.py path/to/translation.xml --out-dir build/glossary

Creates directory if missing; writes:
  glossary_pairs.tsv
  glossary_en_unmatched.tsv
  glossary_ja_unmatched.tsv

Limitations:
  This is a lightweight heuristic; for higher accuracy consider statistical alignment
  (e.g. fast_align) or embedding similarity. This script is intentionally dependency-light.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple, Dict, Set

EN_TOKEN_RE = re.compile(r"(SCP|[A-Z][a-z]+(?:-[A-Z][a-z]+)?|[A-Z]{2,}|[A-Z][a-z]+[A-Z][a-z]+|[A-Z][a-z]+\d+)")
# Kanji: \u4E00-\u9FFF, Katakana: \u30A1-\u30FA\u30FC, prolonged sound mark etc.
JA_TOKEN_RE = re.compile(r"([\u30A1-\u30FA\u30FC]{2,}|[\u4E00-\u9FFF]+[\u30A1-\u30FA\u30FC]*|[\u4E00-\u9FFF]{2,})")
HIRAGANA_RE = re.compile(r"^[\u3040-\u309F]+$")

EN_STOP = {
    "The","A","An","And","Or","But","If","Of","For","To","In","On","At","It","You","I","We","He","She","They","Them","Is","Are","Am","Be","Been","Was","Were","This","That","These","Those","My","Your","Our","Their","With","As","Not","Have","Has","Had","Will","Can","Do","Did","So","All","Any"
}

@dataclass
class Pair:
    src: str
    tgt: str
    count: int
    ids: set[str]


def iter_units(xml_path: Path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for tu in root.findall('.//trans-unit'):
        _id = tu.get('id', '')
        src_el = tu.find('source')
        tgt_el = tu.find('target')
        if src_el is None or tgt_el is None:
            continue
        src = ''.join(src_el.itertext())
        tgt = ''.join(tgt_el.itertext())
        yield _id, src, tgt


def extract_en(text: str):
    cands = []
    for m in EN_TOKEN_RE.finditer(text):
        tok = m.group(0).strip('-')
        if len(tok) < 2:
            continue
        if tok in EN_STOP:
            continue
        cands.append(tok)
    return list(dict.fromkeys(cands))  # dedupe preserving order


def extract_ja(text: str):
    cands = []
    for m in JA_TOKEN_RE.finditer(text):
        tok = m.group(0)
        if HIRAGANA_RE.match(tok):
            continue
        if len(tok) < 2:
            continue
        cands.append(tok)
    return list(dict.fromkeys(cands))


def build_glossary(xml_path: Path):
    pair_counts: Dict[Tuple[str, str], Pair] = {}
    en_unmatched: Dict[str, Set[str]] = defaultdict(set)
    ja_unmatched: Dict[str, Set[str]] = defaultdict(set)

    for _id, src, tgt in iter_units(xml_path):
        en_terms: List[str] = extract_en(src)
        ja_terms: List[str] = extract_ja(tgt)
        if len(en_terms) == 1 and len(ja_terms) == 1:
            key: Tuple[str, str] = (en_terms[0], ja_terms[0])
            if key not in pair_counts:
                pair_counts[key] = Pair(src=en_terms[0], tgt=ja_terms[0], count=0, ids=set())
            pair_counts[key].count += 1
            pair_counts[key].ids.add(_id)
        else:
            for t in en_terms:
                en_unmatched[t].add(_id)
            for t in ja_terms:
                ja_unmatched[t].add(_id)

    return pair_counts, en_unmatched, ja_unmatched


def write_pairs(path: Path, pairs: dict[tuple[str, str], Pair]):
    lines = ["source_term\ttarget_term\tcount\texample_ids"]
    for (_, _), p in sorted(pairs.items(), key=lambda x: (-x[1].count, x[0][0])):
        lines.append(f"{p.src}\t{p.tgt}\t{p.count}\t{','.join(sorted(p.ids))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_unmatched(path: Path, data: dict[str, set[str]], header: str):
    lines = [f"{header}\tcount\texample_ids"]
    for term, ids in sorted(data.items(), key=lambda x: (-len(x[1]), x[0])):
        lines.append(f"{term}\t{len(ids)}\t{','.join(sorted(ids))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]):
    ap = argparse.ArgumentParser(description="Extract heuristic glossary pairs from translation.xml")
    ap.add_argument('xml', type=Path, help='Path to translation.xml')
    ap.add_argument('--out-dir', type=Path, default=Path('build/glossary'), help='Output directory (default: build/glossary)')
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    ns.out_dir.mkdir(parents=True, exist_ok=True)
    pairs, en_unmatched, ja_unmatched = build_glossary(ns.xml)
    write_pairs(ns.out_dir / 'glossary_pairs.tsv', pairs)
    write_unmatched(ns.out_dir / 'glossary_en_unmatched.tsv', en_unmatched, 'en_term')
    write_unmatched(ns.out_dir / 'glossary_ja_unmatched.tsv', ja_unmatched, 'ja_term')
    print(f"Wrote: {ns.out_dir / 'glossary_pairs.tsv'}")
    print(f"Wrote: {ns.out_dir / 'glossary_en_unmatched.tsv'}")
    print(f"Wrote: {ns.out_dir / 'glossary_ja_unmatched.tsv'}")
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
