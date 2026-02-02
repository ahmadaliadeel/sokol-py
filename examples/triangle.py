"""
Sokol Triangle Example using Generated Ctypes Bindings

This example demonstrates drawing a triangle using the Sokol library via
automatically generated Python ctypes bindings.

Requirements:
1. Have sokol-dll.dll in the current directory
2. Run setup_and_generate.py first to generate sokol_bindings.py
3. Install libclang: pip install libclang

Usage:
    python setup_and_generate.py   # Generate bindings first
    python main.py                 # Run the triangle demo
"""

import os
import sys
import ctypes
from pathlib import Path

# Check if bindings exist
# if not Path("sokol.py").exists():
#     print("ERROR: sokol.py not found!")
#     print("Run 'python setup_and_generate.py' first to generate bindings.")
#     sys.exit(1)

# Import generated bindings
from sokol import *


# =============================================================================
# Shaders (HLSL for D3D11)
# =============================================================================

VS_SOURCE_HLSL = """
struct vs_in {
    float4 pos: POSITION;
    float4 color: COLOR0;
};
struct vs_out {
    float4 color: COLOR0;
    float4 pos: SV_Position;
};
vs_out main(vs_in inp) {
    vs_out outp;
    outp.pos = inp.pos;
    outp.color = inp.color;
    return outp;
}
"""

FS_SOURCE_HLSL = """
float4 main(float4 color: COLOR0): SV_Target0 {
    return color;
}
"""

# OpenGL shaders as fallback
VS_SOURCE_GLSL = """#version 330
layout(location=0) in vec4 position;
layout(location=1) in vec4 color0;
out vec4 color;
void main() {
    gl_Position = position;
    color = color0;
}
"""

FS_SOURCE_GLSL = """#version 330
in vec4 color;
out vec4 frag_color;
void main() {
    frag_color = color;
}
"""


# =============================================================================
# Application State
# =============================================================================

class TriangleApp:
    """Triangle rendering application using Sokol."""
    
    def __init__(self):
        self.lib = None
        self.pip = None
        self.bind = None
        self.pass_action = None
        
    def init(self):
        """Initialize callback - called by sapp after window creation."""
        lib = self.lib
        
        # Initialize sokol_gfx
        desc = sg_desc()
        ctypes.memset(ctypes.addressof(desc), 0, ctypes.sizeof(desc))
        
        # Get environment from sokol_glue
        if hasattr(lib, 'sglue_environment'):
            desc.environment = lib.sglue_environment()
        
        # Skip logger setup - use default
        
        lib.sg_setup(ctypes.byref(desc))
        
        # Vertex data: position (x,y,z,w) + color (r,g,b,a)
        vertices = (ctypes.c_float * 24)(
            # positions            colors
             0.0,  0.5, 0.5, 1.0,  1.0, 0.0, 0.0, 1.0,  # top - red
             0.5, -0.5, 0.5, 1.0,  0.0, 1.0, 0.0, 1.0,  # right - green
            -0.5, -0.5, 0.5, 1.0,  0.0, 0.0, 1.0, 1.0,  # left - blue
        )
        
        # Create vertex buffer
        buf_desc = sg_buffer_desc()
        ctypes.memset(ctypes.addressof(buf_desc), 0, ctypes.sizeof(buf_desc))
        buf_desc.data.ptr = ctypes.cast(vertices, ctypes.c_void_p)
        buf_desc.data.size = ctypes.sizeof(vertices)
        
        vbuf = lib.sg_make_buffer(ctypes.byref(buf_desc))
        
        # Create shader
        shd_desc = sg_shader_desc()
        ctypes.memset(ctypes.addressof(shd_desc), 0, ctypes.sizeof(shd_desc))
        
        # Set shader source based on backend
        # For D3D11, we use HLSL
        shd_desc.vertex_func.source = VS_SOURCE_HLSL.encode('utf-8')
        shd_desc.fragment_func.source = FS_SOURCE_HLSL.encode('utf-8')
        
        # Vertex attribute names for D3D11
        shd_desc.attrs[0].hlsl_sem_name = b"POSITION"
        shd_desc.attrs[1].hlsl_sem_name = b"COLOR"
        
        shd = lib.sg_make_shader(ctypes.byref(shd_desc))
        
        # Create pipeline
        pip_desc = sg_pipeline_desc()
        ctypes.memset(ctypes.addressof(pip_desc), 0, ctypes.sizeof(pip_desc))
        pip_desc.shader = shd
        
        # Vertex layout
        pip_desc.layout.attrs[0].format = SG_VERTEXFORMAT_FLOAT4  # position
        pip_desc.layout.attrs[1].format = SG_VERTEXFORMAT_FLOAT4  # color
        
        self.pip = lib.sg_make_pipeline(ctypes.byref(pip_desc))
        
        # Create bindings
        self.bind = sg_bindings()
        ctypes.memset(ctypes.addressof(self.bind), 0, ctypes.sizeof(self.bind))
        self.bind.vertex_buffers[0] = vbuf
        
        # Pass action (clear color)
        self.pass_action = sg_pass_action()
        ctypes.memset(ctypes.addressof(self.pass_action), 0, ctypes.sizeof(self.pass_action))
        
        # SG_LOADACTION_CLEAR = 1
        self.pass_action.colors[0].load_action = 1  # SG_LOADACTION_CLEAR
        self.pass_action.colors[0].clear_value.r = 0.2
        self.pass_action.colors[0].clear_value.g = 0.2
        self.pass_action.colors[0].clear_value.b = 0.3
        self.pass_action.colors[0].clear_value.a = 1.0
        
        print("Sokol initialized successfully!")
        
    def frame(self):
        """Frame callback - called every frame."""
        lib = self.lib
        
        # Get swapchain pass
        swapchain = lib.sglue_swapchain() if hasattr(lib, 'sglue_swapchain') else None
        
        # Begin pass
        pass_desc = sg_pass()
        ctypes.memset(ctypes.addressof(pass_desc), 0, ctypes.sizeof(pass_desc))
        pass_desc.action = self.pass_action
        
        if swapchain:
            pass_desc.swapchain = swapchain
        
        lib.sg_begin_pass(ctypes.byref(pass_desc))
        
        # Apply pipeline and bindings
        lib.sg_apply_pipeline(self.pip)
        lib.sg_apply_bindings(ctypes.byref(self.bind))
        
        # Draw triangle (3 vertices)
        lib.sg_draw(0, 3, 1)
        
        # End pass and commit
        lib.sg_end_pass()
        lib.sg_commit()
        
    def cleanup(self):
        """Cleanup callback - called on shutdown."""
        self.lib.sg_shutdown()
        print("Sokol shut down.")
        
    def event(self, event):
        """Event callback - handle input events."""
        pass  # No event handling needed for this simple example
        
    def run(self):
        """Run the application."""
        # Load the DLL
        dll_name = os.path.abspath("sokol-dll.dll")
        if not Path(dll_name).exists():
            print(f"ERROR: {dll_name} not found!")
            return 1
        
        try:
            self.lib = load_sokol_dll(dll_name)
            print(f"Loaded {dll_name}")
        except Exception as e:
            print(f"Failed to load DLL: {e}")
            return 1
        
        # Create callback wrappers
        # Use the CFUNCTYPE types generated from the bindings
        # Store references to prevent garbage collection
        self._init_cb = _FuncPtr_init_cb(self.init)
        self._frame_cb = _FuncPtr_frame_cb(self.frame)
        self._cleanup_cb = _FuncPtr_cleanup_cb(self.cleanup)
        self._event_cb = _FuncPtr_event_cb(self.event)
        
        # Create app description
        desc = sapp_desc()
        ctypes.memset(ctypes.addressof(desc), 0, ctypes.sizeof(desc))
        
        desc.init_cb = self._init_cb
        desc.frame_cb = self._frame_cb
        desc.cleanup_cb = self._cleanup_cb
        desc.event_cb = self._event_cb
        
        desc.width = 800
        desc.height = 600
        desc.window_title = b"Sokol Triangle (Python Ctypes)"
        
        # High DPI
        desc.high_dpi = True
        
        # Set up logger - slog_func is exported from DLL, we need to cast its address
        # For now, skip the logger setup as it requires special handling
        # The DLL will use default logging
        
        print("Starting Sokol application...")
        print("=" * 50)
        
        # Run the app (this blocks until window is closed)
        self.lib.sapp_run(ctypes.byref(desc))
        
        return 0


