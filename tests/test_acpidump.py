import os
import tempfile
import unittest
from unittest import mock

import HardwareSniffer


class StubFetcher:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def download_and_save_file(self, url, destination_path):
        self.calls += 1
        with open(destination_path, "wb") as file_handle:
            file_handle.write(self.data)


class StubUtils:
    def head(self, *args, **kwargs):
        pass


def make_sniffer(fetcher):
    sniffer = HardwareSniffer.HardwareSniffer.__new__(HardwareSniffer.HardwareSniffer)
    sniffer.fetcher = fetcher
    sniffer.u = StubUtils()
    sniffer.temporary_dir = tempfile.mkdtemp()
    return sniffer


class AcpidumpTests(unittest.TestCase):
    def setUp(self):
        self.working_dir = tempfile.TemporaryDirectory()
        self.previous_dir = os.getcwd()
        os.chdir(self.working_dir.name)

    def tearDown(self):
        os.chdir(self.previous_dir)
        self.working_dir.cleanup()

    def test_rejects_download_with_unexpected_hash(self):
        sniffer = make_sniffer(StubFetcher(b"MZ tampered"))

        with mock.patch("builtins.print"), self.assertRaises(Exception):
            sniffer.check_acpidump()

        self.assertFalse(os.path.exists("acpidump.exe"))

    def test_accepts_download_matching_pinned_hash(self):
        fetcher = StubFetcher(b"MZ trusted")

        with mock.patch.object(HardwareSniffer, "ACPIDUMP_SHA256", HardwareSniffer.hashlib.sha256(b"MZ trusted").hexdigest()):
            sniffer = make_sniffer(fetcher)
            path = sniffer.check_acpidump()
            self.assertEqual(sniffer.check_acpidump(), path)

        self.assertEqual(fetcher.calls, 1)

    def test_replaces_existing_untrusted_binary(self):
        with open("acpidump.exe", "wb") as file_handle:
            file_handle.write(b"MZ old")
        fetcher = StubFetcher(b"MZ trusted")

        with mock.patch.object(HardwareSniffer, "ACPIDUMP_SHA256", HardwareSniffer.hashlib.sha256(b"MZ trusted").hexdigest()), mock.patch("builtins.print"):
            make_sniffer(fetcher).check_acpidump()

        self.assertEqual(fetcher.calls, 1)


if __name__ == "__main__":
    unittest.main()
