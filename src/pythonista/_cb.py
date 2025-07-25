# _cb_mock.py

from typing import Optional, List

# Constants from _cb.pyi
CM_STATE_UNKNOWN: int = 0
CM_STATE_RESETTING: int = 1
CM_STATE_UNSUPPORTED: int = 2
CM_STATE_UNAUTHORIZED: int = 3
CM_STATE_POWERED_OFF: int = 4
CM_STATE_POWERED_ON: int = 5

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
    """
    Mock Characteristic class.
    Provides basic attributes and can be initialized with dummy values for testing.
    """
    def __init__(self, uuid: str, properties: int = 0, value: Optional[bytes] = None, notifying: bool = False):
        self.uuid = uuid
        self.properties = properties
        self.value = value
        self.notifying = notifying
        print(f"Mock Characteristic created: UUID={self.uuid}, Properties={self.properties}")

class Service:
    """
    Mock Service class.
    Holds a list of mock Characteristic objects.
    """
    def __init__(self, uuid: str, primary: bool = True, characteristics: Optional[List[Characteristic]] = None):
        self.uuid = uuid
        self.primary = primary
        self.characteristics = characteristics if characteristics is not None else []
        print(f"Mock Service created: UUID={self.uuid}, Primary={self.primary}")

class Peripheral:
    """
    Mock Peripheral class.
    Simulates a Bluetooth peripheral device.
    """
    def __init__(self, uuid: str, name: Optional[str] = None, manufacturer_data: bytes = b'', state: int = CM_STATE_POWERED_ON, services: Optional[List[Service]] = None):
        self.uuid = uuid
        self.name = name
        self.manufacturer_data = manufacturer_data
        self.state = state
        self.services = services if services is not None else []
        print(f"Mock Peripheral created: UUID={self.uuid}, Name={self.name}")

    def discover_services(self):
        """Mock method for discovering services."""
        print(f"Mock Peripheral {self.uuid}: discover_services called.")
        # In a real mock, you might populate self.services here for testing scenarios
        pass

    def discover_characteristics(self, service: Service):
        """Mock method for discovering characteristics for a given service."""
        print(f"Mock Peripheral {self.uuid}: discover_characteristics for service {service.uuid} called.")
        # In a real mock, you might populate service.characteristics here
        pass

    def set_notify_value(self, characteristic: Characteristic, flag: bool = True):
        """Mock method for setting notification value for a characteristic."""
        characteristic.notifying = flag
        print(f"Mock Peripheral {self.uuid}: set_notify_value for characteristic {characteristic.uuid} to {flag}.")
        pass

    def write_characteristic_value(self, characteristic: Characteristic, data: bytes, with_response: bool):
        """Mock method for writing a characteristic value."""
        characteristic.value = data
        print(f"Mock Peripheral {self.uuid}: write_characteristic_value for {characteristic.uuid} with data {data}, with_response={with_response}.")
        pass

    def read_characteristic_value(self, characteristic: Characteristic) -> Optional[bytes]:
        """Mock method for reading a characteristic value."""
        print(f"Mock Peripheral {self.uuid}: read_characteristic_value for {characteristic.uuid}.")
        return characteristic.value # Return the mock value

class CentralManager:
    """
    Mock CentralManager class.
    Simulates a central Bluetooth manager.
    """
    def __init__(self):
        self.state = CM_STATE_POWERED_ON
        self._discovered_peripherals: List[Peripheral] = []
        print("Mock CentralManager initialized.")

    def scan_for_peripherals(self) -> None:
        """Mock method for scanning for peripherals."""
        print("Mock CentralManager: scan_for_peripherals called.")
        # You can add dummy peripherals to self.discovered_peripherals here for testing
        pass

    def stop_scan(self) -> None:
        """Mock method for stopping scan."""
        print("Mock CentralManager: stop_scan called.")
        pass

    def connect_peripheral(self, p: Peripheral) -> None:
        """Mock method for connecting to a peripheral."""
        print(f"Mock CentralManager: connect_peripheral to {p.uuid} called.")
        p.state = CM_STATE_POWERED_ON # Simulate connection
        self.did_connect_peripheral(p)
        pass

    def cancel_peripheral_connection(self, p: Peripheral) -> None:
        """Mock method for canceling peripheral connection."""
        print(f"Mock CentralManager: cancel_peripheral_connection to {p.uuid} called.")
        p.state = CM_STATE_POWERED_OFF # Simulate disconnection
        self.did_disconnect_peripheral(p, None)
        pass

    # Callback methods (these would typically be called by the native implementation)
    # For mocking, you might call these directly in your tests to simulate events.

    def did_discover_peripheral(self, p: Peripheral) -> None:
        """Mock callback for when a peripheral is discovered."""
        print(f"Mock CentralManager: did_discover_peripheral callback for {p.uuid}.")
        self._discovered_peripherals.append(p)

    def did_connect_peripheral(self, p: Peripheral) -> None:
        """Mock callback for when a peripheral connects."""
        print(f"Mock CentralManager: did_connect_peripheral callback for {p.uuid}.")

    def did_fail_to_connect_peripheral(self, p: Peripheral, error: Optional[str]) -> None:
        """Mock callback for when a peripheral fails to connect."""
        print(f"Mock CentralManager: did_fail_to_connect_peripheral callback for {p.uuid} with error: {error}.")

    def did_disconnect_peripheral(self, p: Peripheral, error: Optional[str]) -> None:
        """Mock callback for when a peripheral disconnects."""
        print(f"Mock CentralManager: did_disconnect_peripheral callback for {p.uuid} with error: {error}.")

    def did_discover_services(self, p: Peripheral, error: Optional[str]) -> None:
        """Mock callback for when services are discovered."""
        print(f"Mock CentralManager: did_discover_services callback for {p.uuid} with error: {error}.")

    def did_discover_characteristics(self, s: Service, error: Optional[str]) -> None:
        """Mock callback for when characteristics are discovered for a service."""
        print(f"Mock CentralManager: did_discover_characteristics callback for service {s.uuid} with error: {error}.")

    def did_write_value(self, c: Characteristic, error: Optional[str]) -> None:
        """Mock callback for when a characteristic value is written."""
        print(f"Mock CentralManager: did_write_value callback for characteristic {c.uuid} with error: {error}.")

    def did_update_value(self, c: Characteristic, error: Optional[str]) -> None:
        """Mock callback for when a characteristic value is updated (e.g., notification)."""
        print(f"Mock CentralManager: did_update_value callback for characteristic {c.uuid} with error: {error}.")

    def did_update_state(self):
        """Mock callback for when the central manager's state updates."""
        print(f"Mock CentralManager: did_update_state callback. Current state: {self.state}.")

# Expose all constants and classes as per __all__ in the original .pyi
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
