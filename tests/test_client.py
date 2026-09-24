import unittest

from stb_rdc.client import BridgeError
from tests.fakes import FakeBridgeClient


class ClientTests(unittest.TestCase):
    def test_exact_managed_session_is_resolved(self) -> None:
        client = FakeBridgeClient()
        self.assertEqual(client.session("verify33")["pane"], "%5")

    def test_unknown_session_fails_closed(self) -> None:
        client = FakeBridgeClient()
        with self.assertRaisesRegex(BridgeError, "managed session not found"):
            client.session("missing")


if __name__ == "__main__":
    unittest.main()
