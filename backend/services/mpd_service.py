"""
Pi-Car - Servico MPD (Music Player Daemon)

Gerencia conexao e controle do MPD.
"""

from mpd import MPDClient
import config
from backend.services.music_library import MusicLibraryIndex

# Dados globais de musica (atualizados por get_status)
music_data = {
    'state': 'stop',
    'artist': '',
    'artists_all': '',
    'title': '',
    'album': '',
    'elapsed': 0,
    'duration': 0,
    'volume': 100,
    'random': False,
    'repeat': False,
    'connected': False
}

music_library = MusicLibraryIndex()


class MPDService:
    """Servico para interacao com MPD"""

    def __init__(self, host=None, port=None):
        self.host = host or config.MPD_HOST
        self.port = port or config.MPD_PORT

    def _get_client(self):
        """Retorna cliente MPD conectado"""
        try:
            client = MPDClient()
            client.timeout = 10
            client.connect(self.host, self.port)
            return client
        except Exception as e:
            print(f"MPD erro: {e}")
            return None

    def get_status(self):
        """Atualiza e retorna dados do MPD"""
        global music_data
        client = self._get_client()

        if client:
            try:
                status = client.status()
                song = client.currentsong()

                music_data['connected'] = True
                music_data['state'] = status.get('state', 'stop')
                music_data['volume'] = int(status.get('volume', 100))
                music_data['elapsed'] = float(status.get('elapsed', 0))
                music_data['duration'] = float(status.get('duration', 0))
                music_data['random'] = status.get('random', '0') == '1'
                # Repeat ativo = repeat + single (repete musica atual)
                music_data['repeat'] = (status.get('repeat', '0') == '1' and
                                        status.get('single', '0') == '1')
                music_data['artist'] = song.get('artist', 'Desconhecido')
                music_data['title'] = song.get('title', song.get('file', 'Sem titulo'))
                music_data['album'] = song.get('album', '')
                current_file = song.get('file', '')
                track = music_library.get_track_by_file(current_file) if current_file else None
                music_data['artists_all'] = (
                    track.get('artists_all', '') if track else song.get('artists_all', '')
                )

                client.close()
                client.disconnect()
            except Exception as e:
                music_data['connected'] = False
                print(f"MPD update erro: {e}")
        else:
            music_data['connected'] = False

        return music_data

    def _stop_radio(self):
        """Stop radio playback when music starts."""
        try:
            from backend.services.rtlsdr_service import get_rtlsdr_service, radio_data
            if radio_data.get('playing'):
                service = get_rtlsdr_service()
                service.stop_playback()
                print("Radio stopped for music playback")
        except Exception as e:
            print(f"Could not stop radio: {e}")

    def control(self, action):
        """Executa acao no player"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            if action == 'play':
                self._stop_radio()  # Stop radio when music starts
                client.play()
            elif action == 'pause':
                client.pause()
            elif action == 'stop':
                client.stop()
            elif action == 'next':
                client.next()
            elif action == 'prev':
                client.previous()
            elif action == 'volup':
                status = client.status()
                vol = min(100, int(status.get('volume', 0)) + 5)
                client.setvol(vol)
            elif action == 'voldown':
                status = client.status()
                vol = max(0, int(status.get('volume', 0)) - 5)
                client.setvol(vol)

            client.close()
            client.disconnect()
            return {'success': True, 'action': action}
        except Exception as e:
            return {'error': str(e)}

    def get_playlist(self):
        """Retorna playlist atual"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            playlist = client.playlistinfo()
            client.close()
            client.disconnect()
            for song in playlist:
                file_path = song.get('file', '')
                if file_path:
                    track = music_library.get_track_by_file(file_path)
                    if track:
                        song['artists_all'] = track.get('artists_all', '')
            return playlist
        except Exception as e:
            return {'error': str(e)}

    def get_library(self):
        """Retorna biblioteca de musicas"""
        try:
            return music_library.refresh(force=True)
        except Exception as e:
            return {'error': str(e)}

    def add_to_playlist(self, uri):
        """Adiciona musica a playlist"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            if uri:
                client.add(uri)
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def search(self, query):
        """Busca musicas por titulo, artista ou album"""
        try:
            return music_library.search(query)
        except Exception as e:
            return {'error': str(e)}

    def list_artists(self):
        """Retorna lista de artistas"""
        try:
            return music_library.list_artists()
        except Exception as e:
            return {'error': str(e)}

    def play_artist(self, artist):
        """Limpa fila, adiciona todas as musicas do artista e toca"""
        songs = music_library.list_by_artist(artist)
        if not songs:
            return {'error': 'Nenhuma musica encontrada'}

        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.clear()
            for song in songs:
                client.add(song['file'])
            client.play()
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def add_artist_to_queue(self, artist):
        """Adiciona todas as musicas do artista a fila"""
        songs = music_library.list_by_artist(artist)
        if not songs:
            return {'error': 'Nenhuma musica encontrada'}

        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            for song in songs:
                client.add(song['file'])
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def list_by_artist(self, artist):
        """Retorna musicas de um artista"""
        try:
            return music_library.list_by_artist(artist)
        except Exception as e:
            return {'error': str(e)}

    def list_playlists(self):
        """Lista playlists salvas em ~/.mpd/playlists"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            playlists = client.listplaylists()
            client.close()
            client.disconnect()
            return playlists
        except Exception as e:
            return {'error': str(e)}

    def load_playlist(self, name):
        """Carrega playlist salva (substitui fila atual)"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.clear()
            client.load(name)
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def save_playlist(self, name):
        """Salva playlist atual"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            # Remove playlist existente com mesmo nome (se houver)
            try:
                client.rm(name)
            except:
                pass
            client.save(name)
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def toggle_random(self):
        """Alterna modo shuffle"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            status = client.status()
            current = status.get('random', '0') == '1'
            client.random(0 if current else 1)
            client.close()
            client.disconnect()
            return {'success': True, 'random': not current}
        except Exception as e:
            return {'error': str(e)}

    def toggle_repeat(self):
        """Alterna modo repeat (repete musica atual)"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            status = client.status()
            # Para repetir uma musica, precisamos de repeat + single
            current_repeat = status.get('repeat', '0') == '1'
            current_single = status.get('single', '0') == '1'
            # Considera ativo se ambos estao ligados
            is_active = current_repeat and current_single
            new_state = 0 if is_active else 1
            client.repeat(new_state)
            client.single(new_state)
            client.close()
            client.disconnect()
            return {'success': True, 'repeat': not is_active}
        except Exception as e:
            return {'error': str(e)}

    def play_pos(self, pos):
        """Toca musica na posicao especifica da fila"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.play(int(pos))
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def clear_queue(self):
        """Limpa a fila atual"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.clear()
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def remove_from_queue(self, pos):
        """Remove musica da fila pela posicao"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.delete(int(pos))
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def add_playlist_to_queue(self, name):
        """Adiciona playlist a fila atual (sem limpar)"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.load(name)
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def play_uri(self, uri):
        """Limpa fila, adiciona musica e toca"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.clear()
            client.add(uri)
            client.play()
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def play_playlist(self, name):
        """Limpa fila, carrega playlist e toca"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.clear()
            client.load(name)
            client.play()
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def list_all_songs(self):
        """Lista todas as musicas da biblioteca"""
        try:
            return music_library.refresh(force=True)
        except Exception as e:
            return {'error': str(e)}

    def seek(self, position):
        """Vai para posicao especifica da musica (em segundos)"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.seekcur(float(position))
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}

    def restart_song(self):
        """Reinicia a musica atual"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            client.seekcur(0)
            client.close()
            client.disconnect()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}
