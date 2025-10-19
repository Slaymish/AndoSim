# CI/CD and Release Process

## Overview

The Ando Barrier Physics Simulator uses **GitHub Actions** for automated multi-platform builds, testing, and releases. This document describes the CI/CD setup and release workflow.

---

## CI/CD Architecture

### Workflows

1. **`.github/workflows/build.yml`**: Continuous Integration
   - **Triggers**: Push to `main`/`develop`, Pull Requests, Releases
   - **Platforms**: Ubuntu (Linux x64), macOS (Universal), Windows (x64)
   - **Actions**: Build, test, create artifacts
   
2. **`.github/workflows/release.yml`**: Release Automation
   - **Triggers**: Git tags matching `v*` (e.g., `v1.0.0`)
   - **Actions**: Build all platforms, package addons, upload to GitHub Releases

### Build Matrix

| Platform | OS | Python | Eigen Source | Package Format |
|----------|------|--------|--------------|----------------|
| Linux | ubuntu-latest | 3.11 | apt-get (libeigen3-dev) | .zip |
| macOS | macos-latest | 3.11 | brew (eigen) | .zip |
| Windows | windows-latest | 3.11 | Manual download (3.4.0) | .zip |

---

## Local Development

### Build Commands

```bash
# Standard release build
./build.sh

# Debug build
./build.sh -d

# Clean build with tests
./build.sh -c -t

# Clean only
./build.sh -c
```

### Testing Locally

```bash
# Run all tests
cd build
ctest --output-on-failure

# Run specific Python tests
python3 tests/test_adaptive_timestep.py
python3 tests/test_heatmap_colors.py
python3 tests/test_e2e.py

# Production validation
python3 validate_production.py
```

---

## Release Process

### Step-by-Step Guide

#### 1. Pre-Release Checklist

- [ ] All tests passing locally (`./build.sh -c -t`)
- [ ] Production validation passes (`python3 validate_production.py`)
- [ ] CHANGELOG.md updated with new version
- [ ] VERSION file updated
- [ ] Documentation updated (README, BUILD.md, etc.)
- [ ] All changes committed to `main` branch

#### 2. Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (1.X.0): New features (backward compatible)
- **PATCH** (1.0.X): Bug fixes (backward compatible)

**Pre-release suffixes**:
- `v1.0.0-alpha.1`: Early testing
- `v1.0.0-beta.1`: Feature-complete, testing
- `v1.0.0-rc.1`: Release candidate

#### 3. Create Release

```bash
# Update VERSION file
echo "1.0.0" > VERSION

# Update CHANGELOG.md
# Replace "Unreleased" section with version and date

# Commit version bump
git add VERSION CHANGELOG.md
git commit -m "Release v1.0.0"

# Create and push tag
git tag -a v1.0.0 -m "Version 1.0.0: Phase 4 Core Features"
git push origin main
git push origin v1.0.0
```

#### 4. Monitor CI/CD

