import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    if sys.platform != "ios":
        assert False, "This backend is only available on iOS"

if sys.version_info < (3, 12):
    from typing_extensions import Buffer, override
else:
    from collections.abc import Buffer
    from typing import override

import asyncio
import logging
from typing import Any, Optional, Union

from bleak import BleakScanner
from bleak.assigned_numbers import gatt_char_props_to_strs
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, NotifyCallback

from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak.exc import BleakDeviceNotFoundError, BleakError

from bleak_pythonista.args.pythonistacb import CBStartNotifyArgs
from bleak_pythonista.backend.pythonistacb.scanner import BleakScannerPythonistaCB

from bleak_pythonista.backend.pythonistacb.types import (
    CB_UUID,
    CBPeripheral,
    CBService,
    CBCentralManagerDelegate,
    CBPeripheralState,
    CBCharacteristicProperty,
    DEFAULT_ATT_MTU_SIZE,
)


__all__ = ("BleakClientPythonistaCB",)


logger = logging.getLogger(__name__)


class BleakClientPythonistaCB(BaseBleakClient):
    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, CB_UUID],
        services: Optional[set[CB_UUID]] = None,
        **kwargs: Any,
    ):
        super().__init__(address_or_ble_device, **kwargs)

        self._peripheral: Optional[CBPeripheral] = None
        # self._delegate: Optional[PeripheralDelegate] = None
        self._delegate: Optional[CBCentralManagerDelegate] = None

        if isinstance(address_or_ble_device, BLEDevice):
            (self._peripheral, self._delegate) = address_or_ble_device.details

        self._requested_services = services if services else None

    def __str__(self):
        return "BleakClientPythonistaCB ({})".format(self.address)

    @override
    async def connect(self, pair: bool = False, **kwargs: Any) -> None:
        if pair:
            logger.debug("Explicit pairing is not available in PythonistaCB.")

        timeout = kwargs.get("timeout", self._timeout)

        if self._peripheral is None:
            device: BLEDevice = await BleakScanner.find_device_by_address(
                self.address, timeout=timeout, backend=BleakScannerPythonistaCB
            )

            if device:
                self._peripheral, self._delegate = device.details
            else:
                raise BleakDeviceNotFoundError(
                    self.address, f"Device with address {self.address} was not found"
                )

        def disconnect_callback() -> None:
            # Ensure that `get_services` retrieves services again, rather
            # than using the cached object
            self.services = None

            # If there are any pending futures waiting for delegate callbacks, we
            # need to raise an exception since the callback will no longer be
            # called because the device is disconnected.

            for future in self._delegate.services_discovered_futures():
                try:
                    future.set_exception(BleakError("disconnected"))
                except asyncio.InvalidStateError:
                    # the future was already done
                    pass

            if self._disconnected_callback:
                self._disconnected_callback()

        manager = self._delegate
        logger.debug("CentralManagerDelegate  at {}".format(manager))
        logger.debug("Connecting to BLE device @ {}".format(self.address))
        await manager.connect(self._peripheral, disconnect_callback, timeout=timeout)

        # Now get services
        await self._get_services()

    @override
    async def disconnect(self) -> None:
        """Disconnect from the peripheral device"""
        if self._peripheral is None:
            return

        state = CBPeripheralState(self._peripheral.state)
        if state is not CBPeripheralState.CONNECTED:
            return

        assert self._delegate
        await self._delegate.disconnect(self._peripheral)

    @property
    @override
    def is_connected(self) -> bool:
        """Checks for current active connection"""
        state = CBPeripheralState(self._peripheral.state)
        return (
            False if self._peripheral is None else state is CBPeripheralState.CONNECTED
        )

    @property
    @override
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        # Use type CBCharacteristicWriteWithoutResponse to get maximum write
        # value length based on the negotiated ATT MTU size. Add the ATT header
        # length (+3) to get the actual ATT MTU size.
        assert self._peripheral

        # pyhtonista `_cb` module not provide method to get MTU size
        return DEFAULT_ATT_MTU_SIZE + 3

    @override
    async def pair(self, *args: Any, **kwargs: Any) -> None:
        """Attempt to pair with a peripheral.

        Raises:
            NotImplementedError:
                This is not available on iOS since there is no explicit API
                to do a pairing. Instead, the docs state that it "auto-pairs",
                when trying to read a characteristic that requires encryption.

        """
        raise NotImplementedError("Pairing is not available in PythonistaCB.")

    @override
    async def unpair(self) -> None:
        """
        Remove pairing information for a peripheral.

        Raises:
            NotImplementedError:
                This is not available on iOS since there is no explicit API
                to do a pairing.
        """
        raise NotImplementedError("Pairing is not available in PythonistaCB.")

    async def _get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self.services is not None:
            return self.services

        services = BleakGATTServiceCollection()

        logger.debug("Retrieving services...")
        assert self._delegate

        cb_services: Optional[list[CBService]] = await self._delegate.discover_services(
            self._peripheral
        )

        matching_cb_services = (
            [
                service
                for service in cb_services
                if service.uuid in self._requested_services
            ]
            if self._requested_services
            else cb_services
        )

        if matching_cb_services:
            for service in matching_cb_services:
                serv = BleakGATTService(service, id(service), service.uuid)
                services.add_service(serv)

                logger.debug(
                    "Retrieving characteristics for service {}".format(service.uuid)
                )

                characteristics = await self._delegate.discover_characteristics(
                    self._peripheral, service
                )

                for characteristic in characteristics:
                    char = BleakGATTCharacteristic(
                        characteristic,
                        id(characteristic),
                        characteristic.uuid,
                        list(gatt_char_props_to_strs(characteristic.properties)),
                        lambda: self.mtu_size,
                        serv,
                    )
                    services.add_characteristic(char)

        logger.debug("Services resolved for %s", str(self))
        self.services = services
        return self.services

    @override
    async def read_gatt_char(
        self, characteristic: BleakGATTCharacteristic, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to read from.

        Returns:
            (bytearray) The read data.

        """
        assert self._delegate
        output = await self._delegate.read_characteristic(
            self._peripheral,
            characteristic.obj,
            use_cached=kwargs.get("use_cached", False),
        )
        value = bytearray(output)
        logger.debug("Read Characteristic {0} : {1}".format(characteristic.uuid, value))
        return value

    @override
    async def read_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor."""
        raise NotImplementedError(
            "GATT descriptor reading is not available in PythonistaCB."
        )

    @override
    async def write_gatt_char(
        self, characteristic: BleakGATTCharacteristic, data: Buffer, response: bool
    ) -> None:
        with_response: CBCharacteristicProperty = (
            CBCharacteristicProperty.WRITE  # CBCharacteristicWriteWithResponse
            if response
            else CBCharacteristicProperty.WRITE_WITHOUT_RESPONSE  # CBCharacteristicWriteWithoutResponse
        )
        await self._delegate.write_characteristic(
            self._peripheral, characteristic.obj, data, with_response
        )
        logger.debug(f"Write Characteristic {characteristic.uuid} : {data}")

    @override
    async def write_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, data: Buffer
    ) -> None:
        """Perform a write operation on the specified GATT descriptor."""
        raise NotImplementedError(
            "GATT descriptor reading is not available in PythonistaCB."
        )

    @override
    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        *,
        cb: CBStartNotifyArgs,  # NOTE: not matching BleakClient.start_notify signature
        **kwargs: Any,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.
        """
        assert self._delegate is not None

        await self._delegate.start_notifications(
            self._peripheral,
            characteristic.obj,
            callback,
            cb.get("notification_discriminator"),
            cb.get("timeout", 20),
        )

    @override
    async def stop_notify(self, characteristic: BleakGATTCharacteristic) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            characteristic (BleakGATTCharacteristic: The characteristic to deactivate
                notification/indication on.
        """
        assert self._delegate
        await self._delegate.stop_notifications(self._peripheral, characteristic.obj)


if __name__ == "__main__":
    from bleak_pythonista.backend.pythonistacb.utils import assert_native_platform

    assert_native_platform()

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
