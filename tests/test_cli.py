import subprocess
import sys

from genicam_fastcs import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "genicam_fastcs", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
