from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chord_sections.analysis import analyze_file
from chord_sections.report import render_csv, render_json, render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chord-sections",
        description="Estimate chords and group harmonically similar sections in a local audio file.",
    )
    parser.add_argument("audio", type=Path, help="Local MP3, WAV, or another librosa-supported audio file")
    parser.add_argument("-o", "--output", type=Path, help="Write the report to this path instead of stdout")
    parser.add_argument("--format", choices=("markdown", "csv", "json"), default="markdown")
    parser.add_argument("--window-seconds", type=float, default=1.0, help="Chord analysis window (default: 1.0)")
    parser.add_argument("--section-seconds", type=float, default=8.0, help="Section comparison window (default: 8.0)")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.88,
        help="Cosine similarity required to reuse a section label (default: 0.88)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = analyze_file(
            args.audio,
            window_seconds=args.window_seconds,
            section_seconds=args.section_seconds,
            similarity_threshold=args.similarity_threshold,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    renderers = {
        "markdown": render_markdown,
        "csv": render_csv,
        "json": render_json,
    }
    report = renderers[args.format](result)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
