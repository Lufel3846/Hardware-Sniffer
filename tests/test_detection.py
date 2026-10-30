import os
import tempfile
import unittest

from Scripts.datasets import chipset_data
from Scripts.gpu_identifier import GPUIdentifier
from Scripts.platforms.linux import LinuxHardwareInfo


CPUINFO_4C_8T = "\n\n".join(
    "processor\t: {}\nvendor_id\t: GenuineIntel\ncpu family\t: 6\nmodel\t\t: 158\n"
    "model name\t: Intel(R) Core(TM) i7-7700 CPU @ 3.60GHz\nstepping\t: 9\n"
    "physical id\t: 0\ncore id\t\t: {}\ncpu cores\t: 4\nflags\t\t: sse sse2 avx avx2".format(index, index % 4)
    for index in range(8)
) + "\n\n"


class StubUtils:
    def __init__(self, files):
        self.files = files

    def read_file(self, path):
        return self.files.get(path)


def make_linux_info(files=None):
    info = LinuxHardwareInfo.__new__(LinuxHardwareInfo)
    info.utils = StubUtils(files or {})
    info.lookup_codename = lambda name, description: "Kaby Lake"
    return info


class GPUIdentifierTests(unittest.TestCase):
    def test_nvidia_ids_missing_from_table_fall_back_to_prefix_rules(self):
        identifier = GPUIdentifier()

        for device_id, codename in (("0FCC", "Kepler"), ("1191", "Kepler"), ("1294", "Kepler"), ("05F1", "Tesla"), ("06CB", "Fermi")):
            self.assertEqual(identifier.classify_gpu("10DE-" + device_id)["Codename"], codename)

    def test_nvidia_table_entries_take_precedence(self):
        identifier = GPUIdentifier()

        self.assertEqual(identifier.classify_gpu("10DE-1180")["Codename"], "Kepler")
        self.assertEqual(identifier.classify_gpu("10DE-2204")["Codename"], "Ampere")
        self.assertEqual(identifier.classify_gpu("10DE-1140")["Codename"], "Fermi")


class LinuxHardwareInfoTests(unittest.TestCase):
    def test_secure_boot_reads_value_after_efivar_attributes(self):
        info = make_linux_info()

        with tempfile.TemporaryDirectory() as temporary_dir:
            efivar_path = os.path.join(temporary_dir, "SecureBoot")
            with open(efivar_path, "wb") as efivar_file:
                efivar_file.write(b"\x06\x00\x00\x00\x01")
            self.assertEqual(info.get_secure_boot_state(efivar_path), "Enabled")

            with open(efivar_path, "wb") as efivar_file:
                efivar_file.write(b"\x06\x00\x00\x00\x00")
            self.assertEqual(info.get_secure_boot_state(efivar_path), "Disabled")

            self.assertEqual(info.get_secure_boot_state(os.path.join(temporary_dir, "missing")), "Disabled")

    def test_core_count_uses_physical_cores(self):
        info = make_linux_info({"/proc/cpuinfo": CPUINFO_4C_8T})

        cpu = info.cpu()

        self.assertEqual(cpu["Core Count"], "04")
        self.assertEqual(cpu["CPU Count"], "01")


class ChipsetDataTests(unittest.TestCase):
    def test_has_no_placeholder_ids(self):
        self.assertNotIn("8086-????", chipset_data.chipset_controllers)


if __name__ == "__main__":
    unittest.main()
