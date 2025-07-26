# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>

import sys
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"

from bleak_pythonista.args.pythonistacb import CBScannerArgs as _CBScannerArgs

import logging
from typing import Any, Literal, Optional

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

from bleak_pythonista.backend.pythonistacb.CentralManagerDelegate import (
    CentralManagerDelegate,
)
from bleak_pythonista.backend.pythonistacb.types import (
    CBUUID,
    DEFAULT_RSSI,
    CBPeripheral,
    CBService,
)

from bleak.backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    BaseBleakScanner,
)
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class BleakScannerPythonistaCB(BaseBleakScanner):
    """The native iOS Bleak BLE Scanner.

    Documentation:
    https://omz-software.com/pythonista/docs/ios/cb.html

    pythonista `_cb` module doesn't explicitly use Bluetooth addresses to identify peripheral
    devices because private devices may obscure their Bluetooth addresses. To cope
    with this, pythonista `_cb` module uses UUIDs for each peripheral. Bleak uses
    this for the BLEDevice address on macOS.

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received.
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode. Not
            supported on iOS! Will raise: class:`BleakError` if set to
            ``"passive"``
        **timeout (float):
             The scanning timeout to be used, in case of missing
            ``stop_scan`` method.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[list[CBUUID]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        *,
        cb: _CBScannerArgs = None,
        **kwargs: Any,
    ):
        super().__init__(detection_callback, service_uuids)

        if scanning_mode == "passive":
            raise BleakError("iOS does not support passive scanning")

        if cb:
            # only for compat with CoreBluetooth backend args
            _use_bdaddr = cb.get("use_bdaddr", False)
            if _use_bdaddr:
                raise BleakError("iOS does not support use_bdaddr")

        manager = CentralManagerDelegate()
        assert manager
        self._manager = manager
        self._timeout: float = kwargs.get("timeout", 5.0)

    @override
    async def start(self) -> None:
        self.seen_devices = {}

        def callback(p: CBPeripheral) -> None:
            # Extract advertisement data
            manufacturer_data: Dict[int, bytes] = {}
            service_data: Dict[CBUUID, CBService] = {}
            service_uuids: List[CBUUID] = []
            tx_power: Optional[int] = None  # not provided use None
            rssi: Optional[int] = DEFAULT_RSSI  # not provided, use default

            # Process service data
            if p.services:
                service_data = {s.uuid.lower(): s for s in p.services}
                service_uuids = list(service_data.keys())

            # Process manufacturer data
            manufacturer_binary_data = p.manufacturer_data
            if manufacturer_binary_data:
                manufacturer_id = int.from_bytes(
                    manufacturer_binary_data[0:2], byteorder="little"
                )
                manufacturer_value = bytes(manufacturer_binary_data[2:])
                manufacturer_data[manufacturer_id] = manufacturer_value

            # Create advertisement data
            advertisement_data = AdvertisementData(
                local_name=p.name,
                manufacturer_data=manufacturer_data,
                # FIXME: pythonista `_cb` module does not have methods
                #  to get service_data as Buffer
                #  we will use CBService object instead
                service_data=service_data,
                service_uuids=service_uuids,
                tx_power=tx_power,
                rssi=rssi,  # Default RSSI, cb module doesn't provide this
                platform_data=(p, rssi),
            )

            # Check if this advertisement passes the service UUID filter
            if not self.is_allowed_uuid(service_uuids):
                return

            # Create or update a device
            device = self.create_or_update_device(
                key=p.uuid,
                address=p.uuid,  # On iOS, we use UUID as an address
                name=p.name,
                details=(
                    p,
                    self._manager.central_manager.delegate,
                ),  # add delegate to details
                adv=advertisement_data,
            )

            # Call detection callbacks
            self.call_detection_callbacks(device, advertisement_data)

        # Create and set delegate
        self._manager.callbacks[id(self)] = callback

        # Start scanning
        await self._manager.start_scan(self._service_uuids)

    @override
    async def stop(self) -> None:
        await self._manager.stop_scan()
        self._manager.callbacks.pop(id(self), None)


if __name__ == "__main__":
    import asyncio

    def detection_cb(*args, **kwargs):
        print("discovered")
        print(locals())

    async def scan(services=None):
        scanner = BleakScannerPythonistaCB(detection_cb, services)
        try:
            await scanner.start()
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            logger.debug("Existing...")
        except Exception as e:
            logger.error(e)
        finally:
            await scanner.stop()
        logger.debug("Done")

    async def main():
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        await scan()
        print("\ndiscover bitchat service")
        await scan(["f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c"])

    asyncio.run(main())
