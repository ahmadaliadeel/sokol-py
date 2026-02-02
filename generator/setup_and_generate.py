"""
Setup script that downloads Sokol headers and generates Python bindings.

Usage:
    python setup_and_generate.py
"""

import os
import sys
import urllib.request
from pathlib import Path

# Sokol headers to download
SOKOL_HEADERS = {
    "sokol_app.h": "https://raw.githubusercontent.com/floooh/sokol/master/sokol_app.h",
    "sokol_gfx.h": "https://raw.githubusercontent.com/floooh/sokol/master/sokol_gfx.h",
    "sokol_glue.h": "https://raw.githubusercontent.com/floooh/sokol/master/sokol_glue.h",
    "sokol_log.h": "https://raw.githubusercontent.com/floooh/sokol/master/sokol_log.h",
}


def download_headers(output_dir: Path) -> bool:
    """Download Sokol headers from GitHub."""
    output_dir.mkdir(exist_ok=True)
    
    print("Downloading Sokol headers...")
    for name, url in SOKOL_HEADERS.items():
        output_path = output_dir / name
        if output_path.exists():
            print(f"  {name} already exists, skipping")
            continue
        
        print(f"  Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, output_path)
        except Exception as e:
            print(f"  Error downloading {name}: {e}")
            return False
    
    print("Headers downloaded successfully!")
    return True


def check_libclang() -> bool:
    """Check if libclang is available."""
    try:
        from clang.cindex import Index
        # Try to create an index to verify it works
        Index.create()
        return True
    except ImportError:
        print("ERROR: libclang Python bindings not installed.")
        print("Install with: pip install libclang")
        return False
    except Exception as e:
        print(f"ERROR: libclang found but failed to initialize: {e}")
        print("You may need to install LLVM/Clang on your system.")
        print("On Windows: Download from https://releases.llvm.org/")
        return False


def generate_bindings(sokol_dir: Path, output_file: Path) -> bool:
    """Run the binding generator."""
    from generate_bindings import SokolParser, BindingGenerator
    
    print()
    print("Parsing Sokol headers...")
    
    parser = SokolParser(sokol_dir)
    if not parser.parse_headers():
        return False
    
    print()
    print("Statistics:")
    print(f"  - {len(parser.enums)} enums")
    print(f"  - {len(parser.structs)} structs")
    print(f"  - {len(parser.typedefs)} typedefs")
    print(f"  - {len(parser.func_typedefs)} function pointer types")
    print(f"  - {len(parser.functions)} functions")
    
    print()
    print("Generating Python bindings...")
    
    generator = BindingGenerator(parser)
    output = generator.generate()
    
    output_file.write_text(output)
    print(f"Generated: {output_file}")
    
    return True


def main():
    print("=" * 60)
    print("Sokol Python Bindings Setup")
    print("=" * 60)
    print()
    
    script_dir = Path(__file__).parent
    sokol_dir = script_dir / "sokol_headers"
    output_file = script_dir / "../sokol" / "__init__.py"
    
    # Step 1: Download headers
    if not download_headers(sokol_dir):
        return 1
    
    print()
    
    # Step 2: Check libclang
    if not check_libclang():
        return 1
    
    # Step 3: Generate bindings
    if not generate_bindings(sokol_dir, output_file):
        return 1
    
    print()
    print("=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print()
    print("Generated files:")
    print(f"  - {output_file}")
    print()
    print("Usage example:")
    print("  from sokol import *")
    print("  sokol = load_sokol_dll('sokol-dll.dll')")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
