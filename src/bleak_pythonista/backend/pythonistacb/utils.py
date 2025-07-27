import sys
import re
from typing import Tuple

__all__ = (
    "is_native_platform",
    "assert_native_platform",
)

PYTHONISTA_EXECUTABLE_REGEX = re.escape("Pythonista3.app")


def is_native_platform() -> Tuple[bool, str]:
    if sys.platform != "ios":
        return False, "Platform not supported, expected `ios`"
    if not re.search(PYTHONISTA_EXECUTABLE_REGEX, sys.executable):
        return False, "Executable not supported, expected `Pythonista3.app`"
    return True, ""


def assert_native_platform():
    result, reason = is_native_platform()
    assert result, reason
