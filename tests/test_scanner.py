import pytest

from bleak_pythonista.backend.pythonistacb._fake_cb import *
from bleak_pythonista import BleakScanner, BleakError, CBCentralManagerState


@pytest.fixture(autouse=True) # Keep it autouse for global state reset
def reset_central_manager_global_state():
    """Fixture to reset the global state of the fake CentralManager for each test."""
    # This code runs BEFORE each test (setup)
    CentralManager.state = CM_STATE_POWERED_OFF  # A safe default
    CentralManager._will_discover = [] # Ensure it's always empty to start
    yield
    # Teardown (optional for this specific use case, but good practice)
    CentralManager.state = CM_STATE_UNKNOWN
    CentralManager._will_discover = []


@pytest.fixture
def hrm_peripheral():
    """A fixture to provide a pre-configured Heart Rate Monitor peripheral."""
    hrm = Peripheral("HeartRateMonitor", "12345678-1234-1234-1234-123456789abc")
    hr_service = Service("180D", primary=True)
    hr_characteristic = Characteristic("2A37", CH_PROP_READ | CH_PROP_NOTIFY, b"\x00\x60")
    hr_service._add_characteristic(hr_characteristic)
    hrm._add_service(hr_service)
    return hrm


@pytest.mark.asyncio
async def test_scanner_BT_READY():
    # The autouse fixture has already reset the state.
    # Now, set the state and peripherals specifically for THIS test.
    CentralManager.state = CM_STATE_POWERED_ON
    test_data = [
        Peripheral("HeartRateMonitor", "12345678-1234-1234-1234-123456789abc"),
        Peripheral("TempSensor", "87654321-4321-4321-4321-cba987654321")
    ]
    CentralManager._will_discover = test_data # This will now work correctly

    devices = await BleakScanner.discover(timeout=1)

    assert len(devices) == len(test_data)
    devices.sort(key=lambda d: d.address)

    for i, device in enumerate(devices):
        assert device.address == test_data[i].uuid
        assert device.name == test_data[i].name


test_scanner_BT_NOT_READY_data =[
    (CM_STATE_UNKNOWN, "Bluetooth device is turned off"),
    (CM_STATE_UNAUTHORIZED, "BLE is not authorized - check iOS privacy settings"),
    (CM_STATE_POWERED_OFF, "Bluetooth device is turned off"),
]

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state, pattern",
    test_scanner_BT_NOT_READY_data,
    ids=[
        i.__repr__()
        for i in [
            CBCentralManagerState.UNKNOWN,
            CBCentralManagerState.UNAUTHORIZED,
            CBCentralManagerState.POWERED_OFF,
        ]
    ],
)
async def test_scanner_BT_NOT_READY(state, pattern):
    # This is a bit of a guess, as I don't have the context of fake_cb.CentralManager
    # It might be that the state attribute expects the enum member directly,
    # or it might expect its value. This code assumes it expects the value.
    CentralManager.state = state
    with pytest.raises(BleakError, match=pattern):
        devices = await BleakScanner.discover(timeout=1)


@pytest.mark.asyncio
async def test_scanner_NO_BT_DEVICES():
    # The fixture already sets the state and clears peripherals.
    # We just need to make sure the state is POWERED_ON
    CentralManager.state = CM_STATE_POWERED_ON
    devices = await BleakScanner.discover(timeout=1)
    assert len(devices) == 0

@pytest.mark.asyncio
async def test_scanner_WITH_SERVICES(hrm_peripheral):
    CentralManager.state = CM_STATE_POWERED_ON

    # hrm = Peripheral("HeartRateMonitor", "12345678-1234-1234-1234-123456789abc")
    # hr_service = Service("180D", primary=True)  # Heart Rate Service UUID
    # hr_characteristic = Characteristic("2A37", CH_PROP_READ | CH_PROP_NOTIFY, b"\x00\x60")  # Heart Rate Measurement
    # hr_service._add_characteristic(hr_characteristic)
    # hrm._add_service(hr_service)

    # # Fake Temperature Sensor
    # temp_sensor = Peripheral("TempSensor", "87654321-4321-4321-4321-cba987654321")
    # temp_service = Service("1809", primary=True)  # Health Thermometer Service
    # temp_characteristic = Characteristic("2A1C", CH_PROP_READ | CH_PROP_INDICATE, b"\x00\x00\x00\x42")  # Temperature Measurement
    # temp_service._add_characteristic(temp_characteristic)
    # temp_sensor._add_service(temp_service)

    CentralManager._will_discover.append(hrm_peripheral)
    devices = await BleakScanner.discover(timeout=1)
    assert len(devices) == 1
    assert devices[0].name == "HeartRateMonitor"
    assert devices[0].address == "12345678-1234-1234-1234-123456789abc"
    assert len(devices[0].details) == 2
    peref, delegate = devices[0].details
    assert peref.services == hrm_peripheral.services

@pytest.mark.asyncio
async def test_scanner_BY_SERVICES(hrm_peripheral):
    CentralManager.state = CM_STATE_POWERED_ON

    # Fake Temperature Sensor
    temp_sensor = Peripheral("UNKNOWN", "00000000-4321-4321-4321-cba987654321")
    temp_service = Service("FFFF", primary=True)  # Health Thermometer Service
    temp_characteristic = Characteristic("2A1C", CH_PROP_READ | CH_PROP_INDICATE, b"\x00\x00\x00\x42")  # Temperature Measurement
    temp_service._add_characteristic(temp_characteristic)
    temp_sensor._add_service(temp_service)

    CentralManager._will_discover = [hrm_peripheral, temp_sensor]
    devices = await BleakScanner.discover(service_uuids=["180D"], timeout=1)
    assert len(devices) == 1
    assert devices[0].name == "HeartRateMonitor"
    assert devices[0].address == "12345678-1234-1234-1234-123456789abc"
    assert len(devices[0].details) == 2
    peref, delegate = devices[0].details
    assert peref.services == hrm_peripheral.services
