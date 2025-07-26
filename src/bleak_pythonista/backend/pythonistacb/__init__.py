# ruff: noqa: F403

from .CentralManagerDelegate import *
from .scanner import *
from .types import *

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sys

    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"
