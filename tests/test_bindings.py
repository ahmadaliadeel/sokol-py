"""Basic tests for sokol package."""

import pytest
import sys


def test_import():
    """Test that the package can be imported."""
    import sokol
    assert sokol is not None
    
    # Also test submodule access
    from sokol import sokol_ahmedaliadeel
    assert sokol_ahmedaliadeel is not None


def test_ctypes_available():
    """Test that ctypes structures are defined."""
    from sokol import sg_desc, sapp_desc
    
    # Check that structs can be instantiated
    desc = sg_desc()
    assert desc is not None
    
    app_desc = sapp_desc()
    assert app_desc is not None


def test_constants():
    """Test that constants are defined."""
    from sokol import (
        SG_BACKEND_D3D11,
        SG_BACKEND_GLCORE,
        SG_BACKEND_METAL_MACOS,
        SG_BACKEND_VULKAN,
        SG_PIXELFORMAT_RGBA8,
    )
    
    assert SG_BACKEND_D3D11 == 2
    assert SG_BACKEND_GLCORE == 0
    assert SG_PIXELFORMAT_RGBA8 == 23


def test_load_sokol_functions_exist():
    """Test that load_sokol and load_sokol_dll functions exist."""
    from sokol import load_sokol, load_sokol_dll
    
    assert callable(load_sokol)
    assert callable(load_sokol_dll)


def test_get_lib_path():
    """Test that _get_lib_path returns correct platform-specific path."""
    from sokol import _get_lib_path
    from pathlib import Path
    
    # This may raise RuntimeError if libs aren't present, which is expected
    try:
        lib_path = _get_lib_path()
        assert isinstance(lib_path, Path)
        
        # Check platform-specific naming
        if sys.platform == "win32":
            assert lib_path.suffix == ".dll"
        elif sys.platform == "darwin":
            assert lib_path.suffix == ".dylib"
        elif sys.platform.startswith("linux"):
            assert lib_path.suffix == ".so"
    except RuntimeError as e:
        # Expected if libraries are not installed
        assert "not found" in str(e).lower()
