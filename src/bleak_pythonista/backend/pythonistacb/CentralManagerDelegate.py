import sys
import asyncio
from functools import wraps
import logging
from typing import Optional, List, Callable, Dict, Any, cast, TYPE_CHECKING
import threading

if sys.version_info < (3, 11):
    from async_timeout import timeout as async_timeout
else:
    from asyncio import timeout as async_timeout

from pythonista import _cb
from bleak_pythonista.backend.pythonistacb.types import (
    CBUUID,
    CBPeripheral,
    CBService,
    CBCharacteristic,
    CBCentralManagerState,
    CBCentralManagerDelegate,
    CBCentralManager,
)


from bleak.exc import BleakError


logger = logging.getLogger(__name__)

DisconnectCallback = Callable[[], None]


_CENTRAL_MANAGER_METHOD = Callable[[CBCentralManager, Any], None]
_CENTRAL_MANAGER_DELEGATE_METHOD = Callable[[CBCentralManagerDelegate, Any], None]


def should_reset_on_exc(func: _CENTRAL_MANAGER_METHOD):
    @wraps(func)
    def wrapper(self: CBCentralManager, *args, **kwargs) -> None:
        try:
            return func(self, *args, **kwargs)
        except AttributeError:
            pass
        except Exception as e:
            try:
                self.delegate.reset()
            except AttributeError as attribute_error:
                raise attribute_error from e
            except Exception:
                raise e

    return wrapper


def ensure_thread_safe(
    func: _CENTRAL_MANAGER_DELEGATE_METHOD,
):
    @wraps(func)
    def wrapper(
        self: CBCentralManagerDelegate, *args, **kwargs
    ) -> Optional[asyncio.Handle]:
        if self.event_loop.is_closed():
            return None

        def callback() -> None:
            func(self, *args, **kwargs)

        return self.event_loop.call_soon_threadsafe(callback)

    return wrapper


