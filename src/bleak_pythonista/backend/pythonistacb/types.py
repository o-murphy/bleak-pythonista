# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>

import sys

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias

import asyncio
from enum import IntEnum
from typing import Any, Optional, Protocol, List, Dict, Callable, Iterable

try:
    import _cb  # type: ignore[import-untyped, import-not-found]
except ImportError:
    import warnings

    warnings.filterwarnings(
        "once",
        message="The `_cb` module could not be loaded.*",  # Use regex to match the message
        category=UserWarning,
    )

    # No need for a manual flag, the filter handles it
    warnings.warn(
        "The `_cb` module could not be loaded. Falling back to a simulated `_cb` module, which may have limited functionality.",
        UserWarning,
    )
    from bleak_pythonista.backend.pythonistacb import _fake_cb as _cb

from bleak_pythonista.args.pythonistacb import NotificationDiscriminator

from bleak.backends.scanner import AdvertisementData
from bleak.backends.client import NotifyCallback

__all__ = (
    "CB_UUID",
    "DEFAULT_RSSI",
    "DEFAULT_ATT_MTU_SIZE",
    "DisconnectCallback",
    "CBPeripheralState",
    "CBCentralManagerState",
    "CENTRAL_MANAGER_STATE_TO_DEBUG",
    "CBCharacteristicProperty",
    "CBDescriptor",
    "CBCharacteristic",
    "CBService",
    "CBPeripheral",
    "CBCentralManager",
    "CBCentralManagerDelegate",
    "CBSharedCentralManager",
    "CBAdvertisementData",
)


CB_UUID: TypeAlias = str
DEFAULT_RSSI: int = -50  # NOTE: maybe should be -127
DEFAULT_ATT_MTU_SIZE = 23  # NOTE: maybe should 244 for bluetooth >= 5.0

DisconnectCallback = Callable[[], None]


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
    uuid: CB_UUID
    value: Any


class CBCharacteristic(Protocol):
    properties: CBCharacteristicProperty
    value: Optional[Buffer]
    uuid: CB_UUID  # hex

    @property
    def notifying(self) -> bool: ...

    # descriptors: List[CBDescriptor] # pythonista `_cb` module does not support descriptors


class CBService(Protocol):
    characteristics: List[CBCharacteristic]
    primary: bool
    uuid: CB_UUID  # hex


class CBPeripheral(Protocol):
    manufacturer_data: Buffer
    name: Optional[str]
    uuid: CB_UUID  # hex
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

    def __init__(self) -> None: ...
    def scan_for_peripherals(self) -> None: ...
    def start_scan(self) -> None: ...
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

    async def start_scan(
        self, service_uuids: Optional[list[CB_UUID]] = None
    ) -> None: ...
    async def stop_scan(self) -> None: ...

    async def connect(
        self,
        p: CBPeripheral,
        disconnect_callback: DisconnectCallback,
        timeout: float = 10.0,
    ) -> None: ...
    async def disconnect(self, p: CBPeripheral) -> None: ...

    def services_discovered_futures(self) -> Iterable[asyncio.Future[Any]]: ...

    async def discover_services(self, p: CBPeripheral) -> List[CBService]: ...
    async def discover_characteristics(
        self, p: CBPeripheral, c: CBCharacteristic
    ) -> List[CBCharacteristic]: ...
    async def read_characteristic(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        use_cached: bool,
        timeout: int = 20,
    ) -> Buffer: ...
    async def write_characteristic(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        value: Buffer,
        response: CBCharacteristicProperty,
    ) -> None: ...

    async def start_notifications(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        callback: NotifyCallback,
        notification_discriminator: Optional[NotificationDiscriminator] = None,
        timeout: Optional[float] = 20.0,
    ) -> None: ...

    async def stop_notifications(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        timeout: Optional[float] = 20.0,
    ) -> None: ...

    def reset(self) -> None: ...
    def did_update_scanning(self, is_scanning: bool) -> None: ...

    # Protocol Functions

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


class CBSharedCentralManager(CBCentralManager):
    delegate: CBCentralManagerDelegate
    verbose: bool

    def verbose_log(self): ...


class CBAdvertisementData(AdvertisementData):
    # NOTE: pythonista `_cb` module does not have methods
    # to get service_data as Buffer
    # we will use CBService object instead

    service_data: dict[str, CBService]  # type: ignore[assignment]
