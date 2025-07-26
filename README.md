# `Bleak` compatible backend for `Pythonista` iOS app

**This module uses `bleak` backend API to implement a compatible solution for `Pythonista` iOS app. 
It uses Pythonista built-in `_cb` module, that is wrapper to iOS `CoreBluetooth`.**

> [!CAUTION]
> This project is in early `beta` use with caution

* This backend refers to [Pythonista.cb docs](https://omz-software.com/pythonista/docs/ios/cb.html)
* This backend refers to existing [`macOS CoreBluetooth bleak backend`](https://github.com/hbldh/bleak/tree/develop/bleak/backends/corebluetooth) was used as a reference
* It also provides stub files for pythonista built-in modules as `_cb` and `pythonista.cb`, and fake `_cb.py` implementation for testing on unsupported platforms
* Use [`Bleak` docs](https://github.com/hbldh/bleak/blob/develop/README.rst) to explore how to use `Bleak`

## Table of Contents
* [Installation](#installation)
* [Usage](#usage)
* [What's done?](#whats-done)


## Installation
```Bash
pip install bleak-pythonista
```

## Usage
Direct import
```python
import asyncio
from bleak_pythonista import BleakScanner

async def main():
    devices = await BleakScanner.discover(
        service_uuids=["<some-service-uuid>"]  # optional
    )
    for d in devices:
        print(d)
    
asyncio.run(main())
```

With `bleak` itself
```python
import asyncio
from bleak import BleakScanner
from bleak_pythonista import BleakScannerPythonistaCB

async def main():
    devices = await BleakScanner.discover(
        service_uuids=["<some-service-uuid>"],  # optional
        backend=BleakScannerPythonistaCB,
    )
    for d in devices:
        print(d)
    
asyncio.run(main())
```

> [!WARNING]
> DO NOT NAME YOUR SCRIPT `bleak.py`! It will cause a circular import error.

## What's done?

* CentralManagerDelegate (for now for scanning purpose only)
* scanner.BleakScannerPythonistaCB
* `_cb` and `pythonista.cb` stubs
* fake `cb.py` for testing with backend simulation on unsupported platforms 

## Work in progress

* PeripheralDelegate
* client.BleakClientPythonistaCB

> [!TIP]
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.