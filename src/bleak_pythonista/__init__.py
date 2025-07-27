# ruff: noqa: F403, F405
from typing import Tuple, Dict

from .backend import *
from .args import *

from bleak import *
from bleak import BleakScanner as _BleakScanner
from bleak import BleakClient as _BleakClient

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

if sys.version_info < (3, 11):
    from typing_extensions import Unpack
else:
    from typing import Unpack


class BleakScanner(_BleakScanner):  # type: ignore[no-redef]
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
    async def discover(  # type: ignore[override]
        cls,
        timeout: float = 5.0,
        *,
        return_adv: bool = False,
        **kwargs: Unpack[_BleakScanner.ExtraArgs],
    ) -> Union[list[BLEDevice], Dict[str, Tuple[BLEDevice, AdvertisementData]]]:
        kwargs.setdefault("backend", BleakScannerPythonistaCB)
        return await super().discover(timeout, return_adv=return_adv, **kwargs)  # type: ignore[call-overload]

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


class BleakClient(_BleakClient):  # type: ignore[no-redef]
    @override
    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, str],
        disconnected_callback: Optional[Callable[[BleakClient], None]] = None,
        services: Optional[Iterable[str]] = None,
        *,
        timeout: float = 10.0,
        pair: bool = False,
        winrt: Optional[WinRTClientArgs] = None,
        backend: Optional[type[BaseBleakClient]] = BleakClientPythonistaCB,
        **kwargs: Any,
    ) -> None:
        PlatformBleakClient = (
            get_platform_client_backend_type() if backend is None else backend
        )

        self._backend = PlatformBleakClient(
            address_or_ble_device,
            disconnected_callback=(
                None
                if disconnected_callback is None
                else functools.partial(disconnected_callback, self)
            ),
            services=(
                None if services is None else set(map(normalize_uuid_str, services))
            ),
            timeout=timeout,
            winrt=winrt or {},
            **kwargs,
        )
        self._pair_before_connect = pair


def cli() -> None:  # type: ignore[no-redef]
    import argparse

    parser = argparse.ArgumentParser(
        description="Perform Bluetooth Low Energy device scan"
    )
    # Selecting adapter on pythonista is unsupported
    # parser.add_argument("-i", dest="adapter", default=None, help="HCI device")
    parser.add_argument(
        "-t", dest="timeout", type=int, default=5, help="Duration to scan for"
    )
    args = parser.parse_args()

    out = asyncio.run(BleakScanner.discover(timeout=float(args.timeout)))
    for o in out:
        print(str(o))


if __name__ == "__main__":
    cli()
