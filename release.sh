#!/bin/bash

# Release Helper Script for Ando Barrier Physics Simulator
# Makes it easy to create new releases with proper version management

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if version provided
if [ -z "$1" ]; then
    print_error "Usage: ./release.sh <version> [--pre-release]"
    echo ""
    echo "Examples:"
    echo "  ./release.sh 1.0.0           # Stable release"
    echo "  ./release.sh 1.0.0-rc.1      # Release candidate"
    echo "  ./release.sh 1.0.0 --dry-run # Test without pushing"
    echo ""
    echo "Version format: X.Y.Z or X.Y.Z-suffix"
    echo "  - Major.Minor.Patch (e.g., 1.0.0)"
    echo "  - With suffix: 1.0.0-alpha.1, 1.0.0-beta.2, 1.0.0-rc.3"
    exit 1
fi

VERSION=$1
DRY_RUN=false

# Check for flags
if [ "$2" = "--dry-run" ]; then
    DRY_RUN=true
    print_warning "DRY RUN MODE - No changes will be pushed"
fi

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-z]+\.[0-9]+)?$ ]]; then
    print_error "Invalid version format: $VERSION"
    echo "Expected: X.Y.Z or X.Y.Z-suffix (e.g., 1.0.0 or 1.0.0-rc.1)"
    exit 1
fi

TAG="v$VERSION"

print_info "Preparing release: $TAG"
echo ""

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    print_warning "Working directory has uncommitted changes!"
    echo ""
    git status --short
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Release cancelled"
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    print_error "Tag $TAG already exists!"
    echo "To create a new release, use a different version number"
    echo "Or delete the old tag: git tag -d $TAG && git push origin :refs/tags/$TAG"
    exit 1
fi

# Pre-release checks
print_info "Running pre-release checks..."

# 1. Check VERSION file
echo "$VERSION" > VERSION
print_success "Updated VERSION file to $VERSION"

# 3. Build check
print_info "Testing build..."
if ./build.sh -c > /dev/null 2>&1; then
    print_success "Build successful"
else
    print_error "Build failed!"
    echo "Fix build errors before creating release"
    exit 1
fi

# 4. Check CHANGELOG
if ! grep -q "\[$VERSION\]" CHANGELOG.md; then
    print_warning "CHANGELOG.md doesn't contain [$VERSION] section"
    echo ""
    echo "Please update CHANGELOG.md with:"
    echo "  ## [$VERSION] - $(date +%Y-%m-%d)"
    echo ""
    read -p "Open CHANGELOG.md now? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        ${EDITOR:-nano} CHANGELOG.md
    else
        print_warning "Remember to update CHANGELOG.md manually!"
    fi
fi

echo ""
print_info "Pre-release checks complete!"
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════"
echo "  Release Summary"
echo "═══════════════════════════════════════════════════════════"
echo "  Version:    $VERSION"
echo "  Tag:        $TAG"
echo "  Branch:     $(git branch --show-current)"
echo "  Commit:     $(git rev-parse --short HEAD)"
echo "  Date:       $(date +"%Y-%m-%d %H:%M:%S")"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Confirm
if [ "$DRY_RUN" = false ]; then
    read -p "Create release $TAG and push to GitHub? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Release cancelled"
        exit 1
    fi
fi

# Create release
print_info "Creating release $TAG..."

# Commit version bump
git add VERSION CHANGELOG.md
git commit -m "Bump version to $VERSION" || print_warning "No changes to commit"

if [ "$DRY_RUN" = false ]; then
    # Push main branch
    print_info "Pushing to main..."
    git push origin main
    
    # Create and push tag
    print_info "Creating tag $TAG..."
    git tag -a "$TAG" -m "Release $VERSION"
    
    print_info "Pushing tag $TAG..."
    git push origin "$TAG"
    
    echo ""
    print_success "Release $TAG created successfully!"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  Next Steps"
    echo "═══════════════════════════════════════════════════════════"
    echo "  1. Monitor GitHub Actions:"
    echo "     https://github.com/Slaymish/AndoSim/actions"
    echo ""
    echo "  2. Wait for builds to complete (~15-20 minutes)"
    echo ""
    echo "  3. Check release page:"
    echo "     https://github.com/Slaymish/AndoSim/releases/tag/$TAG"
    echo ""
    echo "  4. Download and test artifacts on each platform"
    echo ""
    echo "  5. Update release notes if needed (on GitHub)"
    echo "═══════════════════════════════════════════════════════════"
else
    print_info "DRY RUN: Would have created tag $TAG and pushed"
    print_info "Run without --dry-run to actually create the release"
fi

echo ""
print_success "Done! 🎉"
