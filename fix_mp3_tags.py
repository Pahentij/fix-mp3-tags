#!/usr/bin/env python3
"""Repair Cyrillic ID3 text tags misdecoded as Latin-1.

Dry-run is the default. Use --apply to save repaired tags and create backups.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from mutagen.id3 import ID3, ID3NoHeaderError
except ImportError:
    print(
        "ERROR: Missing dependency 'mutagen'. Install with: "
        "python3 -m pip install mutagen",
        file=sys.stderr,
    )
    raise SystemExit(2)

BACKUP_DIR_NAME = "_mp3_tag_backup"


def contains_cyrillic(text: str) -> bool:
    return any("\u0400" <= char <= "\u04FF" for char in text)


def repair_text(text: str) -> str:
    """Reverse Latin-1 misdecoding of Windows-1251 text where recognizable."""
    if not text or contains_cyrillic(text):
        return text
    try:
        candidate = text.encode("latin-1").decode("cp1251")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if candidate != text and contains_cyrillic(candidate):
        return candidate
    return text


def find_mp3_files(root: Path) -> list[Path]:
    """Find MP3 files recursively, excluding macOS sidecars and backups."""
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".mp3"
        and not path.name.startswith("._")
        and BACKUP_DIR_NAME not in path.parts
    )


def backup_file(source: Path, root: Path, backup_root: Path) -> Path:
    """Create a mirrored backup; publish it only after the copy completes."""
    destination = backup_root / source.relative_to(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        shutil.copy2(source, temporary_path)
        temporary_path.replace(destination)
    except BaseException:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return destination


def process_file(
    path: Path, root: Path, backup_root: Path, apply: bool
) -> tuple[str, str]:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        return "SKIP", "No ID3v2 tag found"
    except Exception as exc:
        return "ERROR", f"Could not read ID3 tags: {type(exc).__name__}: {exc}"

    changes = []
    for frame in tags.values():
        frame_text = getattr(frame, "text", None)
        if not isinstance(frame_text, list):
            continue
        for index, original in enumerate(frame_text):
            if not isinstance(original, str):
                continue
            repaired = repair_text(original)
            if repaired != original:
                changes.append((frame, index, original, repaired))

    if not changes:
        return "OK", "No changes needed"

    description = "; ".join(
        f"{frame.FrameID}[{index}]: {original!r} -> {repaired!r}"
        for frame, index, original, repaired in changes
    )
    if not apply:
        return "DRY-RUN", description

    try:
        backup_path = backup_file(path, root, backup_root)

        # Apply the text repairs.
        for frame, index, _original, repaired in changes:
            frame.text[index] = repaired

        # Some existing ID3 text frames are marked as Latin-1 (encoding=0).
        # If their text contains characters outside Latin-1, saving can fail.
        # Use UTF-8 encoding for text frames that cannot be represented in Latin-1.
        for frame in tags.values():
            frame_text = getattr(frame, "text", None)
            if not isinstance(frame_text, list):
                continue
            needs_unicode = any(
                isinstance(value, str)
                and _not_latin1_encodable(value)
                for value in frame_text
            )
            if needs_unicode and hasattr(frame, "encoding"):
                frame.encoding = 3  # UTF-8, supported by ID3v2.4

        tags.save(path, v2_version=4)
    except Exception as exc:
        diagnostic = [f"{type(exc).__name__}: {exc}"]
        try:
            for frame in tags.values():
                frame_text = getattr(frame, "text", None)
                if isinstance(frame_text, list) and frame_text:
                    diagnostic.append(f"{frame.FrameID}: {frame_text!r}")
        except Exception as frame_exc:
            diagnostic.append(
                f"Could not inspect frames: {type(frame_exc).__name__}: {frame_exc}"
            )
        return "ERROR", "Save failed: " + " | ".join(diagnostic)

    return "FIXED", f"Backup: {backup_path}; {description}"


def _not_latin1_encodable(text: str) -> bool:
    try:
        text.encode("latin-1")
        return False
    except UnicodeEncodeError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Repair MP3 ID3 text tags where Windows-1251 Cyrillic was "
            "misinterpreted as Latin-1. Dry-run is the default."
        )
    )
    parser.add_argument(
        "directory", type=Path, help="Root directory to scan recursively"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply", action="store_true",
        help="Save repaired tags and create backups"
    )
    mode.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes only (default)"
    )
    args = parser.parse_args()

    root = args.directory.expanduser().resolve()
    if not root.exists():
        print(f"ERROR: Directory does not exist: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: Not a directory: {root}", file=sys.stderr)
        return 2

    apply = args.apply
    backup_root = root / BACKUP_DIR_NAME
    files = find_mp3_files(root)

    print(f"Root: {root}")
    print(f"MP3 files found: {len(files)}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    if apply:
        print(f"Backup directory: {backup_root}")
    print("-" * 72)

    counts = {"FIXED": 0, "DRY-RUN": 0, "OK": 0, "SKIP": 0, "ERROR": 0}
    for path in files:
        status, details = process_file(path, root, backup_root, apply)
        counts[status] = counts.get(status, 0) + 1
        print(f"[{status}] {path.relative_to(root)}")
        if details:
            print(f"  {details}")

    print("-" * 72)
    print("Summary:")
    for status in ("FIXED", "DRY-RUN", "OK", "SKIP", "ERROR"):
        print(f"  {status}: {counts.get(status, 0)}")
    if not apply:
        print("Dry-run only: no tags were changed. Use --apply to save changes.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
