"""Basic tests for sokol-ahmedaliadeel package."""

import pytest


def test_import():
    """Test that the package can be imported."""
    from sokol import sokol
    assert sokol is not None


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


def test_load_sokol_dll_function():
    """Test that load_sokol_dll function exists."""
    from sokol import load_sokol_dll
    
    assert callable(load_sokol_dll)
