import sys
import pytest
import os
from bleak_pythonista.backend.pythonistacb import _fake_cb as _cb


@pytest.fixture(scope="session", autouse=True)
def mock_all_native_modules():
    """
    Replace all native modules with fakes and ensure the fake module's directory
    is on the import path.
    """
    # Get the directory where conftest.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Add the current directory (which contains fake_cb.py) to sys.path
    sys.path.insert(0, current_dir)

    fake_modules = {
        "_cb": _cb,
    }

    original_modules = sys.modules.copy()
    sys.modules.update(fake_modules)

    yield

    # Restore original sys.modules
    for module_name in fake_modules:
        if module_name in sys.modules:
            del sys.modules[module_name]

    # Restore any modules that were there before
    for name, module in original_modules.items():
        if name not in sys.modules:
            sys.modules[name] = module

    # Remove the current directory from sys.path
    if current_dir in sys.path:
        sys.path.remove(current_dir)