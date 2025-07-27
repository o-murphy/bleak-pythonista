# mypy: ignore-errors
# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>
"""
FAKE pythonista `_cb` module to simulate backend
to simplify tests, mocking on other platforms
"""

from typing import Optional, List
import uuid
import threading
import warnings


warnings.warn(
    "The `_cb` module is for testing purposes only and should not be used in production.",
    UserWarning,
)

__all__ = (
    "CM_STATE_UNKNOWN",
    "CM_STATE_RESETTING",
    "CM_STATE_UNSUPPORTED",
    "CM_STATE_UNAUTHORIZED",
    "CM_STATE_POWERED_OFF",
    "CM_STATE_POWERED_ON",
    "CH_PROP_BROADCAST",
    "CH_PROP_READ",
    "CH_PROP_WRITE_WITHOUT_RESPONSE",
    "CH_PROP_WRITE",
    "CH_PROP_NOTIFY",
    "CH_PROP_INDICATE",
    "CH_PROP_AUTHENTICATED_SIGNED_WRITES",
    "CH_PROP_EXTENDED_PROPERTIES",
    "CH_PROP_NOTIFY_ENCRYPTION_REQUIRED",
    "CH_PROP_INDICATE_ENCRYPTION_REQUIRED",
    "Characteristic",
    "Service",
    "Peripheral",
    "CentralManager",
)

# State constants
CM_STATE_UNKNOWN: int = 0
CM_STATE_RESETTING: int = 1
CM_STATE_UNSUPPORTED: int = 2
CM_STATE_UNAUTHORIZED: int = 3
CM_STATE_POWERED_OFF: int = 4
CM_STATE_POWERED_ON: int = 5

# Characteristic property constants
CH_PROP_BROADCAST: int = 1
CH_PROP_READ: int = 2
CH_PROP_WRITE_WITHOUT_RESPONSE: int = 4
CH_PROP_WRITE: int = 8
CH_PROP_NOTIFY: int = 16
CH_PROP_INDICATE: int = 32
CH_PROP_AUTHENTICATED_SIGNED_WRITES: int = 64
CH_PROP_EXTENDED_PROPERTIES: int = 128
CH_PROP_NOTIFY_ENCRYPTION_REQUIRED: int = 256
CH_PROP_INDICATE_ENCRYPTION_REQUIRED: int = 512


class Characteristic:
    def __init__(
        self,
        uuid_str: str = None,
        properties: int = CH_PROP_READ | CH_PROP_WRITE,
        value: Optional[bytes] = None,
    ):
        self.properties: int = properties
        self.value: Optional[bytes] = value or b""
        self.uuid: str = uuid_str or str(uuid.uuid4())
        self.notifying: bool = False
        self._service = None

    def __repr__(self):
        return f"Characteristic(uuid={self.uuid}, properties={self.properties}, notifying={self.notifying})"


class Service:
    def __init__(self, uuid_str: str = None, primary: bool = True):
        self.characteristics: List[Characteristic] = []
        self.primary: bool = primary
        self.uuid: str = uuid_str or str(uuid.uuid4())
        self._peripheral = None

    def _add_characteristic(self, characteristic: Characteristic):
        """Helper method to add characteristics to this service"""
        characteristic._service = self
        self.characteristics.append(characteristic)

    def __repr__(self):
        return f"Service(uuid={self.uuid}, primary={self.primary}, characteristics={len(self.characteristics)})"