# =============================================================================
# Alternative: Manual Bindings (if generated bindings don't work)
# =============================================================================

def run_with_manual_bindings():
    """
    Run with manually defined minimal bindings.
    Use this if the generated bindings have issues.
    """
    import ctypes
    from ctypes import Structure, c_uint32, c_int, c_float, c_bool, c_void_p, c_char_p
    from ctypes import c_size_t, CFUNCTYPE, POINTER, byref, sizeof, addressof
    
    # Load DLL
    dll_path = "sokol-dll.dll"
    if not Path(dll_path).exists():
        print(f"ERROR: {dll_path} not found!")
        return 1
    
    lib = ctypes.CDLL(dll_path)
    
    # Minimal struct definitions
    class sg_buffer(Structure):
        _fields_ = [("id", c_uint32)]
    
    class sg_shader(Structure):
        _fields_ = [("id", c_uint32)]
    
    class sg_pipeline(Structure):
        _fields_ = [("id", c_uint32)]
    
    class sg_range(Structure):
        _fields_ = [("ptr", c_void_p), ("size", c_size_t)]
    
    class sg_color(Structure):
        _fields_ = [("r", c_float), ("g", c_float), ("b", c_float), ("a", c_float)]
    
    print("Manual bindings mode - minimal implementation")
    print("For full functionality, use the generated bindings.")
    
    return 0


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Sokol Triangle Example - Python Ctypes")
    print("=" * 60)
    print()
    
    # Check for DLL
    dll_path = Path("sokol-dll.dll")
    if not dll_path.exists():
        print(f"ERROR: {dll_path} not found!")
        print()
        print("Please ensure sokol-dll.dll is in the current directory.")
        return 1
    
    # Check for bindings
    bindings_path = Path("sokol_bindings.py")
    if not bindings_path.exists():
        print(f"ERROR: {bindings_path} not found!")
        print()
        print("Run the binding generator first:")
        print("  python setup_and_generate.py")
        return 1
    
    # Run the application
    app = TriangleApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
