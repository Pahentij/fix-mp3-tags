# fix-mp3-tags

Python utility for repairing corrupted Cyrillic ID3 text tags in MP3 files when Windows-1251 text was incorrectly interpreted as Latin-1.

The script scans a directory recursively, reports proposed changes by default, and can create backups before saving corrected ID3 tags. It does not re-encode or modify the MP3 audio stream.

## What it fixes

This utility targets one specific encoding problem:

1. Text originally encoded using Windows-1251 (CP1251) was decoded as Latin-1.
2. The resulting mojibake was stored in MP3 ID3 text frames.
3. The script attempts to reverse that transformation by encoding the displayed text as Latin-1 and decoding those bytes as Windows-1251.

It is not a universal ID3 repair tool. Use it only when the tags match this corruption pattern.

## Features

- Recursively scans the selected directory and its subdirectories.
- Processes `.mp3` files, case-insensitively.
- Inspects ID3 text frames and attempts the CP1251/Latin-1 reversal.
- Uses dry-run mode by default; no changes are written unless `--apply` is specified.
- Creates a backup before changing a file.
- Preserves the directory structure under `_mp3_tag_backup`.
- Excludes macOS AppleDouble files whose names begin with `._`.
- Excludes `_mp3_tag_backup` from scanning.
- Reports changed, unchanged, skipped, and failed files.

## Requirements

- Python 3.10 or newer
- `mutagen`

Install with pip:

```bash
python3 -m pip install mutagen
```

On Debian or OpenMediaVault, you can instead install the distribution package:

```bash
sudo apt update
sudo apt install python3-mutagen
```

## Installation

Download `fix_mp3_tags.py` from this repository, or clone it:

```bash
git clone https://github.com/USERNAME/fix-mp3-tags.git
cd fix-mp3-tags
```

Replace `USERNAME` with the GitHub account or organization that owns the repository.

## Usage

### 1. Preview changes

Dry-run is the default. It reports proposed corrections without saving changes:

```bash
python3 fix_mp3_tags.py "/path/to/audiobooks"
```

Or explicitly request dry-run mode:

```bash
python3 fix_mp3_tags.py "/path/to/audiobooks" --dry-run
```

Review the proposed old and new text before applying changes.

### 2. Apply corrections

After confirming the proposed conversions are correct:

```bash
python3 fix_mp3_tags.py "/path/to/audiobooks" --apply
```

For each file that needs correction, the script creates a backup before saving updated tags.

### Example for Linux

Replace the placeholders with the actual paths on your system:

```bash
python3 /path/to/fix_mp3_tags.py "/path/to/audiobooks" --dry-run
python3 /path/to/fix_mp3_tags.py "/path/to/audiobooks" --apply
```

The script does not depend on a particular directory layout or media-server application.

## Backup behavior

Backups are stored in `_mp3_tag_backup` inside the selected root directory. The relative directory structure is preserved.

Example source layout:

```text
audiobooks/
├── Author/
│   └── Book/
│       └── chapter.mp3
└── another-book.mp3
```

Corresponding backup layout:

```text
audiobooks/
└── _mp3_tag_backup/
    ├── Author/
    │   └── Book/
    │       └── chapter.mp3
    └── another-book.mp3
```

A backup is created only when a file has text changes to apply. The script copies the backup to a temporary file and renames it into place after the copy completes, reducing the chance that an interrupted copy is mistaken for a complete backup.

Do not delete backups until you have verified the corrected tags in your media player or library application.

## Excluded files

The scanner skips:

- Files whose names start with `._` (macOS AppleDouble sidecar files).
- Files located inside any directory named `_mp3_tag_backup`.
- Files that do not have an `.mp3` extension.

Files without a readable ID3v2 tag are skipped or reported as errors, depending on the file and the error raised by Mutagen. This script focuses on ID3v2 text frames.

## Safety notes

- Run the script without `--apply` first.
- Check the proposed conversions before writing tags.
- Keep backups until you have verified the results.
- Investigate reported errors before rerunning with `--apply`.
- The script writes ID3v2.4 tags when saving.
- The audio stream is not re-encoded, but metadata is modified when `--apply` is used.

## Limitations

- Only the specific Latin-1/Windows-1251 mojibake pattern described above is targeted.
- The script edits ID3 text frames. It does not repair filenames, embedded artwork, audio data, or unrelated metadata formats.
- Files with ID3v1 tags but no ID3v2 tag are not repaired.
- The conversion heuristic requires the candidate result to contain Cyrillic and the original string to contain no Cyrillic. Review dry-run output carefully, especially for mixed-language metadata.

## License

This project is intended to use the MIT License. Add the standard MIT license text in `LICENSE` and replace the copyright holder placeholder with your preferred name or pseudonym.
