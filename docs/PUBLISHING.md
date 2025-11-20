# Publishing EDON v1.0.1

Complete guide for publishing EDON v1.0.1 to GitHub Releases and PyPI.

---

## 1. GitHub Release

### Prerequisites

- GitHub CLI installed: https://cli.github.com/
- Authenticated: `gh auth login`
- Repository access: Ensure you have write access to the repository

### Option A: Using Script (Recommended)

**Windows**:
```powershell
.\scripts\create_github_release.ps1
```

**Linux/macOS**:
```bash
chmod +x scripts/create_github_release.sh
./scripts/create_github_release.sh
```

### Option B: Manual GitHub CLI

```bash
# Create release
gh release create v1.0.1 \
  --title "EDON CAV Engine v1.0.1" \
  --notes-file release/v1.0.1/RELEASE_NOTES.md \
  EDON_v1.0.1_OEM_RELEASE.zip \
  release/v1.0.1/edon-0.1.0-py3-none-any.whl

# If Docker image exists
gh release upload v1.0.1 release/v1.0.1/edon-server-v1.0.1.docker
```

### Option C: GitHub Web UI

1. Go to: `https://github.com/YOUR_ORG/edon-cav-engine/releases/new`
2. **Tag**: `v1.0.1` (create new tag)
3. **Release title**: `EDON CAV Engine v1.0.1`
4. **Description**: Copy from `release/v1.0.1/RELEASE_NOTES.md`
5. **Attach files**:
   - `EDON_v1.0.1_OEM_RELEASE.zip` (full bundle)
   - `release/v1.0.1/edon-0.1.0-py3-none-any.whl` (Python SDK)
   - `release/v1.0.1/edon-server-v1.0.1.docker` (Docker image, optional)
6. Click **Publish release**

### Verify Release

```bash
# View release
gh release view v1.0.1

# List releases
gh release list
```

---

## 2. PyPI Publishing (Optional)

### Prerequisites

- PyPI account: https://pypi.org/account/register/
- API token: https://pypi.org/manage/account/token/
- Build tools: `pip install build twine`

### Setup PyPI Credentials

**Option A: Use API Token (Recommended)**

Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Option B: Environment Variables**

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Option A: Using Script (Recommended)

**Windows**:
```powershell
.\scripts\publish_to_pypi.ps1
```

**Linux/macOS**:
```bash
chmod +x scripts/publish_to_pypi.sh
./scripts/publish_to_pypi.sh
```

### Option B: Manual Steps

```bash
cd sdk/python

# Install build tools
pip install build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build wheel and source distribution
python -m build

# Verify package
twine check dist/*

# Upload to PyPI (will prompt for credentials)
twine upload dist/*
```

### Test Installation

After publishing, test installation:

```bash
# Install from PyPI
pip install edon

# Or with gRPC support
pip install edon[grpc]

# Test import
python -c "from edon import EdonClient; print('OK')"
```

### Update Version for Next Release

When publishing a new version:

1. Update version in `sdk/python/pyproject.toml`
2. Update version in `sdk/python/edon/__init__.py`
3. Rebuild and publish

---

## 3. Release Checklist

### Pre-Publishing
- [ ] All tests passing
- [ ] Version numbers correct
- [ ] Release notes complete
- [ ] Documentation updated
- [ ] Bundle created (`EDON_v1.0.1_OEM_RELEASE.zip`)

### GitHub Release
- [ ] GitHub CLI authenticated
- [ ] Release notes file ready
- [ ] All assets built (wheel, zip, docker)
- [ ] Release created
- [ ] Assets uploaded
- [ ] Release URL verified

### PyPI Publishing (Optional)
- [ ] PyPI account created
- [ ] API token configured
- [ ] Package built (`python -m build`)
- [ ] Package verified (`twine check`)
- [ ] Published to PyPI
- [ ] Installation tested

### Post-Publishing
- [ ] Update main README with PyPI install instructions
- [ ] Notify OEM partners
- [ ] Update changelog
- [ ] Monitor for issues

---

## 4. Quick Reference

### GitHub Release

**Script**: `scripts/create_github_release.ps1` or `.sh`  
**Manual**: `gh release create v1.0.1 --title "..." --notes-file ...`  
**URL**: `https://github.com/YOUR_ORG/edon-cav-engine/releases/tag/v1.0.1`

### PyPI Publishing

**Script**: `scripts/publish_to_pypi.ps1` or `.sh`  
**Manual**: `python -m build && twine upload dist/*`  
**Package**: `edon`  
**Install**: `pip install edon[grpc]`

---

## 5. Troubleshooting

### GitHub Release Issues

**"Not authenticated"**:
```bash
gh auth login
```

**"Permission denied"**:
- Check repository access
- Verify GitHub CLI permissions

### PyPI Publishing Issues

**"Invalid credentials"**:
- Verify API token in `~/.pypirc` or environment variables
- Check token hasn't expired

**"Package already exists"**:
- Version already published
- Update version number in `pyproject.toml`

**"Package name conflict"**:
- Package name `edon` may be taken
- Consider using `edon-cav` or `edon-cav-engine`

---

## 6. Security Notes

- **Never commit** PyPI credentials to git
- Use API tokens, not passwords
- Store credentials in `~/.pypirc` (not in repo)
- Use environment variables in CI/CD

---

**See also**: 
- `PUBLISHING_GUIDE.md` - Complete publishing guide
- `scripts/publish_release.md` - Publishing instructions

