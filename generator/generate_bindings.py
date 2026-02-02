"""
Sokol Ctypes Binding Generator

This script uses libclang to parse Sokol C headers and automatically generates
Python ctypes bindings.

Requirements:
    pip install libclang

Usage:
    python generate_bindings.py --sokol-dir ./sokol --output sokol_bindings.py

The generator will:
1. Parse sokol_app.h, sokol_gfx.h, sokol_glue.h, sokol_log.h
2. Extract all enums, structs, typedefs, and function declarations
3. Generate Python ctypes bindings
"""

import argparse
import re
import sys
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List, Optional, Set, Tuple, Any

try:
    from clang.cindex import (
        Index, CursorKind, TypeKind, TranslationUnit,
        Cursor, Type, Config
    )
except ImportError:
    print("ERROR: libclang not installed.")
    print("Install with: pip install libclang")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

# Headers to parse in order (order matters for dependencies)
SOKOL_HEADERS = [
    "sokol_log.h",
    "sokol_gfx.h",
    "sokol_app.h",
    "sokol_glue.h",
]

# Type mappings from C to ctypes
C_TO_CTYPES = {
    # Basic types
    "void": "None",
    "bool": "c_bool",
    "_Bool": "c_bool",
    "char": "c_char",
    "signed char": "c_byte",
    "unsigned char": "c_ubyte",
    "short": "c_short",
    "unsigned short": "c_ushort",
    "int": "c_int",
    "unsigned int": "c_uint",
    "long": "c_long",
    "unsigned long": "c_ulong",
    "long long": "c_longlong",
    "unsigned long long": "c_ulonglong",
    "float": "c_float",
    "double": "c_double",
    "size_t": "c_size_t",
    "ssize_t": "c_ssize_t",
    "int8_t": "c_int8",
    "uint8_t": "c_uint8",
    "int16_t": "c_int16",
    "uint16_t": "c_uint16",
    "int32_t": "c_int32",
    "uint32_t": "c_uint32",
    "int64_t": "c_int64",
    "uint64_t": "c_uint64",
    "uintptr_t": "c_size_t",
    "intptr_t": "c_ssize_t",
    "ptrdiff_t": "c_ssize_t",
    "wchar_t": "c_wchar",
}

# Known pointer types that should be void*
OPAQUE_POINTER_TYPES = {
    "const void *", "void *",
    "const void*", "void*",
}


# =============================================================================
# AST Visitor
# =============================================================================

