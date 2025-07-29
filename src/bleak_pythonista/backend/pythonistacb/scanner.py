# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"

if sys.version_info < (3, 12):
    from typing_extensions import override
else:
    from typing import override

import asyncio
import logging
from typing import Dict, List, Any, Literal, Optional

from bleak_pythonista.args.pythonistacb import CBScannerArgs as _CBScannerArgs

from bleak_pythonista.backend.pythonistacb.CentralManager import (
    CentralManagerDelegate,
)
from bleak_pythonista.backend.pythonistacb.types import (
    CB_UUID,
    DEFAULT_RSSI,
    CBPeripheral,
    CBService,
    CBAdvertisementData,
)

from bleak.backends.scanner import (
    AdvertisementDataCallback,
    BaseBleakScanner,
)
from bleak.exc import BleakError


__all__ = ("BleakScannerPythonistaCB",)

logger = logging.getLogger(__name__)


class BleakScannerPythonistaCB(BaseBleakScanner):
    """The native iOS Bleak BLE Scanner.

    Documentation:
    https://omz-software.com/pythonista/docs/ios/cb.html

    Pythonista `_cb` module doesn't explicitly use Bluetooth addresses to identify peripheral
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
        service_uuids: Optional[list[CB_UUID]] = None,
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
        loop = asyncio.get_running_loop()

        def callback(p: CBPeripheral) -> None:
            if self._service_uuids:
                asyncio.run_coroutine_threadsafe(
                    self._handle_peripheral_matching_services(p), loop
                )
            else:
                self._handle_peripheral(p)

        # Create and set delegate
        self._manager.callbacks[id(self)] = callback

        # Start scanning
        await self._manager.start_scan()

    @override
    async def stop(self) -> None:
        await self._manager.stop_scan()
        self._manager.callbacks.pop(id(self), None)

    def _handle_peripheral(self, p):
        # Extract advertisement data
        manufacturer_data: Dict[int, bytes] = {}
        service_data: Dict[CB_UUID, CBService] = {}
        service_uuids: List[CB_UUID] = []
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
        advertisement_data = CBAdvertisementData(
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
            details=(p, self._manager),
            adv=advertisement_data,
        )

        # Call detection callbacks
        self.call_detection_callbacks(device, advertisement_data)

    async def _handle_peripheral_matching_services(self, p: CBPeripheral) -> None:
        try:
            await self._manager.connect(p)
            services = await self._manager.discover_services(p)

            service_ids = [s.uuid.lower() for s in services or []]
            if not any(s in service_ids for s in self._service_uuids):
                await self._manager.disconnect(p)
                return

            # If matching → create adv and call detection callback
            self._handle_peripheral(p)

            await self._manager.disconnect(p)

        except Exception as e:
            logger.debug(f"Error during service filtering: {e}")
            try:
                await self._manager.disconnect(p)
            except Exception as e:
                logger.debug(f"Error during disconnecting: {e}")


if __name__ == "__main__":
    from bleak_pythonista.backend.pythonistacb.utils import assert_native_platform

    assert_native_platform()

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

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
        await scan()
        print("\ndiscover bitchat service")
        await scan(["f47b5e2d-4a9e-4c5a-9b3f-8e1d2c3a4b5c"])

    asyncio.run(main())
