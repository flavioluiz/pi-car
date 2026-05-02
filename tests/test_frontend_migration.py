import importlib
import sys
import types
import unittest
import warnings


def install_dependency_stubs():
    mpd_module = types.ModuleType("mpd")

    class MPDClient:
        timeout = 10

        def connect(self, *args, **kwargs):
            return None

        def status(self):
            return {
                "state": "stop",
                "volume": "72",
                "elapsed": "0",
                "duration": "0",
                "random": "0",
                "repeat": "0",
                "single": "0",
            }

        def currentsong(self):
            return {}

        def playlistinfo(self):
            return []

        def close(self):
            return None

        def disconnect(self):
            return None

    mpd_module.MPDClient = MPDClient
    sys.modules["mpd"] = mpd_module

    mutagen_module = types.ModuleType("mutagen")
    mutagen_module.File = lambda *args, **kwargs: None
    sys.modules["mutagen"] = mutagen_module

    mutagen_easyid3 = types.ModuleType("mutagen.easyid3")

    class EasyID3(dict):
        def __init__(self, *args, **kwargs):
            super().__init__()

    mutagen_easyid3.EasyID3 = EasyID3
    sys.modules["mutagen.easyid3"] = mutagen_easyid3

    mutagen_id3 = types.ModuleType("mutagen.id3")

    class ID3:
        def __init__(self, *args, **kwargs):
            return None

        def getall(self, *args, **kwargs):
            return []

    class ID3NoHeaderError(Exception):
        pass

    mutagen_id3.ID3 = ID3
    mutagen_id3.ID3NoHeaderError = ID3NoHeaderError
    sys.modules["mutagen.id3"] = mutagen_id3


class FrontendMigrationSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore", ResourceWarning)
        install_dependency_stubs()
        for module_name in [
            "backend.routes",
            "backend.routes.music",
            "backend.routes.gps",
            "backend.routes.vehicle",
            "backend.routes.system",
            "backend.routes.radio",
            "backend.services",
            "backend.services.mpd_service",
            "backend.services.music_library",
            "backend.services.gps_service",
            "backend.services.obd_service",
            "backend.services.rtlsdr_service",
            "app",
        ]:
            sys.modules.pop(module_name, None)
        cls.app_module = importlib.import_module("app")
        cls.client = cls.app_module.app.test_client()

    def test_index_renders_picasso_shell(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        critical_hooks = [
            'id="panel-home"',
            'id="panel-music"',
            'id="panel-gps"',
            'id="panel-vehicle"',
            'id="panel-radio"',
            'id="panel-settings"',
            'id="music-title"',
            'id="music-artist"',
            'id="btn-play"',
            'id="btn-shuffle"',
            'id="btn-repeat"',
            'id="queue-list"',
            'id="artists-list"',
            'id="playlists-list"',
            'id="search-results"',
            'id="obd-speed"',
            'id="obd-rpm"',
            'id="gps-speed"',
            'id="radio-freq"',
            'id="favorites-list"',
            'id="spectrogram"',
        ]
        for hook in critical_hooks:
            self.assertIn(hook, html)

        self.assertIn('/static/logos/picasso_logo.png', html)
        self.assertIn('/static/logos/picasso_name_only.png', html)
        self.assertNotIn('id="home-avg-speed"', html)

    def test_static_logo_assets_are_served(self):
        for path in (
            "/static/logos/picasso_logo.png",
            "/static/logos/picasso_name_only.png",
            "/static/logos/picasso_name_full.png",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertTrue(response.get_data(), path)


class AppTestModeSmokeTest(unittest.TestCase):
    def test_app_test_mode_exposes_fake_live_data(self):
        original_argv = sys.argv[:]
        try:
            sys.argv = ["app.py", "--teste"]
            for module_name in [
                "backend.routes",
                "backend.routes.music",
                "backend.routes.gps",
                "backend.routes.vehicle",
                "backend.routes.system",
                "backend.routes.radio",
                "backend.services",
                "backend.services.mpd_service",
                "backend.services.music_library",
                "backend.services.gps_service",
                "backend.services.obd_service",
                "backend.services.rtlsdr_service",
                "app",
            ]:
                sys.modules.pop(module_name, None)

            app_module = importlib.import_module("app")
            client = app_module.app.test_client()

            response = client.get("/api/status")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()

            self.assertTrue(payload["gps"]["connected"])
            self.assertTrue(payload["obd"]["connected"])
            self.assertTrue(payload["radio"]["connected"])
            self.assertTrue(payload["music"]["connected"])
            self.assertGreaterEqual(payload["music"]["elapsed"], 0)
            self.assertGreater(payload["obd"]["direct"]["speed_kmh"], -1)
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