class CentralManager(_cb.CentralManager):
    def __init__(self, delegate: CBCentralManagerDelegate):
        super().__init__()
        self.delegate: CBCentralManagerDelegate = delegate
        self._scanning: bool = False

        self._scanning_service_uuids: Optional[set[CBUUID]] = None

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    @property
    def scanning_services_uuids(self) -> Optional[set[CBUUID]]:
        return self._scanning_service_uuids

    @scanning_services_uuids.setter
    def scanning_services_uuids(self, services_uids: Optional[set[CBUUID]] = None):
        if services_uids:
            services_uids = set([uuid.lower() for uuid in services_uids])
        self._scanning_service_uuids = services_uids

    @should_reset_on_exc
    def did_update_scanning(self, is_scanning: bool) -> None:
        self._scanning = is_scanning
        self.delegate.did_update_scanning(self._scanning)

    def start_scan(self) -> None:
        logger.debug("CM: start scanning")
        super().scan_for_peripherals()
        self.did_update_scanning(True)

    def stop_scan(self) -> None:
        logger.debug("CM: stop scanning")
        super().stop_scan()
        self._scanning_service_uuids = None
        self.did_update_scanning(False)

    def reset(self):
        self.delegate = None

    @should_reset_on_exc
    def did_update_state(self) -> None:
        logger.debug("CM: Did update state: %i" % self.state)
        self.delegate.did_update_state()

    @should_reset_on_exc
    def did_discover_peripheral(self, p: CBPeripheral) -> None:
        logger.debug("CM: Did discover peripheral: %s (%s)" % (p.name, p.uuid))
        self.delegate.did_discover_peripheral(p)

    @should_reset_on_exc
    def did_connect_peripheral(self, p: CBPeripheral) -> None:
        logger.debug("CM: Did connect peripheral: %s (%s)" % (p.name, p.uuid))
        self.delegate.did_connect_peripheral(p)

    @should_reset_on_exc
    def did_fail_to_connect_peripheral(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        logger.debug(
            "CM: Did fail to connect peripheral: %s (%s) -- Error: %s"
            % (p.name, p.uuid, error)
        )
        self.delegate.did_fail_to_connect_peripheral(p, error)

    @should_reset_on_exc
    def did_disconnect_peripheral(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        logger.debug(
            "CM: Did disconnect peripheral: %s (%s) -- Error: %s"
            % (p.name, p.uuid, error)
        )
        self.delegate.did_disconnect_peripheral(p, error)

    @should_reset_on_exc
    def did_discover_services(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        logger.debug(
            "CB: Did discover services for peripheral: %s (%s)" % (p.name, p.uuid)
        )
        self.delegate.did_discover_services(p, error)

    @should_reset_on_exc
    def did_discover_characteristics(self, s: CBService, error: Optional[str]) -> None:
        logger.debug("CM: Did discover characteristics for service: %s" % (s.uuid,))
        self.delegate.did_discover_characteristics(s, error)

    @should_reset_on_exc
    def did_write_value(self, c: CBCharacteristic, error: Optional[str]) -> None:
        logger.debug("CM: Did write value for characteristic: %s" % c.uuid)
        self.delegate.did_write_value(c, error)

    @should_reset_on_exc
    def did_update_value(self, c: CBCharacteristic, error: Optional[str]) -> None:
        logger.debug("CM: Did update value for characteristic: %s" % c.uuid)
        self.delegate.did_update_value(c, error)

    def scan_for_peripherals_with_services(
        self, service_uuids: Optional[List[CBUUID]] = None
    ) -> None:
        self.scanning_services_uuids = service_uuids
        self.start_scan()


class CentralManagerDelegate:
    def __init__(self):
        self._peripherals: Dict[CBUUID, CBPeripheral] = {}

        self.event_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._connect_futures: Dict[CBUUID, asyncio.Future[bool]] = {}

        self.callbacks: Dict[int, Callable[[CBPeripheral], None]] = {}

        self._disconnect_callbacks: Dict[CBUUID, DisconnectCallback] = {}

        self._disconnect_futures: Dict[CBUUID, asyncio.Future[None]] = {}

        self._did_update_state_event: threading.Event = threading.Event()

        self.central_manager: CBCentralManager = cast(
            CBCentralManager, CentralManager(cast(CBCentralManagerDelegate, self))
        )

        self._did_update_state_event.wait(1)

        cm_state: CBCentralManagerState = CBCentralManagerState(
            self.central_manager.state
        )

        if cm_state is CBCentralManagerState.UNSUPPORTED:
            raise BleakError("BLE is unsupported")

        if cm_state is CBCentralManagerState.UNAUTHORIZED:
            raise BleakError("BLE is not authorized - check iOS privacy settings")

        if cm_state is not CBCentralManagerState.POWERED_ON:
            raise BleakError("Bluetooth device is turned off")

        self._did_start_scanning_event: Optional[asyncio.Event] = None
        self._did_stop_scanning_event: Optional[asyncio.Event] = None

    def __del__(self):
        self.central_manager.reset()
        del self.central_manager

    def reset(self) -> None:
        self.__del__()
        self.central_manager = cast(
            CBCentralManager, CentralManager(cast(CBCentralManagerDelegate, self))
        )
        logger.debug("CMD: CM reset success")

    async def start_scan(self, service_uuids: Optional[list[CBUUID]] = None) -> None:
        self.central_manager.scan_for_peripherals_with_services(service_uuids)

        event = asyncio.Event()
        self._did_start_scanning_event = event
        if not self.central_manager.is_scanning:
            await event.wait()

    async def stop_scan(self):
        self.central_manager.stop_scan()

        event = asyncio.Event()
        self._did_stop_scanning_event = event
        if self.central_manager.is_scanning:
            await event.wait()

    async def connect(
        self,
        p: CBPeripheral,
        disconnect_callback: DisconnectCallback,
        timeout: float = 10.0,
    ):
        try:
            self._disconnect_callbacks[p.uuid] = disconnect_callback
            future = self.event_loop.create_future()

            self._connect_futures[p.uuid] = future

            try:
                self.central_manager.connect_peripheral(p)
                async with async_timeout(timeout):
                    await future
            finally:
                del self._connect_futures[p.uuid]

        except asyncio.TimeoutError:
            logger.debug(f"Connection timed out after {timeout} seconds.")
            del self._disconnect_callbacks[p.uuid]
            future = self.event_loop.create_future()

            self._disconnect_futures[p.uuid] = future
            try:
                self.central_manager.cancel_peripheral_connection(p)
                await future
            finally:
                del self._disconnect_futures[p.uuid]

            raise

    async def disconnect(self, p: CBPeripheral):
        future = self.event_loop.create_future()

        self._disconnect_futures[p.uuid] = future
        try:
            self.central_manager.cancel_peripheral_connection(p)
            await future
        finally:
            del self._disconnect_futures[p.uuid]

    def did_update_scanning(self, is_scanning: bool) -> None:
        if is_scanning:
            if self._did_start_scanning_event:
                self._did_start_scanning_event.set()
        else:
            if self._did_stop_scanning_event:
                self._did_stop_scanning_event.set()

    @ensure_thread_safe
    def did_update_state(self) -> None:
        cm_state = CBCentralManagerState(self.central_manager.state)
        state_msg = str(cm_state)
        if state_msg:
            logger.debug(state_msg)

        self._did_update_state_event.set()

    @ensure_thread_safe
    def did_discover_peripheral(self, p: CBPeripheral):
        self._peripherals[p.uuid] = p
        self.central_manager.connect_peripheral(p)

    @ensure_thread_safe
    def did_connect_peripheral(self, p: CBPeripheral):
        future = self._connect_futures.get(p.uuid, None)
        if future is not None:
            future.set_result(True)

        p.discover_services()

    @ensure_thread_safe
    def did_fail_to_connect_peripheral(
        self, p: CBPeripheral, error: Optional[str] = None
    ):
        future = self._connect_futures.get(p.uuid, None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"failed to connect: {error}"))
            else:
                future.set_result(False)

    @ensure_thread_safe
    def did_disconnect_peripheral(self, p: CBPeripheral, error: Optional[str] = None):
        logger.debug("Peripheral Device disconnected!")
        future = self._disconnect_futures.get(p.uuid, None)
        if future is not None:
            if error is not None:
                future.set_exception(BleakError(f"disconnect failed: {error}"))
            else:
                future.set_result(None)

        callback = self._disconnect_callbacks.pop(p.uuid, None)

        if callback is not None:
            callback()
        self._peripherals.pop(p.uuid, None)

    @ensure_thread_safe
    def did_discover_services(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        assert not error  # FIXME: should use future?
        # future = self._connect_futures.get(p.uuid, None)
        # if future is not None:
        #     if error is not None:
        #         future.set_exception(BleakError(f"failed to connect: {error}"))
        #     else:
        #         future.set_result(False)

        if self.central_manager.scanning_services_uuids:
            found_services = p.services
            if found_services:
                found_services_uids = set([s.uuid.lower() for s in found_services])
                for uuid in found_services_uids:
                    if uuid in self.central_manager.scanning_services_uuids:
                        self._process_callbacks(p)
        else:
            self._process_callbacks(p)

    def _process_callbacks(self, p: CBPeripheral):
        for callback in self.callbacks.values():
            # if callback: # always True
            callback(p)

    @ensure_thread_safe
    def did_discover_characteristics(
        self, s: CBCharacteristic, error: Optional[str]
    ) -> None: ...

    @ensure_thread_safe
    def did_write_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...

    @ensure_thread_safe
    def did_update_value(self, c: CBCharacteristic, error: Optional[str]) -> None: ...


if __name__ == "__main__":

    async def main():
        m = CentralManagerDelegate()
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        try:
            await m.start_scan()
            while True:
                await asyncio.sleep(3)
        except KeyboardInterrupt:
            logger.debug("Exiting...")
        except Exception as e:
            logger.error(e)
        finally:
            m.reset()
        logger.debug("Done")

    asyncio.run(main())
