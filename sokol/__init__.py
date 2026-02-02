"""
Sokol Python Bindings

Python ctypes bindings for the Sokol cross-platform graphics library.

Usage:
    from sokol import load_sokol
    lib = load_sokol()  # Auto-detects platform and loads library
    
    # Or import everything:
    from sokol import *
    lib = load_sokol()
"""

# Re-export everything from sokol_ahmedaliadeel
from sokol.sokol_ahmedaliadeel import *
from sokol.sokol_ahmedaliadeel import __all__ as _bindings_all

__version__ = "0.1.0"

# Extend __all__ with our module-level exports
__all__ = list(_bindings_all) + ["__version__", "sokol_ahmedaliadeel"]
