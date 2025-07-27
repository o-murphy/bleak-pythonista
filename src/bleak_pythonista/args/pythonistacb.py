"""
-------------------------------
PythonistaCB backend arguments
-------------------------------
"""

from collections.abc import Callable
from typing import Optional, TypedDict


class CBScannerArgs(TypedDict, total=False):
    """
    Platform-specific :class:`BleakScanner` args for the PythonistaCB backend.
    """

    use_bdaddr: bool  # unsupported


NotificationDiscriminator = Callable[[bytes], bool]


class CBStartNotifyArgs(TypedDict, total=False):
    """PythonistaCB backend-specific dictionary of arguments for the
    :meth:`bleak.BleakClient.start_notify` method.
    """

    timeout: float
    notification_discriminator: Optional[NotificationDiscriminator]
    """
    A function that takes a single argument of a characteristic value
    and returns ``True`` if the value is from a notification or
    ``False`` if the value is from a read response.

    .. seealso:: :ref:`cb-notification-discriminator` for more info.
    """
