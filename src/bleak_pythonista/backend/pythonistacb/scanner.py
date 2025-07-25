import sys
from typing import TYPE_CHECKING, Dict, List

from bleak_pythonista.args.pythonistacb import CBScannerArgs as _CBScannerArgs

if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"

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
                service_data = {
                    s.uuid.lower(): s for s in p.services
                }
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
