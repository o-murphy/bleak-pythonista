# ruff: noqa: F403, F405

from .backend import *
from .args import *

from bleak import *
from bleak import BleakScanner as _BleakScanner

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

if sys.version_info < (3, 11):
    from typing_extensions import Unpack
else:
    from typing import Unpack


class BleakScanner(_BleakScanner):
    @override
    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[list[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        *,
        bluez: Optional[BlueZScannerArgs] = None,
        cb: Optional[CBScannerArgs] = None,
        backend: Optional[type[BaseBleakScanner]] = BleakScannerPythonistaCB,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            detection_callback,
            service_uuids,
            scanning_mode,
            bluez=bluez or {},
            cb=cb or {},
            backend=backend,
            **kwargs,
        )

    @override
    @classmethod
    async def discover(
        cls,
        timeout: float = 5.0,
        *,
        return_adv: bool = False,
        **kwargs: Unpack[_BleakScanner.ExtraArgs],
    ):
        kwargs.setdefault("backend", BleakScannerPythonistaCB)
        return await super().discover(timeout, return_adv=return_adv, **kwargs)

    @override
    @classmethod
    async def find_device_by_address(
        cls,
        device_identifier: str,
        timeout: float = 10.0,
        **kwargs: Unpack[_BleakScanner.ExtraArgs],
    ) -> Optional[BLEDevice]:
        kwargs.setdefault("backend", BleakScannerPythonistaCB)
        return await super().find_device_by_address(
            device_identifier, timeout, **kwargs
        )

    @override
    @classmethod
    async def find_device_by_name(
        cls, name: str, timeout: float = 10.0, **kwargs: Unpack[_BleakScanner.ExtraArgs]
    ) -> Optional[BLEDevice]:
        kwargs.setdefault("backend", BleakScannerPythonistaCB)
        return await super().find_device_by_name(name, timeout, **kwargs)

    @override
    @classmethod
    async def find_device_by_filter(
        cls,
        filterfunc: AdvertisementDataFilter,
        timeout: float = 10.0,
        **kwargs: Unpack[_BleakScanner.ExtraArgs],
    ) -> Optional[BLEDevice]:
        kwargs.setdefault("backend", BleakScannerPythonistaCB)
        return await super().find_device_by_filter(filterfunc, timeout, **kwargs)
