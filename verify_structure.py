#!/usr/bin/env python3
"""Verify edon-cav-engine directory structure and imports."""

import sys
from pathlib import Path

print("=" * 60)
print("EDON CAV Engine Structure Verification")
print("=" * 60)

# Check directory structure
print("\n1. Checking directory structure...")
required_dirs = [
    "app",
    "app/routes",
    "models",
]
for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✓ {dir_path}/")
    else:
        print(f"   ✗ {dir_path}/ MISSING")

# Check required files
print("\n2. Checking required files...")
required_files = [
    "app/__init__.py",
    "app/main.py",
    "app/routes/__init__.py",
    "app/routes/models.py",
    "app/routes/telemetry.py",
]
for file_path in required_files:
    if Path(file_path).exists():
        print(f"   ✓ {file_path}")
    else:
        print(f"   ✗ {file_path} MISSING")

# Test imports
print("\n3. Testing imports...")
try:
    from app.routes.models import router, _discover_model
    print("   ✓ app.routes.models imports OK")
except Exception as e:
    print(f"   ✗ app.routes.models import failed: {e}")

try:
    from app.main import app
    print("   ✓ app.main imports OK")
except Exception as e:
    print(f"   ✗ app.main import failed: {e}")

# Test model discovery
print("\n4. Testing model discovery...")
try:
    info = _discover_model()
    print(f"   ✓ Model discovery works")
    print(f"     Name: {info['name']}")
    print(f"     SHA256: {info['sha256'][:16]}...")
    print(f"     Features: {info['features']}")
    print(f"     Window: {info['window']}")
    print(f"     PCA Dim: {info['pca_dim']}")
except Exception as e:
    print(f"   ✗ Model discovery failed: {e}")

# Check routes
print("\n5. Checking routes...")
try:
    routes = [(r.path, list(r.methods) if hasattr(r, 'methods') else []) 
              for r in app.routes if hasattr(r, 'path')]
    model_routes = [r for r in routes if 'model' in r[0].lower()]
    if model_routes:
        print(f"   ✓ Found {len(model_routes)} model route(s):")
        for path, methods in model_routes:
            print(f"     {path} {methods}")
    else:
        print("   ✗ No model routes found")
except Exception as e:
    print(f"   ✗ Route check failed: {e}")

print("\n" + "=" * 60)
print("Verification complete!")
print("=" * 60)

