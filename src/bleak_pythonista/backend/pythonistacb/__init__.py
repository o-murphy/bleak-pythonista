import sys
from .CentralManagerDelegate import *
from .scanner import *
from .types import *

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"
