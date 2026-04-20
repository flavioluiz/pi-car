"""
Pi-Car - Index de biblioteca local de musicas.

Lê os arquivos da pasta `~/Music` diretamente para acessar tags
customizadas como `artists_all`, que o MPD não expõe.
"""

from __future__ import annotations

import time
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError

import config


AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".wma", ".webm"}
ARTISTS_ALL_DESC = "artists_all"


def _first(value) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    if value is None:
        return ""
    return str(value)


class MusicLibraryIndex:
    """Indexador simples da biblioteca local."""

    def __init__(self, library_dir: str | Path | None = None):
        self.library_dir = Path(library_dir or config.MUSIC_DIRECTORY).expanduser()
        self._cache: list[dict] = []
        self._file_index: dict[str, dict] = {}
        self._cache_timestamp = 0.0
        self.cache_ttl_seconds = 10

    def _iter_audio_files(self):
        if not self.library_dir.exists():
            return []
        return sorted(
            path
            for path in self.library_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        )

    def _read_artists_all_generic(self, file_path: Path) -> str:
        """Lê artists_all de qualquer formato suportado pelo mutagen."""
        try:
            audio = MutagenFile(str(file_path))
            if audio is None or audio.tags is None:
                return ""

            # FLAC / OGG (VorbisComment)
            if hasattr(audio.tags, 'get'):
                val = audio.tags.get(ARTISTS_ALL_DESC) or audio.tags.get(ARTISTS_ALL_DESC.upper())
                if val:
                    return _first(val)

            # M4A / MP4
            if hasattr(audio.tags, 'items'):
                for key, val in audio.tags.items():
                    if ARTISTS_ALL_DESC in str(key).lower():
                        return _first(val)
        except Exception:
            pass
        return ""

    def _read_track(self, file_path: Path) -> dict:
        metadata = {
            "file": str(file_path.relative_to(self.library_dir)),
            "title": file_path.stem,
            "artist": "",
            "album": "",
            "artists_all": "",
        }

        try:
            easy = EasyID3(str(file_path))
            metadata["title"] = _first(easy.get("title")) or metadata["title"]
            metadata["artist"] = _first(easy.get("artist"))
            metadata["album"] = _first(easy.get("album"))
        except Exception:
            pass

        # Tenta ler artists_all via ID3 (MP3)
        try:
            tags = ID3(str(file_path))
            custom_tags = tags.getall(f"TXXX:{ARTISTS_ALL_DESC}")
            if custom_tags:
                metadata["artists_all"] = _first(custom_tags[0].text)
        except ID3NoHeaderError:
            pass
        except Exception:
            pass

        # Para formatos não-ID3 (FLAC, OGG, M4A), tenta leitura genérica
        if not metadata["artists_all"] and file_path.suffix.lower() != ".mp3":
            metadata["artists_all"] = self._read_artists_all_generic(file_path)

        if not metadata["artists_all"]:
            metadata["artists_all"] = metadata["artist"]

        return metadata

    def _scan_library(self) -> list[dict]:
        return [self._read_track(path) for path in self._iter_audio_files()]

    def refresh(self, force: bool = False) -> list[dict]:
        now = time.monotonic()
        if not force and self._cache and (now - self._cache_timestamp) < self.cache_ttl_seconds:
            return self._cache

        self._cache = self._scan_library()
        self._file_index = {}
        for track in self._cache:
            self._file_index[track["file"]] = track
            self._file_index[Path(track["file"]).name] = track
        self._cache_timestamp = now
        return self._cache

    def get_track_by_file(self, file_name: str) -> dict | None:
        if not file_name:
            return None

        self.refresh()
        target = file_name.strip()
        return self._file_index.get(target)

    def search(self, query: str) -> list[dict]:
        query = (query or "").strip().casefold()
        if not query:
            return self.refresh(force=True)

        results = []
        for track in self.refresh(force=True):
            haystacks = (
                track.get("title", ""),
                track.get("artist", ""),
                track.get("album", ""),
                track.get("artists_all", ""),
                track.get("file", ""),
            )
            if any(query in value.casefold() for value in haystacks if value):
                results.append(track)
        return results

    def list_artists(self) -> list[str]:
        artists = set()
        for track in self.refresh(force=True):
            artist = (track.get("artist") or "").strip()
            if artist:
                artists.add(artist)
            for part in (track.get("artists_all") or "").split(","):
                part = part.strip()
                if part:
                    artists.add(part)

        return sorted(artists, key=str.casefold)

    def list_by_artist(self, artist: str) -> list[dict]:
        needle = (artist or "").strip().casefold()
        if not needle:
            return []

        results = []
        for track in self.refresh(force=True):
            canonical = (track.get("artist") or "").strip().casefold()
            if canonical == needle:
                results.append(track)
                continue

            credits = [part.strip().casefold() for part in (track.get("artists_all") or "").split(",")]
            if needle in [part for part in credits if part]:
                results.append(track)

        return results
