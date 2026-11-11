import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from chessai.remote_control import create_handler


class RemoteControlTests(unittest.TestCase):
    def setUp(self):
        self.running = False
        self.calls = []

        def run(action):
            self.calls.append(action)
            if action == "start":
                self.running = True
            if action == "stop":
                self.running = False
            if action == "is-active":
                return self.running

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler("secret-token", run))
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, method="GET", token="secret-token"):
        request = Request(self.url + path, method=method,
                          headers={"Authorization": f"Bearer {token}"})
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_authentication_and_start_stop(self):
        with self.assertRaises(HTTPError) as error:
            self.request("/start", "POST", token="wrong")
        self.assertEqual(error.exception.code, 401)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.request("/status")["running"])
        self.assertTrue(self.request("/start", "POST")["running"])
        self.assertFalse(self.request("/stop", "POST")["running"])
        with self.assertRaises(HTTPError) as error:
            self.request("/restart", "POST")
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
