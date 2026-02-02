# Sokol Python Bindings

[![PyPI version](https://badge.fury.io/py/sokol.svg)](https://badge.fury.io/py/sokol)
[![CI](https://github.com/ahmadaliadeel/sokol-py/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmadaliadeel/sokol-py/actions/workflows/ci.yml)
[![Build Sokol](https://github.com/ahmadaliadeel/sokol-py/actions/workflows/build-sokol.yml/badge.svg)](https://github.com/ahmadaliadeel/sokol-py/actions/workflows/build-sokol.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically generated Python ctypes bindings for the [Sokol](https://github.com/floooh/sokol) cross-platform graphics library using libclang.

## Installation

```bash
pip install sokol
```

Or with uv:

```bash
uv add sokol
```

## Features

- **Cross-platform support**: Windows (D3D11), macOS (Metal), Linux (OpenGL)
- **Automatic platform detection**: Just call `load_sokol()` and it works
- **Pre-built shared libraries**: Included for all supported platforms
- **Automatic binding generation** from Sokol C headers using libclang
- **Complete type coverage**: enums, structs, function pointers, and API functions
- **Zero manual binding code** - everything is parsed from headers

## Supported Platforms

| Platform | Architecture | Backend | Library |
|----------|-------------|---------|----------|
| Windows | x64 | D3D11 | `sokol-windows-x64.dll` |
| macOS | x64 | Metal | `libsokol-macos-x64.dylib` |
| macOS | ARM64 | Metal | `libsokol-macos-arm64.dylib` |
| Linux | x64 | OpenGL | `libsokol-linux-x64.so` |

## Generated Statistics

| Type | Count |
|------|-------|
| Enums | 42 |
| Structs | 199 |
| Function Pointer Types | 80 |
| API Functions | 207 |

## Requirements

- Python 3.10+
- Pre-built shared libraries are included in the package

### For Development/Binding Generation

- libclang (`pip install libclang`)

## Quick Start

### 1. Install Dependencies

```bash
uv pip install libclang
```

### 2. Generate Bindings

```bash
python setup_and_generate.py
```

This will:
- Download Sokol headers from GitHub to `./sokol/`
- Parse headers with libclang
- Generate `sokol_bindings.py` (~6000 lines)

### 3. Run the Demo

```bash
python main.py
```

## Project Structure

```
├── generate_bindings.py    # Binding generator using libclang
├── setup_and_generate.py   # Downloads headers & runs generator
├── sokol_bindings.py       # Auto-generated ctypes bindings
├── main.py                 # Triangle demo application
├── sokol-dll.dll           # Pre-built Sokol DLL (you provide)
├── sokol/                  # Downloaded Sokol headers
│   ├── sokol_app.h
│   ├── sokol_gfx.h
│   ├── sokol_glue.h
│   └── sokol_log.h
└── README.md
```

## Usage

### Basic Usage

```python
from sokol.sokol_ahmedaliadeel import *

# Auto-detect platform and load the appropriate library
lib = load_sokol()

# Now use Sokol API
# lib.sg_setup(), lib.sapp_run(), etc.
```

### Explicit Library Path

```python
from sokol.sokol_ahmedaliadeel import load_sokol

# Load a specific library file
lib = load_sokol('/path/to/libsokol.so')
```

### Creating Structs

```python
# All Sokol structs are available as ctypes Structures
desc = sg_desc()
ctypes.memset(ctypes.addressof(desc), 0, ctypes.sizeof(desc))

# Set fields
desc.environment = lib.sglue_environment()
```

### Callbacks

```python
# Use generated function pointer types for callbacks
init_callback = _FuncPtr_init_cb_66(my_init_function)
frame_callback = _FuncPtr_frame_cb_67(my_frame_function)

desc = sapp_desc()
desc.init_cb = init_callback
desc.frame_cb = frame_callback
```

### Vertex Buffers

```python
# Create vertex data
vertices = (ctypes.c_float * 24)(
    # x, y, z, w,    r, g, b, a
    0.0,  0.5, 0.5, 1.0,  1.0, 0.0, 0.0, 1.0,  # top
    0.5, -0.5, 0.5, 1.0,  0.0, 1.0, 0.0, 1.0,  # right
   -0.5, -0.5, 0.5, 1.0,  0.0, 0.0, 1.0, 1.0,  # left
)

# Create buffer
buf_desc = sg_buffer_desc()
buf_desc.data.ptr = ctypes.cast(vertices, ctypes.c_void_p)
buf_desc.data.size = ctypes.sizeof(vertices)
vbuf = lib.sg_make_buffer(ctypes.byref(buf_desc))
```

## Generator Details

The `generate_bindings.py` script:

1. **Parses headers** with libclang in combined mode (all headers together for proper dependency resolution)
2. **Extracts types**:
   - Enums → Python constants
   - Structs → `ctypes.Structure` subclasses
   - Function pointers → `ctypes.CFUNCTYPE` types
   - Functions → DLL function bindings with argtypes/restype
3. **Handles edge cases**:
   - Anonymous structs (filtered out)
   - Nested struct arrays
   - Function pointer fields in structs
   - Proper type ordering for forward declarations

### Command Line Usage

```bash
# Generate with custom paths
python generate_bindings.py --sokol-dir ./sokol --output sokol_bindings.py

# Specify libclang path (if not auto-detected)
python generate_bindings.py --libclang /path/to/libclang.dll
```

## Sokol Headers

The generator supports these Sokol headers:

| Header | Description |
|--------|-------------|
| `sokol_log.h` | Logging utilities |
| `sokol_gfx.h` | 3D graphics API abstraction |
| `sokol_app.h` | Application/window handling |
| `sokol_glue.h` | Glue between sokol_app and sokol_gfx |

## Building sokol-dll.dll

If you need to build the DLL yourself:

```c
// sokol_dll.c
#define SOKOL_DLL
#define SOKOL_D3D11
#define SOKOL_NO_ENTRY
#define SOKOL_IMPL
#include "sokol_log.h"
#include "sokol_gfx.h"
#include "sokol_app.h"
#include "sokol_glue.h"
```

Compile with MSVC:
```bash
cl /LD /O2 /DSOKOL_DLL sokol_dll.c /Fe:sokol-dll.dll
```

## License

This binding generator is provided as-is. Sokol itself is licensed under the zlib license - see [sokol](https://github.com/floooh/sokol) for details.

## Links

- [Sokol](https://github.com/floooh/sokol) - Minimal cross-platform standalone C headers
- [Sokol Samples](https://github.com/floooh/sokol-samples) - Sample code and examples
- [libclang Python](https://pypi.org/project/libclang/) - Python bindings for libclang
