#!/usr/bin/env python3
"""Translation consistency & length difference checker.

Features:
  * Parse an XLIFF 1.2 or 2.1 file (translation.xml)
  * For each unit (trans-unit in 1.2 / unit>segment in 2.1): collect source / target text
  * Detect likely untranslated targets (exact match or high ASCII ratio)
  * Compute length stats (char counts, ratio target/source)
  * Optional thresholds for flagging too-short / too-long translations
  * Outputs a TSV table to stdout and a JSON summary (optional)

Usage:
  python script/check_translation.py path/to/translation.xml \
      [--min-ratio 0.3] [--max-ratio 2.5] [--ascii-ratio 0.7] [--json report.json]

Heuristics:
  * Untranslated if stripped target == stripped source
  * Or if target has ASCII proportion >= ascii-ratio AND contains at least one letter
  * Mark ratio issues if len(target)/len(source) outside [min_ratio, max_ratio]

Exit code:
  0 always (does not fail build) — can be adjusted if desired.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional

ASCII_LETTER_RE = re.compile(r"[A-Za-z]")


def normalize_text(s: str) -> str:
    # Remove surrounding whitespace and collapse internal line endings for comparison
    return "".join(s.split()).lower()


def ascii_ratio(s: str) -> float:
    if not s:
        return 0.0
    ascii_chars = sum(1 for ch in s if ord(ch) < 128 and not ch.isspace())
    total = sum(1 for ch in s if not ch.isspace())
    return ascii_chars / total if total else 0.0


def strip_markup(s: str) -> str:
    # Remove simple emphases like //...// and **...** but leave contents
    s = s.replace("**", "")
    # Keep slashes but this is fine; we can remove paired // markers
    return s.replace("//", "")


def char_len(s: str) -> int:
    # Count visible characters excluding most whitespace newlines
    return sum(1 for ch in s if not ch.isspace())


@dataclass
class UnitReport:
    id: str
    source_chars: int
    target_chars: int
    ratio: float
    untranslated: bool
    ascii_heavy: bool
    ratio_flag: bool
    source_preview: str
    target_preview: str


@dataclass
class Summary:
    units: int
    untranslated: int
    ascii_heavy: int
    ratio_flags: int
    avg_ratio: float
    min_ratio: float
    max_ratio: float


def _local(tag: str) -> str:
    return tag.split('}', 1)[1] if '}' in tag else tag


def iter_units(xml_path: Path) -> Iterable[tuple[str, str, str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Prefer XLIFF 1.2 trans-unit elements if present
    trans_units = list(root.findall('.//trans-unit'))
    if trans_units:
        for tu in trans_units:
            _id = tu.get('id', '')
            src_el = tu.find('source')
            tgt_el = tu.find('target')
            if src_el is None or tgt_el is None:
                continue
            src = ''.join(src_el.itertext())
            tgt = ''.join(tgt_el.itertext())
            yield _id, src, tgt
        return

    # Fallback: XLIFF 2.1 <unit><segment><source/target>
    # Need to traverse with namespace-agnostic handling
    for el in root.iter():
        if _local(el.tag) == 'unit':
            unit_id = el.get('id', '')
            segments = [c for c in el if _local(c.tag) == 'segment']
            if not segments:
                # Some tools may nest segment deeper; search descendants
                segments = [c for c in el.iter() if _local(c.tag) == 'segment']
            for idx, seg in enumerate(segments, start=1):
                src_el = None
                tgt_el = None
                for child in seg:
                    lname = _local(child.tag)
                    if lname == 'source':
                        src_el = child
                    elif lname == 'target':
                        tgt_el = child
                if src_el is None or tgt_el is None:
                    continue
                src = ''.join(src_el.itertext())
                tgt = ''.join(tgt_el.itertext())
                seg_id = unit_id if len(segments) == 1 else f"{unit_id}:{idx}"
                yield seg_id, src, tgt


def analyze(xml_path: Path, min_ratio: float, max_ratio: float, ascii_threshold: float) -> tuple[List[UnitReport], Summary]:
    reports: List[UnitReport] = []
    ratios: List[float] = []
    untranslated_count = 0
    ascii_heavy_count = 0
    ratio_flag_count = 0

    for _id, src_raw, tgt_raw in iter_units(xml_path):
        src_clean = strip_markup(src_raw)
        tgt_clean = strip_markup(tgt_raw)
        src_norm = normalize_text(src_clean)
        tgt_norm = normalize_text(tgt_clean)
        untranslated = (src_norm == tgt_norm and src_norm != '')
        ascii_r = ascii_ratio(tgt_clean)
        ascii_heavy = ascii_r >= ascii_threshold and ASCII_LETTER_RE.search(tgt_clean) is not None
        s_len = max(char_len(src_clean), 1)  # avoid div by zero
        t_len = char_len(tgt_clean)
        ratio = t_len / s_len if s_len else 0.0
        ratio_flag = ratio < min_ratio or ratio > max_ratio

        if untranslated:
            untranslated_count += 1
        if ascii_heavy:
            ascii_heavy_count += 1
        if ratio_flag:
            ratio_flag_count += 1
        ratios.append(ratio)

        reports.append(
            UnitReport(
                id=_id,
                source_chars=s_len,
                target_chars=t_len,
                ratio=round(ratio, 3),
                untranslated=untranslated,
                ascii_heavy=ascii_heavy,
                ratio_flag=ratio_flag,
                source_preview=src_clean.strip().replace('\n', ' ')[:60],
                target_preview=tgt_clean.strip().replace('\n', ' ')[:60],
            )
        )

    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    summary = Summary(
        units=len(reports),
        untranslated=untranslated_count,
        ascii_heavy=ascii_heavy_count,
        ratio_flags=ratio_flag_count,
        avg_ratio=round(avg_ratio, 3),
        min_ratio=round(min(ratios), 3) if ratios else 0.0,
        max_ratio=round(max(ratios), 3) if ratios else 0.0,
    )
    return reports, summary


def write_tsv(reports: List[UnitReport]):
    header = [
        "id",
        "src_chars",
        "tgt_chars",
        "ratio",
        "untranslated",
        "ascii_heavy",
        "ratio_flag",
        "source_preview",
        "target_preview",
    ]
    print("\t".join(header))
    for r in reports:
        print(
            "\t".join(
                [
                    r.id,
                    str(r.source_chars),
                    str(r.target_chars),
                    f"{r.ratio:.3f}",
                    "1" if r.untranslated else "0",
                    "1" if r.ascii_heavy else "0",
                    "1" if r.ratio_flag else "0",
                    r.source_preview,
                    r.target_preview,
                ]
            )
        )


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check translation consistency and length differences in an XLIFF file")
    p.add_argument("xml", type=Path, help="Path to translation.xml")
    p.add_argument("--min-ratio", type=float, default=0.3, help="Minimum acceptable target/source char ratio")
    p.add_argument("--max-ratio", type=float, default=2.5, help="Maximum acceptable target/source char ratio")
    p.add_argument("--ascii-ratio", type=float, default=0.7, help="ASCII char proportion threshold to mark ascii_heavy")
    p.add_argument("--json", type=Path, help="Optional path to write JSON summary + per-unit details")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ns = parse_args(sys.argv[1:] if argv is None else argv)
    reports, summary = analyze(ns.xml, ns.min_ratio, ns.max_ratio, ns.ascii_ratio)
    write_tsv(reports)
    if ns.json:
        payload = {
            "summary": asdict(summary),
            "units": [asdict(r) for r in reports],
        }
        ns.json.parent.mkdir(parents=True, exist_ok=True)
        ns.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Print summary to stderr
    print("\n# Summary", file=sys.stderr)
    for k, v in asdict(summary).items():
        print(f"{k}: {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
