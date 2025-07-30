# Created on July, 07 2025 by o-murphy <https://github.com/o-murphy>
"""
CentralManagerDelegate will implement the CBCentralManagerDelegate protocol to
manage CoreBluetooth services and resources on the Central End
[pythonista.cb docs](https://omz-software.com/pythonista/docs/ios/cb.html)
"""

import itertools
import sys
import asyncio
from functools import wraps
import logging
from typing import Optional, List, Callable, Dict, Any, Iterable
import threading


if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

if sys.version_info < (3, 11):
    from async_timeout import timeout as async_timeout
else:
    from asyncio import timeout as async_timeout

if sys.version_info < (3, 10):
    from typing import cast
else:
    from typing_extensions import cast

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

from bleak_pythonista.backend.pythonistacb.types import (
    CB_UUID,
    CBPeripheral,
    CBService,
    CBCharacteristic,
    CBCentralManagerState,
    CBCharacteristicProperty,
    CBCentralManagerDelegate,
    CBCentralManager,
    DisconnectCallback,
)
from bleak_pythonista.args.pythonistacb import NotificationDiscriminator

from bleak.backends.client import NotifyCallback
from bleak.exc import BleakError

__all__ = (
    "CentralManager",
    "CentralManagerDelegate",
)


logger = logging.getLogger(__name__)


def should_reset_on_exc(func):
    """
    Decorates CentralManager method
    to reset it via it's delegate on exception
    """

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


def ensure_thread_safe(func):
    """
    Decorates CentralManagerDelegate method
    to run it thread safe in running asyncio loop
    """

    @wraps(func)
    def wrapper(
        self: CBCentralManagerDelegate, *args, **kwargs
    ) -> Optional[asyncio.Handle]:
        if self.event_loop.is_closed():
            return None

        def callback() -> None:
            func(self, *args, **kwargs)

        # noinspection PyTypeChecker
        return self.event_loop.call_soon_threadsafe(callback)

    return wrapper


class CentralManager(_cb.CentralManager):
    """
    Custom `CentralManager` wrapper is inheritance from `_cb.CentralManager`
    to allow having few manager instances,

    Described in docs `pythonista.cb.SharedCentralManager` do not allow it
    """

    def __init__(self, delegate: CBCentralManagerDelegate):
        super().__init__()
        self.delegate: CBCentralManagerDelegate = delegate
        self._scanning: bool = False

    def __del__(self):
        # require freeing resources on __del__
        # you should call `del <CentralManager>` in parent scope
        self.delegate = None
        # del self.delegate

    @property
    def is_scanning(self) -> bool:
        return self._scanning

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
        self.did_update_scanning(False)

    def reset(self):
        # require freeing resources on __del__
        # _cb.CentralManager can't reinstantiate itself!
        # You should call `del <CentralManager>` it and reinstantiate it in parent scope
        # self.delegate = None
        self.__del__()

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


