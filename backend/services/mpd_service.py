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
