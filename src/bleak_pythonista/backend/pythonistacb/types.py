# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>

import sys
import asyncio
from enum import IntEnum
from typing import Any, Optional, Protocol, List, Dict, Callable


if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

import _cb


CBUUID: TypeAlias = str
CBCharacteristicProp: TypeAlias = IntEnum
DEFAULT_RSSI: int = -50


class CBPeripheralState(IntEnum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class CBCentralManagerState(IntEnum):
    UNKNOWN = _cb.CM_STATE_UNKNOWN
    RESETTING = _cb.CM_STATE_RESETTING
    UNSUPPORTED = _cb.CM_STATE_UNSUPPORTED
    UNAUTHORIZED = _cb.CM_STATE_UNAUTHORIZED
    POWERED_OFF = _cb.CM_STATE_POWERED_OFF
    POWERED_ON = _cb.CM_STATE_POWERED_ON

    def __str__(self) -> str:
        return CENTRAL_MANAGER_STATE_TO_DEBUG.get(self, "")


CENTRAL_MANAGER_STATE_TO_DEBUG: Dict[CBCentralManagerState, str] = {
    CBCentralManagerState.UNKNOWN: "Cannot detect bluetooth device",
    CBCentralManagerState.RESETTING: "Bluetooth is resetting",
    CBCentralManagerState.UNSUPPORTED: "Bluetooth is unsupported",
    CBCentralManagerState.UNAUTHORIZED: "Bluetooth is unauthorized",
    CBCentralManagerState.POWERED_OFF: "Bluetooth is powered off",
    CBCentralManagerState.POWERED_ON: "Bluetooth is powered on",
}


class CBCharacteristicProperty(IntEnum):
    BROADCAST = _cb.CH_PROP_BROADCAST
    READ = _cb.CH_PROP_READ
    WRITE_WITHOUT_RESPONSE = _cb.CH_PROP_WRITE_WITHOUT_RESPONSE
    WRITE = _cb.CH_PROP_WRITE
    NOTIFY = _cb.CH_PROP_NOTIFY
    INDICATE = _cb.CH_PROP_INDICATE
    AUTHENTICATED_SIGNED_WRITES = _cb.CH_PROP_AUTHENTICATED_SIGNED_WRITES
    EXTENDED_PROPERTIES = _cb.CH_PROP_EXTENDED_PROPERTIES
    NOTIFY_ENCRYPTION_REQUIRED = _cb.CH_PROP_NOTIFY_ENCRYPTION_REQUIRED
    INDICATE_ENCRYPTION_REQUIRED = _cb.CH_PROP_INDICATE_ENCRYPTION_REQUIRED


class CBDescriptor:
    uuid: CBUUID
    value: Any


class CBCharacteristic(Protocol):
    properties: CBCharacteristicProperty
    value: Optional[Buffer]
    uuid: CBUUID  # hex

    @property
    def notifying(self) -> bool: ...

    # descriptors: List[CBDescriptor] # pythonista `_cb` module does not support descriptors


class CBService(Protocol):
    characteristics: List[CBCharacteristic]
    primary: bool
    uuid: CBUUID  # hex


class CBPeripheral(Protocol):
    manufacturer_data: Buffer
    name: Optional[str]
    uuid: CBUUID  # hex
    state: int
    services: List[CBService]

    def discover_services(self): ...
    def discover_characteristics(self, service: CBService): ...
    def set_notify_value(self, characteristic: CBCharacteristic, flag: bool): ...
    def write_characteristic_value(
        self, characteristic: CBCharacteristic, data: Buffer, with_response: bool
    ): ...
    def read_characteristic_value(self, characteristic: CBCharacteristic): ...


class CBCentralManager(Protocol):
    state: CBCentralManagerState
    delegate: "CBCentralManagerDelegate"

    @property
    def is_scanning(self) -> bool: ...

    @property
    def scanning_services_uuids(self) -> bool: ...

    def __init__(self) -> None: ...
    def scan_for_peripherals(self) -> None: ...
    def scan_for_peripherals_with_services(
        self, service_uuids: Optional[List[CBUUID]] = None
    ) -> None: ...
    def stop_scan(self) -> None: ...
    def reset(self) -> None: ...
    def connect_peripheral(self, p: CBPeripheral) -> None: ...
    def cancel_peripheral_connection(self, p: CBPeripheral) -> None: ...
    def did_discover_peripheral(self, p: CBPeripheral) -> None: ...
    def did_connect_peripheral(self, p: CBPeripheral) -> None: ...
    def did_fail_to_connect_peripheral(
        self, p: CBPeripheral, error: Optional[str]
    ) -> None: ...
    def did_disconnect_peripheral(
        self, p: CBPeripheral, error: Optional[str]
    ) -> None: ...
    def did_discover_services(self, p: CBPeripheral, error: Optional[str]) -> None: ...
    def did_discover_characteristics(
        self, s: CBService, error: Optional[str]
    ) -> None: ...
    def did_write_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...
    def did_update_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...
    def did_update_state(self) -> None: ...


class CBCentralManagerDelegate(Protocol):
    event_loop: asyncio.AbstractEventLoop
    callbacks: Dict[int, Callable[[CBPeripheral], None]] = {}
    central_manager: CBCentralManager

    def reset(self) -> None: ...

    def did_discover_peripheral(self, p: CBPeripheral) -> None: ...
    def did_connect_peripheral(self, p: CBPeripheral) -> None: ...
    def did_fail_to_connect_peripheral(
        self, p: CBPeripheral, error: Optional[str]
    ) -> None: ...
    def did_disconnect_peripheral(
        self, p: CBPeripheral, error: Optional[str]
    ) -> None: ...
    def did_discover_services(self, p: CBPeripheral, error: Optional[str]) -> None: ...
    def did_discover_characteristics(
        self, s: CBService, error: Optional[str]
    ) -> None: ...
    def did_write_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...
    def did_update_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...
    def did_update_state(self) -> None: ...
    def did_update_scanning(self, is_scanning: bool) -> None: ...


class CBSharedCentralManager(CBCentralManager):
    delegate: CBCentralManagerDelegate
    verbose: bool

    def verbose_log(self): ...