class Peripheral:
    def __init__(self, name: Optional[str] = None, uuid_str: str = None):
        self.manufacturer_data: bytes = b"\x00\x01\x02\x03"  # Fake manufacturer data
        self.name: Optional[str] = name or "FakeDevice"
        self.uuid: str = uuid_str or str(uuid.uuid4())
        self.state: int = 0
        self.services: List[Service] = []
        self._central_manager = None

    def _add_service(self, service: Service):
        """Helper method to add services to this peripheral"""
        service._peripheral = self
        self.services.append(service)

    def discover_services(self):
        """Simulate service discovery"""
        # In real implementation, this would trigger async discovery
        # For fake, we can immediately call the callback if central manager is set
        if self._central_manager:
            # Simulate some delay
            threading.Timer(
                0.001, lambda: self._central_manager.did_discover_services(self, None)
            ).start()

    def discover_characteristics(self, service: Service):
        """Simulate characteristic discovery for a service"""
        if self._central_manager:
            # Simulate some delay
            threading.Timer(
                0.001,
                lambda: self._central_manager.did_discover_characteristics(
                    service, None
                ),
            ).start()

    def set_notify_value(self, characteristic: Characteristic, flag: bool = True):
        """Enable/disable notifications for a characteristic"""
        if characteristic in [c for s in self.services for c in s.characteristics]:
            characteristic.notifying = flag
            # In real implementation, this might trigger a callback

    def write_characteristic_value(
        self, characteristic: Characteristic, data: bytes, with_response: bool = True
    ):
        """Write value to a characteristic"""
        if characteristic in [c for s in self.services for c in s.characteristics]:
            characteristic.value = data
            if self._central_manager:
                error = (
                    None if len(data) <= 512 else "Data too long"
                )  # Simulate error condition
                if with_response:
                    threading.Timer(
                        0.002,
                        lambda: self._central_manager.did_write_value(
                            characteristic, error
                        ),
                    ).start()

    def read_characteristic_value(self, characteristic: Characteristic):
        """Read value from a characteristic"""
        if characteristic in [c for s in self.services for c in s.characteristics]:
            if self._central_manager:
                # Simulate reading - update the characteristic value and call callback
                if not characteristic.value:
                    characteristic.value = b"fake_read_data"
                threading.Timer(
                    0.002,
                    lambda: self._central_manager.did_update_value(
                        characteristic, None
                    ),
                ).start()

    def __repr__(self):
        return f"Peripheral(name={self.name}, uuid={self.uuid}, state={self.state})"


class CentralManager:
    state: int = CM_STATE_POWERED_OFF

    _will_discover: List[Peripheral] = []

    def __init__(self) -> None: ...

    def scan_for_peripherals(self) -> None:
        """Start scanning for peripherals"""
        # Simulate discovering peripherals after a short delay
        for peripheral in self._will_discover:
            print("Will discover peripheral", peripheral)
            threading.Timer(
                0.002, lambda p=peripheral: self.did_discover_peripheral(p)
            ).start()

    def stop_scan(self) -> None:
        """Stop scanning for peripherals"""

    def connect_peripheral(self, p: Peripheral) -> None:
        """Connect to a peripheral"""
        p.state = 1

        # Simulate connection delay
        def connect():
            p._central_manager = self
            p.state = 2
            self.did_connect_peripheral(p)

        threading.Timer(0.003, connect).start()

    def cancel_peripheral_connection(self, p: Peripheral) -> None:
        """Disconnect from a peripheral"""

        def disconnect():
            p._central_manager = None
            p.state = 0
            self.did_disconnect_peripheral(p, None)

        threading.Timer(0.001, disconnect).start()

    # Callback methods - these would be overridden in real usage
    def did_discover_peripheral(self, p: Peripheral) -> None:
        """Called when a peripheral is discovered during scanning"""
        print(f"Discovered peripheral: {p}")

    def did_connect_peripheral(self, p: Peripheral) -> None:
        """Called when successfully connected to a peripheral"""
        print(f"Connected to peripheral: {p}")

    def did_fail_to_connect_peripheral(
        self, p: Peripheral, error: Optional[str]
    ) -> None:
        """Called when connection to peripheral fails"""
        print(f"Failed to connect to peripheral: {p}, error: {error}")

    def did_disconnect_peripheral(self, p: Peripheral, error: Optional[str]) -> None:
        """Called when disconnected from a peripheral"""
        print(f"Disconnected from peripheral: {p}, error: {error}")

    def did_discover_services(self, p: Peripheral, error: Optional[str]) -> None:
        """Called when services are discovered for a peripheral"""
        print(f"Discovered {len(p.services)} services for peripheral: {p}")

    def did_discover_characteristics(self, s: Service, error: Optional[str]) -> None:
        """Called when characteristics are discovered for a service"""
        print(f"Discovered {len(s.characteristics)} characteristics for service: {s}")

    def did_write_value(self, c: Characteristic, error: Optional[str]) -> None:
        """Called when a characteristic value write completes"""
        if error:
            print(f"Write failed for characteristic {c}: {error}")
        else:
            print(f"Successfully wrote to characteristic: {c}")

    def did_update_value(self, c: Characteristic, error: Optional[str]) -> None:
        """Called when a characteristic value is updated (read or notification)"""
        if error:
            print(f"Value update failed for characteristic {c}: {error}")
        else:
            print(f"Value updated for characteristic {c}: {c.value}")

    def did_update_state(self):
        """Called when the central manager state changes"""
        print(f"Central manager state updated: {self.state}")
