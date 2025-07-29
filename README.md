# `Bleak` compatible backend for `Pythonista` iOS app

[![license]][MIT]
[![pypi]][PyPiUrl]
[![py-versions]][sources]
[![Made in Ukraine]][SWUBadge]

[![Pytest](https://github.com/o-murphy/bleak-pythonista/actions/workflows/pytest.yml/badge.svg)](https://github.com/o-murphy/bleak-pythonista/actions/workflows/pytest.yml)
[![Mypy](https://github.com/o-murphy/bleak-pythonista/actions/workflows/mypy.yml/badge.svg)](https://github.com/o-murphy/bleak-pythonista/actions/workflows/mypy.yml)
[![Ruff](https://github.com/o-murphy/bleak-pythonista/actions/workflows/ruff.yml/badge.svg)](https://github.com/o-murphy/bleak-pythonista/actions/workflows/ruff.yml)


[sources]:
https://github.com/o-murphy/bleak-pythonista

[license]:
https://img.shields.io/github/license/o-murphy/bleak-pythonista?style=flat-square

[MIT]:
https://opensource.org/license/MIT

[pypi]:
https://img.shields.io/pypi/v/bleak-pythonista?style=flat-square&logo=pypi

[PyPiUrl]:
https://pypi.org/project/bleak-pythonista/

[pepy]:
https://pepy.tech/project/bleak-pythonista

[py-versions]:
https://img.shields.io/pypi/pyversions/bleak-pythonista?style=flat-square

[Made in Ukraine]:
https://img.shields.io/badge/made_in-Ukraine-ffd700.svg?labelColor=0057b7&style=flat-square

[SWUBadge]:
https://stand-with-ukraine.pp.ua

**This module uses `bleak` backend API to implement a compatible solution for `Pythonista` iOS app. 
It uses Pythonista built-in `_cb` module, that is wrapper to iOS `CoreBluetooth`.**

> [!CAUTION]
> This project is in `beta`, use it with caution

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
from bleak_pythonista import BleakScanner, BleakClient

async def main():
    devices = await BleakScanner.discover(
        service_uuids=["<some-service-uuid>"]  # optional
    )
    for d in devices:
        print(d)        
        client = BleakClient(d)
        await client.connect()
        print(client.services)
    
asyncio.run(main())
```

With `bleak` itself
```python
import asyncio
from bleak import BleakScanner, BleakClient
from bleak_pythonista import BleakScannerPythonistaCB, BleakClientPythonistaCB

async def main():
    devices = await BleakScanner.discover(
        service_uuids=["<some-service-uuid>"],  # optional
        backend=BleakScannerPythonistaCB,
    )
    for d in devices:
        print(d)        
        client = BleakClient(d, backend=BleakClientPythonistaCB)
        await client.connect()
        print(client.services)
    
asyncio.run(main())
```

> [!WARNING]
> DO NOT NAME YOUR SCRIPT `bleak.py` or `bleak_pythonista`! It will cause a circular import error.

## What's done?

* CentralManagerDelegate (for now for scanning purpose only)
* client.BleakClientPythonistaCB
* scanner.BleakScannerPythonistaCB
* `_cb` and `pythonista.cb` stubs
* fake `cb.py` for testing with backend simulation on unsupported platforms 

> [!TIP]
> THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.