import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from geolab.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def fetch(self, path):
        with urlopen(self.base + path, timeout=10) as response:
            return json.load(response)

    def test_inputs_and_truth_separated(self):
        scene = self.fetch("/api/scene?id=benchmark-01")
        self.assertNotIn("camera", scene)
        self.assertEqual(self.fetch("/api/truth?id=benchmark-01")["camera"], [1, 3])
        self.assertEqual(len(self.fetch("/api/scenes")["scenes"]), 51)

    def test_default_and_empty_selection_differ(self):
        a = self.fetch("/api/solve?id=benchmark-01&n=32")
        b = self.fetch("/api/solve?id=benchmark-01&n=32&obs=")
        self.assertEqual(a["observation_ids"], ["o1", "o2"])
        self.assertEqual(b["observation_ids"], [])
        self.assertGreater(b["area_upper"], a["area_upper"])

    def test_invalid_queries_rejected(self):
        for url in ["/api/solve?id=benchmark-01&n=99999", "/api/solve?id=benchmark-01&obs=bad", "/api/truth?id=../secret"]:
            with self.assertRaises(HTTPError) as ctx:
                self.fetch(url)
            self.assertEqual(ctx.exception.code, 400)
            ctx.exception.close()
        for url in ["/../docs/mission.txt", "/data/truth/benchmark-01.json"]:
            with self.assertRaises(HTTPError) as ctx:
                self.fetch(url)
            self.assertEqual(ctx.exception.code, 404)
            ctx.exception.close()


if __name__ == "__main__":
    unittest.main()
