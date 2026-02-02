# Sokol Shared Libraries

This directory contains pre-built Sokol shared libraries for all supported platforms.

## Files

| File | Platform | Architecture | Backend |
|------|----------|--------------|---------|
| `sokol-windows-x64.dll` | Windows | x64 | D3D11 |
| `libsokol-linux-x64.so` | Linux | x64 | OpenGL |
| `libsokol-macos-x64.dylib` | macOS | Intel x64 | Metal |
| `libsokol-macos-arm64.dylib` | macOS | Apple Silicon | Metal |

## Building from Source

These libraries are automatically built by the GitHub Actions workflow in `.github/workflows/build-sokol.yml`.

To build manually, see the instructions in the main README.md.