class SokolParser:
    """Parse Sokol headers and extract type/function information."""
    
    def __init__(self, sokol_dir: Path):
        self.sokol_dir = sokol_dir
        self.index = Index.create()
        
        # Collected items
        self.enums: Dict[str, List[Tuple[str, int]]] = OrderedDict()
        self.structs: Dict[str, List[Tuple[str, str, Optional[int]]]] = OrderedDict()
        self.typedefs: Dict[str, str] = OrderedDict()
        self.functions: Dict[str, Tuple[str, List[Tuple[str, str]]]] = OrderedDict()
        self.func_typedefs: Dict[str, Tuple[str, List[str]]] = OrderedDict()
        
        # Track what we've seen
        self.seen_types: Set[str] = set()
        self.forward_decls: Set[str] = set()
        
    def parse_headers(self) -> bool:
        """Parse all Sokol headers using a combined approach."""
        # Create a combined source file that includes all headers in the right order
        combined_source = """
#define SOKOL_DLL
#define SOKOL_D3D11
#define SOKOL_NO_ENTRY
#define SOKOL_IMPL

#include "sokol_log.h"
#include "sokol_gfx.h"
#include "sokol_app.h"
#include "sokol_glue.h"
"""
        
        # Write temporary combined header
        combined_path = self.sokol_dir / "_combined_sokol.c"
        combined_path.write_text(combined_source)
        
        print("Parsing all headers together...")
        
        # Parse with clang
        args = [
            '-x', 'c',
            '-std=c11',
            f'-I{self.sokol_dir}',
            '-DSOKOL_DLL',
            '-DSOKOL_D3D11', 
            '-DSOKOL_NO_ENTRY',
            '-D_WIN32',
            '-D_MSC_VER=1920',
        ]
        
        try:
            tu = self.index.parse(
                str(combined_path),
                args=args,
                options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
            )
        except Exception as e:
            print(f"Error parsing headers: {e}")
            combined_path.unlink(missing_ok=True)
            return False
        
        # Check for errors
        for diag in tu.diagnostics:
            if diag.severity >= 3:  # Error or Fatal
                print(f"  Clang error: {diag.spelling}")
        
        # Visit the AST
        self._visit_cursor(tu.cursor, str(combined_path))
        
        # Clean up
        combined_path.unlink(missing_ok=True)
        
        return True
    
    def _visit_cursor(self, cursor: Cursor, source_file: str):
        """Visit a cursor and its children."""
        # Only process items from sokol headers
        if cursor.location.file:
            file_name = cursor.location.file.name
            if not any(h in file_name for h in ['sokol_', 'sokol/']):
                # Still visit children for includes
                for child in cursor.get_children():
                    self._visit_cursor(child, source_file)
                return
        
        kind = cursor.kind
        
        if kind == CursorKind.ENUM_DECL:
            self._process_enum(cursor)
        elif kind == CursorKind.STRUCT_DECL:
            self._process_struct(cursor)
        elif kind == CursorKind.TYPEDEF_DECL:
            self._process_typedef(cursor)
        elif kind == CursorKind.FUNCTION_DECL:
            self._process_function(cursor)
        
        # Visit children
        for child in cursor.get_children():
            self._visit_cursor(child, source_file)
    
    def _process_enum(self, cursor: Cursor):
        """Process an enum declaration."""
        name = cursor.spelling
        if not name:
            # Anonymous enum, might be part of typedef
            return
        
        if name in self.enums:
            return  # Already processed
        
        values = []
        for child in cursor.get_children():
            if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                values.append((child.spelling, child.enum_value))
        
        if values:
            self.enums[name] = values
    
    def _process_struct(self, cursor: Cursor):
        """Process a struct declaration."""
        name = cursor.spelling
        if not name:
            return
        
        # Skip anonymous/unnamed structs or invalid names
        if 'unnamed' in name or '(' in name or ' ' in name:
            return
        
        # Check if this is a definition or just a declaration
        if not cursor.is_definition():
            self.forward_decls.add(name)
            return
        
        if name in self.structs:
            return  # Already processed
        
        fields = []
        for child in cursor.get_children():
            if child.kind == CursorKind.FIELD_DECL:
                field_name = child.spelling
                field_type = self._get_type_string(child.type)
                
                # Check for function pointers
                is_func_ptr = False
                if child.type.kind == TypeKind.POINTER:
                    pointee = child.type.get_pointee()
                    if pointee.kind == TypeKind.FUNCTIONPROTO:
                        is_func_ptr = True
                        # Extract and store the function signature
                        ret_type = self._get_type_string(pointee.get_result())
                        arg_types = [self._get_type_string(arg) for arg in pointee.argument_types()]
                        # Create a unique name for this func ptr type
                        #func_ptr_name = f"_FuncPtr_{field_name}_{len(self.func_typedefs)}"
                        func_ptr_name = f"_FuncPtr_{field_name}"
                        self.func_typedefs[func_ptr_name] = (ret_type, arg_types)
                        field_type = func_ptr_name
                
                # Check for arrays
                array_size = None
                if child.type.kind == TypeKind.CONSTANTARRAY:
                    array_size = child.type.get_array_size()
                    # Get element type
                    elem_type = child.type.get_array_element_type()
                    field_type = self._get_type_string(elem_type)
                
                fields.append((field_name, field_type, array_size))
        
        if fields:
            self.structs[name] = fields
    
    def _process_typedef(self, cursor: Cursor):
        """Process a typedef declaration."""
        name = cursor.spelling
        if not name:
            return
        
        if name in self.typedefs or name in self.structs or name in self.enums:
            return
        
        underlying = cursor.underlying_typedef_type
        
        # Check if this is a function pointer typedef
        if underlying.kind == TypeKind.POINTER:
            pointee = underlying.get_pointee()
            if pointee.kind == TypeKind.FUNCTIONPROTO:
                self._process_func_typedef(name, pointee)
                return
        
        # Check if it's a typedef to a struct with same name
        type_str = underlying.spelling
        if type_str.startswith("struct "):
            struct_name = type_str[7:]
            if struct_name == name:
                return  # Skip self-referential typedefs
        
        # Check for anonymous enum in typedef
        for child in cursor.get_children():
            if child.kind == CursorKind.ENUM_DECL:
                # Anonymous enum, store values under typedef name
                values = []
                for enum_child in child.get_children():
                    if enum_child.kind == CursorKind.ENUM_CONSTANT_DECL:
                        values.append((enum_child.spelling, enum_child.enum_value))
                if values:
                    self.enums[name] = values
                return
            elif child.kind == CursorKind.STRUCT_DECL:
                # Anonymous struct, store under typedef name
                if not child.spelling:  # Truly anonymous
                    fields = []
                    for field in child.get_children():
                        if field.kind == CursorKind.FIELD_DECL:
                            field_name = field.spelling
                            field_type = self._get_type_string(field.type)
                            array_size = None
                            if field.type.kind == TypeKind.CONSTANTARRAY:
                                array_size = field.type.get_array_size()
                                elem_type = field.type.get_array_element_type()
                                field_type = self._get_type_string(elem_type)
                            fields.append((field_name, field_type, array_size))
                    if fields:
                        self.structs[name] = fields
                return
        
        self.typedefs[name] = self._get_type_string(underlying)
    
    def _process_func_typedef(self, name: str, func_type: Type):
        """Process a function pointer typedef."""
        ret_type = self._get_type_string(func_type.get_result())
        arg_types = []
        
        for arg in func_type.argument_types():
            arg_types.append(self._get_type_string(arg))
        
        self.func_typedefs[name] = (ret_type, arg_types)
    
    def _process_function(self, cursor: Cursor):
        """Process a function declaration."""
        name = cursor.spelling
        if not name:
            return
        
        # Only process sokol API functions
        if not (name.startswith('sg_') or name.startswith('sapp_') or 
                name.startswith('sglue_') or name.startswith('slog_')):
            return
        
        if name in self.functions:
            return
        
        ret_type = self._get_type_string(cursor.result_type)
        args = []
        
        for arg in cursor.get_arguments():
            arg_name = arg.spelling or f"arg{len(args)}"
            arg_type = self._get_type_string(arg.type)
            args.append((arg_name, arg_type))
        
        self.functions[name] = (ret_type, args)
    
    def _get_type_string(self, t: Type) -> str:
        """Convert a clang Type to a string representation."""
        kind = t.kind
        
        if kind == TypeKind.VOID:
            return "void"
        elif kind == TypeKind.BOOL:
            return "bool"
        elif kind == TypeKind.CHAR_S or kind == TypeKind.SCHAR:
            return "char"
        elif kind == TypeKind.CHAR_U or kind == TypeKind.UCHAR:
            return "unsigned char"
        elif kind == TypeKind.SHORT:
            return "short"
        elif kind == TypeKind.USHORT:
            return "unsigned short"
        elif kind == TypeKind.INT:
            return "int"
        elif kind == TypeKind.UINT:
            return "unsigned int"
        elif kind == TypeKind.LONG:
            return "long"
        elif kind == TypeKind.ULONG:
            return "unsigned long"
        elif kind == TypeKind.LONGLONG:
            return "long long"
        elif kind == TypeKind.ULONGLONG:
            return "unsigned long long"
        elif kind == TypeKind.FLOAT:
            return "float"
        elif kind == TypeKind.DOUBLE:
            return "double"
        elif kind == TypeKind.POINTER:
            pointee = t.get_pointee()
            if pointee.kind == TypeKind.VOID:
                if t.is_const_qualified() or "const" in t.spelling:
                    return "const void *"
                return "void *"
            elif pointee.kind == TypeKind.CHAR_S:
                return "const char *"
            elif pointee.kind == TypeKind.FUNCTIONPROTO:
                return t.spelling  # Function pointer
            else:
                return f"{self._get_type_string(pointee)} *"
        elif kind == TypeKind.CONSTANTARRAY:
            elem = t.get_array_element_type()
            size = t.get_array_size()
            return f"{self._get_type_string(elem)}[{size}]"
        elif kind == TypeKind.TYPEDEF:
            return t.spelling
        elif kind == TypeKind.ELABORATED:
            type_str = t.spelling.replace("struct ", "").replace("enum ", "")
            # Handle unnamed types - return generic int for unnamed structs
            if 'unnamed' in type_str or '(' in type_str:
                return "int"  # Placeholder for unnamed struct, often a bitfield union
            return type_str
        elif kind == TypeKind.RECORD:
            type_str = t.spelling.replace("struct ", "")
            if 'unnamed' in type_str or '(' in type_str:
                return "int"
            return type_str
        elif kind == TypeKind.ENUM:
            type_str = t.spelling.replace("enum ", "")
            if 'unnamed' in type_str or '(' in type_str:
                return "int"
            return type_str
        else:
            # Fallback
            spelling = t.spelling
            if spelling:
                clean = spelling.replace("struct ", "").replace("enum ", "")
                if 'unnamed' in clean or '(' in clean:
                    return "int"
                return clean
            return "int"  # Default fallback