1. Go to [GitHub Actions](https://github.com/YOUR_USERNAME/BlenderSim/actions)
2. Watch the "Create Release" workflow
3. Check build status for all platforms (Linux, macOS, Windows)
4. Wait for all builds to complete (~10-15 minutes)

#### 5. Verify Release

1. Go to [Releases](https://github.com/YOUR_USERNAME/BlenderSim/releases)
2. Find the new release (e.g., "Ando Barrier v1.0.0")
3. Verify all platform packages are attached:
   - `ando_barrier_v1.0.0_linux_x64.zip`
   - `ando_barrier_v1.0.0_macos_universal.zip`
   - `ando_barrier_v1.0.0_windows_x64.zip`
4. Download and test installation on each platform

#### 6. Post-Release

- [ ] Update release notes on GitHub (if needed)
- [ ] Announce release (Discord, forums, etc.)
- [ ] Monitor issue tracker for platform-specific problems
- [ ] Start next development cycle (bump VERSION to `1.1.0-dev`)

---

## CI/CD Workflow Details

### Build Workflow (`.github/workflows/build.yml`)

**Trigger Events**:
```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [published]
```

**Build Steps**:
1. **Checkout**: Clone repository
2. **Setup Python**: Install Python 3.11
3. **Install Dependencies**:
   - Linux: `apt-get install cmake build-essential libeigen3-dev python3-dev`
   - macOS: `brew install cmake eigen pybind11`
   - Windows: `choco install cmake` + manual Eigen download
4. **Build**: CMake configure + build
5. **Test**: Run test suite (`test_adaptive_timestep.py`, `test_heatmap_colors.py`)
6. **Package**: Create addon ZIP for platform
7. **Upload Artifacts**: Store on GitHub (90-day retention)

### Release Workflow (`.github/workflows/release.yml`)

**Trigger Event**:
```yaml
on:
  push:
    tags:
      - 'v*'  # Matches v1.0.0, v2.1.3, etc.
```

**Release Steps**:
1. **Create Release**: GitHub release with auto-generated notes
2. **Build All Platforms**: Matrix build (Linux, macOS, Windows)
3. **Package Addons**: Platform-specific ZIPs
4. **Upload Assets**: Attach ZIPs to GitHub Release

---

## Platform-Specific Notes

### Linux (Ubuntu)

**Dependencies**:
```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential libeigen3-dev python3-dev
pip install numpy pybind11
```

**Build**:
```bash
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build .
```

**Output**: `ando_barrier_core.cpython-311-x86_64-linux-gnu.so`

### macOS (Universal Binary)

**Dependencies**:
```bash
brew install cmake eigen pybind11
pip install numpy
```

**Build**:
```bash
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build .
```

**Output**: `ando_barrier_core.cpython-311-darwin.so` (Universal: Intel + Apple Silicon)

**Note**: macOS may require code signing for distribution (not yet implemented).

### Windows (x64)

**Dependencies**:
```powershell
choco install cmake
pip install numpy pybind11

# Manual Eigen download
Invoke-WebRequest -Uri "https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip" -OutFile "eigen.zip"
Expand-Archive -Path eigen.zip -DestinationPath C:\
$env:EIGEN3_INCLUDE_DIR = "C:\eigen-3.4.0"
```

**Build**:
```powershell
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release -DEigen3_DIR=$env:EIGEN3_INCLUDE_DIR ..
cmake --build . --config Release
```

**Output**: `ando_barrier_core.cp311-win_amd64.pyd`

---

## Troubleshooting CI/CD

### Build Failures

**Symptom**: CI build fails with "Eigen3 not found"

**Solution**:
- Linux/macOS: Check package manager installation
- Windows: Verify `EIGEN3_INCLUDE_DIR` environment variable in workflow

**Symptom**: CI build fails with "Python.h not found"

**Solution**:
- Ensure `python3-dev` (Linux) or `python-devel` (Windows) is installed
- Check Python version matches setup-python action (3.11)

**Symptom**: Test failures on Windows

**Solution**:
- Check path separators (use `os.path.join` instead of `/`)
- Verify floating point precision (Windows may have different defaults)
- Check line endings (CRLF vs LF)

### Release Issues

**Symptom**: Release workflow doesn't trigger

**Solution**:
- Verify tag format: `v1.0.0` (must start with 'v')
- Check tag was pushed: `git push origin v1.0.0`
- Verify GitHub Actions are enabled in repo settings

**Symptom**: Release assets not uploaded

**Solution**:
- Check workflow logs for upload errors
- Verify `GITHUB_TOKEN` has write permissions
- Check asset size (< 2GB limit)

---

## Performance

### Build Times (Approximate)

| Platform | Build Time | Test Time | Total |
|----------|------------|-----------|-------|
| Linux | 3-5 min | 30-60s | 4-6 min |
| macOS | 5-8 min | 30-60s | 6-9 min |
| Windows | 6-10 min | 30-60s | 7-11 min |

**Total Release Time**: ~15-20 minutes (parallel builds)

### Artifact Sizes

| Platform | Module Size | Addon Package |
|----------|-------------|---------------|
| Linux | 580 KB | ~600 KB |
| macOS | 620 KB | ~650 KB |
| Windows | 590 KB | ~620 KB |

---

## Security

### GitHub Secrets

No custom secrets required. Uses built-in `GITHUB_TOKEN` for:
- Creating releases
- Uploading assets
- Accessing repository

### Code Signing

**Status**: Not yet implemented

**Future Work**:
- macOS: Sign with Apple Developer ID
- Windows: Authenticode signing
- Both: Notarization for enhanced security

---

## Future Improvements

### Planned Enhancements

1. **Automatic Version Bumping**: Script to update VERSION, CHANGELOG, and tag
2. **Release Notes Generation**: Auto-extract from CHANGELOG.md
3. **Pre-release Testing**: Deploy to test environment before public release
4. **Code Signing**: macOS notarization and Windows Authenticode
5. **Performance Benchmarks**: Track build times and binary sizes over versions
6. **Docker Builds**: Reproducible builds with containerization
7. **Release Notifications**: Webhook to Discord/Slack on release

### Monitoring

Track these metrics:
- Build success rate (target: >95%)
- Average build time per platform
- Artifact download counts
- Platform-specific issue reports

---

## Support

### Reporting Build Issues

If CI/CD fails:

1. **Check GitHub Actions logs**: [Actions tab](https://github.com/YOUR_USERNAME/BlenderSim/actions)
2. **Reproduce locally**: Follow platform-specific build steps above
3. **Create issue**: Include:
   - Platform (Linux/macOS/Windows)
   - Build log excerpt (error messages)
   - CMake version, Python version
   - Steps to reproduce

### Contact

- **GitHub Issues**: [BlenderSim Issues](https://github.com/YOUR_USERNAME/BlenderSim/issues)
- **Discussions**: [BlenderSim Discussions](https://github.com/YOUR_USERNAME/BlenderSim/discussions)

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CMake Documentation](https://cmake.org/documentation/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
