import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"