# =============================================================================
# Code Generator
# =============================================================================

class BindingGenerator:
    """Generate Python ctypes bindings from parsed data."""
    
    def __init__(self, parser: SokolParser):
        self.parser = parser
        self.output_lines: List[str] = []
        self.generated_types: Set[str] = set()
        
    def generate(self) -> str:
        """Generate the complete bindings module."""
        self._write_header()
        self._write_imports()
        self._write_type_helpers()
        self._write_enums()
        self._write_forward_declarations()
        self._write_func_typedefs()  # Before structs since structs may use func ptr types
        self._write_structs()
        self._write_library_loader()
        self._write_function_bindings()
        self._write_footer()
        
        return "\n".join(self.output_lines)
    
    def _write(self, line: str = ""):
        """Write a line to output."""
        self.output_lines.append(line)
    
    def _write_header(self):
        """Write module header."""
        self._write('"""')
        self._write("Sokol Python Bindings (Auto-generated)")
        self._write("")
        self._write("This module was automatically generated by generate_bindings.py")
        self._write("from the Sokol C headers using libclang.")
        self._write("")
        self._write("Usage:")
        self._write("    from sokol_bindings import *")
        self._write("    sokol = load_sokol_dll('sokol-dll.dll')")
        self._write('"""')
        self._write("")
    
    def _write_imports(self):
        """Write import statements."""
        self._write("import ctypes")
        self._write("from ctypes import (")
        self._write("    Structure, Union, POINTER, CFUNCTYPE,")
        self._write("    c_bool, c_char, c_byte, c_ubyte, c_short, c_ushort,")
        self._write("    c_int, c_uint, c_long, c_ulong, c_longlong, c_ulonglong,")
        self._write("    c_float, c_double, c_size_t, c_ssize_t, c_void_p, c_char_p,")
        self._write("    c_int8, c_uint8, c_int16, c_uint16, c_int32, c_uint32,")
        self._write("    c_int64, c_uint64, c_wchar, c_wchar_p,")
        self._write("    byref, cast, sizeof, addressof,")
        self._write(")")
        self._write("from pathlib import Path")
        self._write("from typing import Optional, Any")
        self._write("")
        self._write("# Platform detection")
        self._write("import sys")
        self._write("if sys.platform == 'win32':")
        self._write("    from ctypes import windll, WinDLL")
        self._write("")
    
    def _write_type_helpers(self):
        """Write helper type definitions."""
        self._write("# =============================================================================")
        self._write("# Type Helpers")
        self._write("# =============================================================================")
        self._write("")
        self._write("# C type aliases")
        self._write("c_bool_p = POINTER(c_bool)")
        self._write("c_float_p = POINTER(c_float)")
        self._write("c_double_p = POINTER(c_double)")
        self._write("c_int_p = POINTER(c_int)")
        self._write("c_uint_p = POINTER(c_uint)")
        self._write("c_uint8_p = POINTER(c_uint8)")
        self._write("c_uint32_p = POINTER(c_uint32)")
        self._write("")
    
    def _write_enums(self):
        """Write enum definitions."""
        if not self.parser.enums:
            return
        
        self._write("# =============================================================================")
        self._write("# Enums")
        self._write("# =============================================================================")
        self._write("")
        
        for enum_name, values in self.parser.enums.items():
            self._write(f"# {enum_name}")
            for name, value in values:
                self._write(f"{name} = {value}")
            self._write("")
    
    def _write_forward_declarations(self):
        """Write forward declarations for structs."""
        if not self.parser.structs:
            return
        
        self._write("# =============================================================================")
        self._write("# Forward Declarations")
        self._write("# =============================================================================")
        self._write("")
        
        for struct_name in self.parser.structs.keys():
            self._write(f"class {struct_name}(Structure): pass")
            self.generated_types.add(struct_name)
        
        self._write("")
    
    def _write_structs(self):
        """Write struct definitions."""
        if not self.parser.structs:
            return
        
        self._write("# =============================================================================")
        self._write("# Structures")
        self._write("# =============================================================================")
        self._write("")
        
        for struct_name, fields in self.parser.structs.items():
            self._write(f"# {struct_name}")
            self._write(f"{struct_name}._fields_ = [")
            
            for field_name, field_type, array_size in fields:
                ctype = self._convert_type(field_type)
                if array_size:
                    self._write(f'    ("{field_name}", {ctype} * {array_size}),')
                else:
                    self._write(f'    ("{field_name}", {ctype}),')
            
            self._write("]")
            self._write("")
    
    def _write_func_typedefs(self):
        """Write function pointer typedefs."""
        if not self.parser.func_typedefs:
            return
        
        self._write("# =============================================================================")
        self._write("# Function Pointer Types")
        self._write("# =============================================================================")
        self._write("")
        
        for name, (ret_type, arg_types) in self.parser.func_typedefs.items():
            ret_ctype = self._convert_type(ret_type)
            arg_ctypes = [self._convert_type(t) for t in arg_types]
            
            if arg_ctypes:
                args_str = ", ".join(arg_ctypes)
                self._write(f"{name} = CFUNCTYPE({ret_ctype}, {args_str})")
            else:
                self._write(f"{name} = CFUNCTYPE({ret_ctype})")
        
        self._write("")
    
    def _write_library_loader(self):
        """Write library loading function."""
        self._write("# =============================================================================")
        self._write("# Library Loader")
        self._write("# =============================================================================")
        self._write("")
        self._write("_sokol_lib = None")
        self._write("")
        self._write("def load_sokol_dll(dll_path: str = 'sokol-dll.dll') -> Any:")
        self._write('    """')
        self._write("    Load the Sokol DLL and set up function prototypes.")
        self._write("    ")
        self._write("    Args:")
        self._write("        dll_path: Path to the Sokol DLL file")
        self._write("    ")
        self._write("    Returns:")
        self._write("        The loaded library object with all functions bound")
        self._write('    """')
        self._write("    global _sokol_lib")
        self._write("    ")
        self._write("    path = Path(dll_path)")
        self._write("    if not path.exists():")
        self._write("        # Try common locations")
        self._write("        for try_path in [Path('.') / dll_path, Path(__file__).parent / dll_path]:")
        self._write("            if try_path.exists():")
        self._write("                path = try_path")
        self._write("                break")
        self._write("    ")
        self._write("    if sys.platform == 'win32':")
        self._write("        lib = ctypes.CDLL(str(path))")
        self._write("    else:")
        self._write("        lib = ctypes.CDLL(str(path))")
        self._write("    ")
        self._write("    _setup_function_prototypes(lib)")
        self._write("    _sokol_lib = lib")
        self._write("    return lib")
        self._write("")
    
    def _write_function_bindings(self):
        """Write function prototype setup."""
        self._write("def _setup_function_prototypes(lib):")
        self._write('    """Set up ctypes function prototypes."""')
        self._write("    ")
        
        for func_name, (ret_type, args) in self.parser.functions.items():
            ret_ctype = self._convert_type(ret_type)
            arg_ctypes = []
            
            for arg_name, arg_type in args:
                arg_ctypes.append(self._convert_type(arg_type))
            
            # Check if function exists
            self._write(f"    # {func_name}")
            self._write(f"    if hasattr(lib, '{func_name}'):")
            self._write(f"        lib.{func_name}.restype = {ret_ctype}")
            
            if arg_ctypes:
                args_str = ", ".join(arg_ctypes)
                self._write(f"        lib.{func_name}.argtypes = [{args_str}]")
            else:
                self._write(f"        lib.{func_name}.argtypes = []")
            
            self._write("    ")
        
        self._write("")
    
    def _write_footer(self):
        """Write module footer with helper functions."""
        self._write("# =============================================================================")
        self._write("# Helper Functions")
        self._write("# =============================================================================")
        self._write("")
        self._write("def get_lib():")
        self._write('    """Get the loaded Sokol library."""')
        self._write("    if _sokol_lib is None:")
        self._write("        raise RuntimeError('Sokol library not loaded. Call load_sokol_dll() first.')")
        self._write("    return _sokol_lib")
        self._write("")
        self._write("")
        self._write("def make_range(data: bytes) -> sg_range:")
        self._write('    """Create an sg_range from bytes data."""')
        self._write("    r = sg_range()")
        self._write("    r.ptr = ctypes.cast(data, c_void_p)")
        self._write("    r.size = len(data)")
        self._write("    return r")
        self._write("")
        self._write("")
        self._write("def make_buffer_from_array(arr, ctype=c_float):")
        self._write('    """Create a ctypes array from a Python list."""')
        self._write("    return (ctype * len(arr))(*arr)")
        self._write("")
        self._write("")
        self._write("# Export all public names")
        self._write("__all__ = [")
        
        # Export enums
        for enum_name, values in self.parser.enums.items():
            for name, _ in values:
                self._write(f"    '{name}',")
        
        # Export structs
        for struct_name in self.parser.structs.keys():
            self._write(f"    '{struct_name}',")
        
        # Export function typedefs
        for name in self.parser.func_typedefs.keys():
            self._write(f"    '{name}',")
        
        self._write("    'load_sokol_dll',")
        self._write("    'get_lib',")
        self._write("    'make_range',")
        self._write("    'make_buffer_from_array',")
        self._write("]")
    
    def _convert_type(self, c_type: str) -> str:
        """Convert a C type string to ctypes."""
        c_type = c_type.strip()
        
        # Handle const
        c_type_clean = c_type.replace("const ", "").strip()
        
        # Check for function pointer patterns like "void (*)(void)" or "void (*)(const sapp_event *)"
        func_ptr_match = re.match(r'(.+?)\s*\(\s*\*\s*\)\s*\((.*)\)', c_type_clean)
        if func_ptr_match:
            # It's a function pointer - use c_void_p as a generic function pointer
            # The actual callback should be created with CFUNCTYPE at runtime
            return "c_void_p"
        
        # Check basic types first
        if c_type_clean in C_TO_CTYPES:
            return C_TO_CTYPES[c_type_clean]
        
        # Handle pointers
        if c_type.endswith("*"):
            base_type = c_type[:-1].strip().replace("const ", "")
            
            # Special cases
            if "void" in base_type:
                return "c_void_p"
            if "char" in base_type:
                return "c_char_p"
            
            # Pointer to known struct
            if base_type in self.parser.structs or base_type in self.generated_types:
                return f"POINTER({base_type})"
            
            # Pointer to basic type
            if base_type in C_TO_CTYPES:
                return f"POINTER({C_TO_CTYPES[base_type]})"
            
            # Unknown pointer type, treat as void*
            return "c_void_p"
        
        # Check if it's a known struct
        if c_type_clean in self.parser.structs or c_type_clean in self.generated_types:
            return c_type_clean
        
        # Check if it's a known enum (treat as c_int)
        if c_type_clean in self.parser.enums:
            return "c_int"
        
        # Check if it's a known typedef
        if c_type_clean in self.parser.typedefs:
            return self._convert_type(self.parser.typedefs[c_type_clean])
        
        # Check for function pointer typedef
        if c_type_clean in self.parser.func_typedefs:
            return c_type_clean
        
        # Handle arrays in type string
        match = re.match(r'(.+)\[(\d+)\]', c_type_clean)
        if match:
            elem_type = match.group(1).strip()
            size = int(match.group(2))
            return f"{self._convert_type(elem_type)} * {size}"
        
        # Default fallback
        return "c_int"


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate Python ctypes bindings for Sokol headers"
    )
    parser.add_argument(
        "--sokol-dir", "-s",
        type=Path,
        default=Path("sokol"),
        help="Path to directory containing Sokol headers"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("sokol_bindings.py"),
        help="Output Python file"
    )
    parser.add_argument(
        "--libclang", "-l",
        type=str,
        default=None,
        help="Path to libclang library (optional)"
    )
    
    args = parser.parse_args()
    
    # Configure libclang path if specified
    if args.libclang:
        Config.set_library_file(args.libclang)
    
    # Check sokol directory
    if not args.sokol_dir.exists():
        print(f"Error: Sokol directory not found: {args.sokol_dir}")
        print("Please specify the path with --sokol-dir")
        return 1
    
    # Check for headers
    found_headers = False
    for header in SOKOL_HEADERS:
        if (args.sokol_dir / header).exists():
            found_headers = True
            break
    
    if not found_headers:
        print(f"Error: No Sokol headers found in {args.sokol_dir}")
        print("Expected files: " + ", ".join(SOKOL_HEADERS))
        return 1
    
    print("=" * 60)
    print("Sokol Ctypes Binding Generator")
    print("=" * 60)
    print(f"Sokol directory: {args.sokol_dir}")
    print(f"Output file: {args.output}")
    print()
    
    # Parse headers
    sokol_parser = SokolParser(args.sokol_dir)
    if not sokol_parser.parse_headers():
        print("Failed to parse headers")
        return 1
    
    # Print statistics
    print()
    print("Parsed:")
    print(f"  - {len(sokol_parser.enums)} enums")
    print(f"  - {len(sokol_parser.structs)} structs")
    print(f"  - {len(sokol_parser.typedefs)} typedefs")
    print(f"  - {len(sokol_parser.func_typedefs)} function pointer types")
    print(f"  - {len(sokol_parser.functions)} functions")
    print()
    
    # Generate bindings
    generator = BindingGenerator(sokol_parser)
    output = generator.generate()
    
    # Write output
    args.output.write_text(output)
    print(f"Generated: {args.output}")
    print()
    print("Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
