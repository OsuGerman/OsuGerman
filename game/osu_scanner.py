"""Scan osu! Songs folder → extract metadata, audio, backgrounds, preview times."""
from __future__ import annotations
import os, re, glob
from dataclasses import dataclass, field


@dataclass
class OsuDifficulty:
    name: str
    filename: str
    creator: str = ''

@dataclass
class OsuSong:
    folder: str
    title: str
    artist: str
    audio_path: str
    preview_time: float = 45000
    bpm: float = 120
    background: str = ''
    difficulties: list[OsuDifficulty] = field(default_factory=list)

    @property
    def id(self) -> str:
        return os.path.basename(self.folder)


def scan_osu_folder(songs_path: str) -> list[OsuSong]:
    """Scan all subfolders in an osu! Songs directory."""
    if not os.path.isdir(songs_path):
        print(f"[OsuScanner] Path not found: {songs_path}")
        return []

    songs = []
    for entry in os.scandir(songs_path):
        if not entry.is_dir():
            continue
        song = _scan_song_folder(entry.path)
        if song:
            songs.append(song)

    songs.sort(key=lambda s: s.title.lower())
    print(f"[OsuScanner] Found {len(songs)} songs in {songs_path}")
    return songs


def _scan_song_folder(folder: str) -> OsuSong | None:
    osu_files = glob.glob(os.path.join(folder, '*.osu'))

    if not osu_files:
        # No .osu files — try to find audio directly
        audio = _find_audio(folder)
        if not audio:
            return None
        name = os.path.basename(folder)
        # Try to parse "12345 Artist - Title" format
        match = re.match(r'^\d+\s+(.+?)\s*-\s*(.+)$', name)
        if match:
            artist, title = match.group(1).strip(), match.group(2).strip()
        else:
            artist, title = '', name
        bg = _find_background(folder)
        return OsuSong(folder=folder, title=title, artist=artist,
                       audio_path=audio, background=bg or '')

    # Parse first .osu file for metadata
    meta = _parse_osu_file(osu_files[0])
    audio_name = meta.get('AudioFilename', '')
    audio_path = os.path.join(folder, audio_name) if audio_name else _find_audio(folder)
    if not audio_path or not os.path.exists(audio_path):
        audio_path = _find_audio(folder)
    if not audio_path:
        return None

    title = meta.get('Title', meta.get('TitleUnicode', os.path.basename(folder)))
    artist = meta.get('Artist', meta.get('ArtistUnicode', ''))
    preview = float(meta.get('PreviewTime', 45000))
    if preview < 0:
        preview = 30000

    bg = meta.get('_background', '') or _find_background(folder)
    bg_path = os.path.join(folder, bg) if bg and not os.path.isabs(bg) else bg

    # Parse BPM from first timing point
    bpm = float(meta.get('_bpm', 120))

    # Collect difficulties
    diffs = []
    for osu_file in osu_files:
        m = _parse_osu_file(osu_file)
        diff_name = m.get('Version', os.path.splitext(os.path.basename(osu_file))[0])
        creator = m.get('Creator', '')
        diffs.append(OsuDifficulty(name=diff_name, filename=osu_file, creator=creator))

    return OsuSong(
        folder=folder, title=title, artist=artist,
        audio_path=audio_path, preview_time=preview,
        bpm=bpm, background=bg_path if bg_path and os.path.exists(bg_path) else '',
        difficulties=diffs
    )


def _parse_osu_file(path: str) -> dict:
    """Parse key metadata from a .osu file."""
    meta = {}
    section = ''
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('['):
                    section = line.strip('[]')
                    continue

                if section == 'General':
                    if ':' in line:
                        k, v = line.split(':', 1)
                        meta[k.strip()] = v.strip()

                elif section == 'Metadata':
                    if ':' in line:
                        k, v = line.split(':', 1)
                        meta[k.strip()] = v.strip()

                elif section == 'Difficulty':
                    if ':' in line:
                        k, v = line.split(':', 1)
                        meta[k.strip()] = v.strip()

                elif section == 'Events':
                    # Background image
                    if line.startswith('0,0,"'):
                        match = re.match(r'0,0,"([^"]+)"', line)
                        if match:
                            meta['_background'] = match.group(1)

                elif section == 'TimingPoints':
                    if ',' in line and '_bpm' not in meta:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            try:
                                beat_len = float(parts[1])
                                if beat_len > 0:
                                    meta['_bpm'] = str(round(60000 / beat_len, 1))
                            except ValueError:
                                pass
    except Exception:
        pass
    return meta


def _find_audio(folder: str) -> str:
    """Find first audio file in folder."""
    for ext in ('*.mp3', '*.ogg', '*.wav'):
        files = glob.glob(os.path.join(folder, ext))
        if files:
            return files[0]
    return ''


def _find_background(folder: str) -> str:
    """Find first image file in folder."""
    for ext in ('*.jpg', '*.jpeg', '*.png'):
        files = glob.glob(os.path.join(folder, ext))
        if files:
            return files[0]
    return ''
