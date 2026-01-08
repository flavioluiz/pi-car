"""
Pi-Car - Servico MPD (Music Player Daemon)

Gerencia conexao e controle do MPD.
"""

from mpd import MPDClient
import config

# Dados globais de musica (atualizados por get_status)
music_data = {
    'state': 'stop',
    'artist': '',
    'title': '',
    'album': '',
    'elapsed': 0,
    'duration': 0,
    'volume': 100,
    'random': False,
    'repeat': False,
    'connected': False
}


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
                music_data['repeat'] = status.get('repeat', '0') == '1'
                music_data['artist'] = song.get('artist', 'Desconhecido')
                music_data['title'] = song.get('title', song.get('file', 'Sem titulo'))
                music_data['album'] = song.get('album', '')

                client.close()
                client.disconnect()
            except Exception as e:
                music_data['connected'] = False
                print(f"MPD update erro: {e}")
        else:
            music_data['connected'] = False

        return music_data

    def control(self, action):
        """Executa acao no player"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            if action == 'play':
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
            return playlist
        except Exception as e:
            return {'error': str(e)}

    def get_library(self):
        """Retorna biblioteca de musicas"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            songs = client.listall()
            client.close()
            client.disconnect()
            return songs
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
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            results = client.search('any', query)
            client.close()
            client.disconnect()
            return results
        except Exception as e:
            return {'error': str(e)}

    def list_artists(self):
        """Retorna lista de artistas"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            result = client.list('artist')
            client.close()
            client.disconnect()

            # Normaliza resultado (pode ser lista de strings ou dicts)
            artists = []
            for item in result:
                if isinstance(item, str):
                    if item:
                        artists.append(item)
                elif isinstance(item, dict):
                    artist = item.get('artist', '')
                    if artist:
                        artists.append(artist)

            return sorted(set(artists))
        except Exception as e:
            return {'error': str(e)}

    def list_by_artist(self, artist):
        """Retorna musicas de um artista"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            songs = client.find('artist', artist)
            client.close()
            client.disconnect()
            return songs
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
        """Alterna modo repeat"""
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            status = client.status()
            current = status.get('repeat', '0') == '1'
            client.repeat(0 if current else 1)
            client.close()
            client.disconnect()
            return {'success': True, 'repeat': not current}
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
        client = self._get_client()
        if not client:
            return {'error': 'MPD nao conectado'}

        try:
            songs = client.listallinfo()
            client.close()
            client.disconnect()
            # Filtra apenas arquivos (ignora diretorios)
            return [s for s in songs if 'file' in s]
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