class CentralManagerDelegate:
    def __init__(self):
        self._peripherals: Dict[CB_UUID, CBPeripheral] = {}

        self.event_loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._connect_futures: Dict[CB_UUID, asyncio.Future[bool]] = {}

        self.callbacks: Dict[int, Callable[[CBPeripheral], None]] = {}

        self._disconnect_callbacks: Dict[CB_UUID, DisconnectCallback] = {}

        self._disconnect_futures: Dict[CB_UUID, asyncio.Future[None]] = {}

        self._did_update_state_event: threading.Event = threading.Event()

        self._services_discovered_future = self.event_loop.create_future()

        self._services_discovered_futures: Dict[
            CB_UUID, asyncio.Future[List[CBService]]
        ] = {}

        self._characteristics_discovered_futures: dict[
            CB_UUID, asyncio.Future[list[CBCharacteristic]]
        ] = {}

        self._characteristic_read_futures: Dict[CB_UUID, asyncio.Future[Buffer]] = {}
        self._characteristic_write_futures: Dict[CB_UUID, asyncio.Future[None]] = {}

        self._characteristic_notify_callbacks: Dict[CB_UUID, NotifyCallback] = {}
        self._characteristic_notification_discriminators: Dict[
            CB_UUID, Optional[NotificationDiscriminator]
        ] = {}

        self.central_manager: CBCentralManager = cast(
            CBCentralManager, CentralManager(cast(CBCentralManagerDelegate, self))
        )

        self._did_update_state_event.wait(1)

        # According to `pythonista.cb` docs, it is not valid to call CBCentral
        # methods until the `CentralManager.did_update_state()` delegate method
        # is called and the current state is `CBManagerStatePoweredOn`.
        # It doesn't take long for the callback to occur, so we should be able
        # to do a blocking wait here without anyone complaining.

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
        # require freeing resources on __del__
        self.central_manager.reset()
        del self.central_manager

    def reset(self) -> None:
        # require freeing resources on __del__
        self.central_manager.reset()
        del self.central_manager
        self.central_manager = cast(
            CBCentralManager, CentralManager(cast(CBCentralManagerDelegate, self))
        )
        logger.debug("CMD: CM reset success")

    async def start_scan(self) -> None:
        self.central_manager.start_scan()

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
        disconnect_callback: Optional[DisconnectCallback] = None,
        timeout: float = 10.0,
    ):
        try:
            if disconnect_callback is not None:
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
            if self._disconnect_callbacks.get(p.uuid, None):
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

    def services_discovered_futures(self) -> Iterable[asyncio.Future[Any]]:
        """
        Gets all futures for this delegate.

        These can be used to handle any pending futures when a peripheral is disconnected.
        """
        services_discovered_future = (
            (self._services_discovered_future,)
            if hasattr(self, "_services_discovered_future")
            else ()
        )

        return itertools.chain(
            services_discovered_future,
            self._services_discovered_futures.values(),
            self._characteristics_discovered_futures.values(),
            self._characteristic_read_futures.values(),
            self._characteristic_write_futures.values(),
        )

    async def discover_services(
        self, p: CBPeripheral, timeout: float = 10.0
    ) -> List[CBService]:
        future = self.event_loop.create_future()
        self._services_discovered_futures[p.uuid] = future

        try:
            p.discover_services()
            p.discover_services()
            async with async_timeout(timeout):
                return await future or []
        except asyncio.TimeoutError:
            logger.debug(f"Discover services timed out after {timeout} seconds.")
            future.set_result([])
            return []
        finally:
            del self._services_discovered_futures[p.uuid]

    async def discover_characteristics(
        self, p: CBPeripheral, s: CBService, timeout: float = 10.0
    ) -> List[CBCharacteristic]:
        future = self.event_loop.create_future()
        self._characteristics_discovered_futures[s.uuid] = future

        try:
            p.discover_characteristics(s)
            async with async_timeout(timeout):
                return await future or []
        except asyncio.TimeoutError:
            logger.debug(f"Discovery timed out after {timeout} seconds.")
            future.set_result([])
            return []
        finally:
            del self._characteristics_discovered_futures[s.uuid]

    async def read_characteristic(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        use_cached: bool,
        timeout: float = 10.0,
    ) -> Buffer:
        value = c.value
        if value is not None and use_cached:
            return value

        future = self.event_loop.create_future()

        self._characteristic_read_futures[c.uuid] = future

        try:
            p.read_characteristic_value(c)
            async with async_timeout(timeout):
                return await future
        except asyncio.TimeoutError:
            logger.debug(f"Read characteristic timed out after {timeout} seconds.")
            future.set_result(b"")
            return b""
        finally:
            del self._characteristic_read_futures[c.uuid]

    async def write_characteristic(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        value: Buffer,
        response: CBCharacteristicProperty,
        timeout: float = 10.0,
    ) -> None:
        # In CoreBluetooth, there's no sign of success or failure for CBCharacteristicWriteWithoutResponse.
        # Determine if a response is expected based on the characteristic property.
        with_response = bool(response & CBCharacteristicProperty.WRITE)

        try:
            p.write_characteristic_value(c, value, with_response)
        except SystemError as err:
            # Assuming SystemError here means a Pythonista version issue (e.g., <3.5).
            raise SystemError(
                "Failed to write characteristic value: "
                "Writing characteristic values requires `Pythonista` version 3.5 or newer."
            ) from err

        if with_response:
            future = self.event_loop.create_future()
            self._characteristic_write_futures[c.uuid] = future
            try:
                # Use async_timeout from its package if you have it.
                # From async_timeout import timeout as async_timeout
                async with async_timeout(
                    timeout
                ):  # Using built-in asyncio.timeout in Python 3.11+
                    await future
            except asyncio.TimeoutError:
                logger.debug(f"Write characteristic timed out after {timeout} seconds.")
                future.set_result(
                    None
                )  # Indicate that the future completed (with a timeout)
            finally:
                del self._characteristic_write_futures[c.uuid]

    async def start_notifications(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        callback: NotifyCallback,
        notification_discriminator: Optional[NotificationDiscriminator] = None,
        timeout: float = 2.0,
    ) -> None:
        if c.uuid in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notifications already started")
        self._characteristic_notify_callbacks[c.uuid] = callback
        self._characteristic_notification_discriminators[c.uuid] = (
            notification_discriminator
        )
        try:
            p.set_notify_value(c, True)
            async with async_timeout(timeout):
                while True:
                    await asyncio.sleep(timeout / 10)
                    if c.notifying:
                        break
        except asyncio.TimeoutError:
            BleakError(
                f"Can't determine notification "
                f"for characteristic {c.uuid} ({id(c)}) start after {timeout}s"
            )

    async def stop_notifications(
        self,
        p: CBPeripheral,
        c: CBCharacteristic,
        timeout: float = 2.0,
    ) -> None:
        if c.uuid not in self._characteristic_notify_callbacks:
            raise ValueError("Characteristic notification never started")

        try:
            p.set_notify_value(c, False)
            async with async_timeout(timeout):
                while True:
                    await asyncio.sleep(timeout / 10)
                    if not c.notifying:
                        break

        except asyncio.TimeoutError:
            BleakError(
                f"Can't determine notification "
                f"for characteristic {c.uuid} ({id(c)}) stop after {timeout}s"
            )

        self._characteristic_notify_callbacks.pop(c.uuid)
        self._characteristic_notification_discriminators.pop(c.uuid)

    def did_update_scanning(self, is_scanning: bool) -> None:
        if is_scanning:
            if self._did_start_scanning_event:
                self._did_start_scanning_event.set()
        else:
            if self._did_stop_scanning_event:
                self._did_stop_scanning_event.set()

    # Protocol Functions

    @ensure_thread_safe
    def did_update_state(self) -> None:
        cm_state = CBCentralManagerState(self.central_manager.state)
        state_msg = str(cm_state)
        if state_msg:
            logger.debug(state_msg)

        self._did_update_state_event.set()

    @ensure_thread_safe
    def did_discover_peripheral(self, p: CBPeripheral) -> None:
        # Note: this function might be called several times for the same device.
        # This can happen, for instance, when an active scan is done, and the
        # second call with contain the data from the BLE scan response.
        # Example a first time with the following keys in advertisementData:
        # ['kCBAdvDataLocalName', 'kCBAdvDataIsConnectable', 'kCBAdvDataChannel']
        # ... and later a second time with other keys (and values) such as:
        # ['kCBAdvDataServiceUUIDs', 'kCBAdvDataIsConnectable', 'kCBAdvDataChannel']
        #
        # i.e. it is best not to trust advertisementData for later use and data
        # from it should be copied.
        #
        # This behaviour can't be affected by now,
        # but CentralManagerDelegate keeps discovered devices
        # in CentralManagerDelegate._peripherals dict by uuid
        # and updates it if discovered again

        self._peripherals[p.uuid] = p

        # `cb_.did_discover_peripheral` does not handle `Peripheral.services`
        # we can't scan for peripherals by services without
        # peripheral connection, so connecting is required

        for callback in self.callbacks.values():
            # if callback: # always True
            callback(p)

    @ensure_thread_safe
    def did_connect_peripheral(self, p: CBPeripheral) -> None:
        future = self._connect_futures.get(p.uuid, None)
        if future is not None:
            future.set_result(True)

        # `cb_.did_connect_peripheral` does not handle `Peripheral.services`
        # we can't scan for peripherals by services without
        # peripheral connection, so connecting is required
        # p.discover_services()

    @ensure_thread_safe
    def did_fail_to_connect_peripheral(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        future = self._connect_futures.get(p.uuid, None)
        if future is not None:
            if error is not None:
                exception = BleakError(f"failed to connect: {error}")
                future.set_exception(exception)
            else:
                future.set_result(False)

    @ensure_thread_safe
    def did_disconnect_peripheral(
        self, p: CBPeripheral, error: Optional[str] = None
    ) -> None:
        logger.debug("Peripheral Device disconnected!")
        future = self._disconnect_futures.get(p.uuid, None)
        if future is not None:
            if error is not None:
                exception = BleakError(f"disconnect failed: {error}")
                future.set_exception(exception)
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
        future = self._services_discovered_futures.get(p.uuid, None)
        if future is not None:
            if error is not None:
                exception = BleakError(f"Failed to discover services {error}")
                future.set_exception(exception)
            else:
                logger.debug(f"Services discovered for peripheral {p.uuid}")
                future.set_result(p.services)

    @ensure_thread_safe
    def did_discover_characteristics(self, s: CBService, error: Optional[str]) -> None:
        future = self._characteristics_discovered_futures.get(s.uuid, None)
        if not future:
            logger.debug(
                f"Unexpected event did_discover_characteristics for service {s.uuid}: ({id(s)})"
            )
            return

        if error is not None:
            exception = BleakError(
                f"Failed to discover characteristics for service {s.uuid} ({id(s)}): {error}"
            )
            future.set_exception(exception)
        else:
            logger.debug(f"Characteristics discovered for service {s.uuid} ({id(s)}")
            future.set_result(s.characteristics)

    @ensure_thread_safe
    def did_update_value(
        self,
        c: CBCharacteristic,
        error: Optional[str],
    ) -> None:
        value = c.value

        future = self._characteristic_read_futures.get(c.uuid)

        # If error is set, then we know this was a read response.
        # Otherwise, if there is a pending read request, we can't tell if this is a read response or notification.
        # If the user provided a notification discriminator, we can use that to
        # identify if this callback is due to a notification by analysing the value.
        # If not, and there is a future (pending read request), we assume it is a read response but can't know for sure.
        if not error:
            assert value is not None

            notification_discriminator = (
                self._characteristic_notification_discriminators.get(c.uuid)
            )
            if not future or (
                notification_discriminator and notification_discriminator(bytes(value))
            ):
                notify_callback = self._characteristic_notify_callbacks.get(c.uuid)

                if notify_callback:
                    notify_callback(bytearray(value))
                    return

        if not future:
            logger.warning(
                "Unexpected event didUpdateValueForCharacteristic "
                "for 0x%04x with value: %r and error: %r",
                c.uuid,
                value,
                error,
            )
            return

        if error is not None:
            exception = BleakError(f"Failed to read characteristic {c.uuid}: {error}")
            future.set_exception(exception)
        else:
            logger.debug("Read characteristic value")
            assert value is not None
            future.set_result(value)

    @ensure_thread_safe
    def did_write_value(
        self,
        c: CBCharacteristic,
        error: Optional[str],
    ) -> None:
        future = self._characteristic_write_futures.get(c.uuid, None)
        if not future:
            return  # event only expected on writing with response
        if error is not None:
            exception = BleakError(f"Failed to write characteristic {c.uuid}: {error}")
            future.set_exception(exception)
        else:
            logger.debug("Write Characteristic Value")
            future.set_result(None)

    # # NOTE: The code bellow is undone, it should be implemented soon for safe resources freeing
    # @ensure_thread_safe
    # def shutdown_services_futures(self, exception: BleakError) -> None:
    #     """Clears all futures and callbacks related to a disconnected or failed-to-connect peripheral."""
    #     # Cancel and remove futures for the specific peripheral
    #
    #     for future in self.services_discovered_futures():
    #         try:
    #             future.set_exception(BleakError("disconnected"))
    #         except asyncio.InvalidStateError:
    #             # the future was already done
    #             pass
    #
    #     # Clear the internal dictionaries related to characteristics and services
    #     # These are cleared regardless of the peripheral because the method is designed to be global now
    #     self._services_discovered_futures.clear()
    #     self._characteristics_discovered_futures.clear()
    #     self._characteristic_read_futures.clear()
    #     self._characteristic_write_futures.clear()
    #     self._characteristic_notify_callbacks.clear()
    #     self._characteristic_notification_discriminators.clear()
    #
    #     logger.debug("Shutdown services futures globally")

    # @ensure_thread_safe
    # def shutdown_connection_futures(self, exception: BleakError) -> None:
    #     for future in itertools.chain(
    #         self._connect_futures.values(), self._disconnect_futures.values()
    #     ):
    #         try:
    #             future.set_exception(exception)
    #         except asyncio.InvalidStateError:
    #             pass
    #
    #     self._connect_futures.clear()
    #     self._disconnect_futures.clear()

    # @ensure_thread_safe
    # def shutdown(self, exception: BleakError = BleakError("shutdown")) -> None:
    #     """Performs a complete shutdown of all managed futures and callbacks."""
    #     # self.shutdown_connection_futures(exception)
    #     self.shutdown_services_futures(exception)
    #     self._peripherals.clear()
    #     logger.debug("Full shutdown completed")


if __name__ == "__main__":
    from bleak_pythonista.backend.pythonistacb.utils import assert_native_platform

    assert_native_platform()

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    async def main():
        m = CentralManagerDelegate()

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
