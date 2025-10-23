# Python Shared Libraries and Execute Permissions

## Question
Do Python extension modules (.so/.pyd files) need execute permissions to be imported?

## Answer
**No, but it's standard practice to set them.**

## Technical Details

### Import Behavior (Tested)
```bash
# Without execute permission (still works)
-rw-r--r-- ando_barrier_core.cpython-313-aarch64-linux-gnu.so
python3 -c "import ando_barrier_core"  # ✓ Imports successfully

# With execute permission (standard)
-rwxr-xr-x ando_barrier_core.cpython-313-aarch64-linux-gnu.so
python3 -c "import ando_barrier_core"  # ✓ Imports successfully
```

### Why They Don't Need +x
Python shared libraries are **dynamically loaded**, not directly executed:
1. Python calls `dlopen()` to load the shared object
2. `dlopen()` only requires **read permission** on the file
3. The dynamic linker (ld.so) maps the library into memory
4. No execute permission check is performed

### Why System Python Modules Have +x Anyway
```bash
$ ls -l /usr/lib/python3.13/lib-dynload/*.so
-rwxr-xr-x  array.cpython-313-aarch64-linux-gnu.so
-rwxr-xr-x  _asyncio.cpython-313-aarch64-linux-gnu.so
# All system modules have +x
```

**Reasons:**
1. **Convention**: Shared libraries (.so) traditionally have execute permission
2. **Consistency**: Same permissions as other shared libraries in /usr/lib
3. **Future-proofing**: Some tools might expect it (e.g., security scanners)
4. **No harm**: Setting +x on a shared library is harmless

### CMake Install Behavior
CMake automatically sets execute permission on `LIBRARY` targets:
```cmake
install(TARGETS ando_barrier_core 
    LIBRARY DESTINATION ${CMAKE_SOURCE_DIR}/blender_addon  # Sets rwxr-xr-x
)
```

This is why locally built modules have +x, but the GitHub Actions package initially didn't (file was copied via `cp` which preserves source permissions, and the source in the build tree may have had different permissions depending on how CMake created it).

### Our Packaging
The GitHub Actions workflow uses:
```bash
cp blender_addon/ando_barrier_core*.so addon_package/ando_barrier/
```

This preserves whatever permissions CMake set. Since CMake install sets +x for LIBRARY targets, the packaged file should have it.

## Conclusion

**For ando_barrier_core.so:**
- ✅ Works without +x (tested)
- ✅ Has +x by default (from CMake install)
- ✅ Follows convention (matches system Python modules)
- ✅ No action needed

**Recommendation:** Keep the execute permission (it's automatic from CMake). The validation script now correctly notes this as "standard" rather than "required".
