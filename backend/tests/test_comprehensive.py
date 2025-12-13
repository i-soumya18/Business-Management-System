"""
Comprehensive System Validation Test

Tests all core modules and validates Phase 0/1 completion.
"""

import sys
import os
import importlib
import traceback
from typing import List, Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_module_imports() -> Dict[str, Any]:
    """Test importing all core modules."""
    modules_to_test = [
        # Core modules
        'app.core.config',
        'app.core.database',
        'app.core.security',
        'app.core.logging',

        # Models
        'app.models.base',
        'app.models.user',
        'app.models.category',
        'app.models.brand',
        'app.models.supplier',
        'app.models.product',
        'app.models.variant',
        'app.models.inventory',
        'app.models.location',
        'app.models.adjustment',
        'app.models.garment',

        # Schemas
        'app.schemas.auth',
        'app.schemas.user',
        'app.schemas.category',
        'app.schemas.brand',
        'app.schemas.supplier',
        'app.schemas.product',
        'app.schemas.variant',
        'app.schemas.inventory',
        'app.schemas.location',
        'app.schemas.adjustment',
        'app.schemas.garment',

        # Repositories
        'app.repositories.base',
        'app.repositories.user',
        'app.repositories.category',
        'app.repositories.brand',
        'app.repositories.supplier',
        'app.repositories.product',
        'app.repositories.variant',
        'app.repositories.inventory',
        'app.repositories.location',
        'app.repositories.adjustment',
        'app.repositories.garment',
        'app.repositories.reports',

        # API modules
        'app.api.v1.auth',
        'app.api.v1.products',
        'app.api.v1.router',

        # Services
        'app.services.auth_service',
        'app.services.inventory_service',

        # Utils
        'app.utils.validators',
        'app.utils.helpers',
    ]

    results = {
        'total': len(modules_to_test),
        'successful': 0,
        'failed': 0,
        'failures': []
    }

    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
            results['successful'] += 1
            print(f"✅ {module_name}")
        except Exception as e:
            results['failed'] += 1
            results['failures'].append({
                'module': module_name,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            print(f"❌ {module_name}: {e}")

    return results

def test_fastapi_app_initialization() -> Dict[str, Any]:
    """Test FastAPI app initialization."""
    try:
        from app.main import app
        routes = [route.path for route in app.routes]
        return {
            'success': True,
            'routes_count': len(routes),
            'routes': routes[:10]  # First 10 routes
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def test_database_connection() -> Dict[str, Any]:
    """Test database connection."""
    try:
        import asyncio
        from sqlalchemy import text
        from app.core.database import get_db

        async def test_db():
            async for session in get_db():
                # Simple query to test connection
                result = await session.execute(text("SELECT 1 as test"))
                row = result.first()
                return row[0] if row else None

        result = asyncio.run(test_db())
        return {
            'success': True,
            'result': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

def main():
    """Run comprehensive system validation."""
    print("🚀 Starting Comprehensive System Validation")
    print("=" * 50)

    # Test 1: Core Modules Import Test
    print("\n1. Core Modules Import Test:")
    print("-" * 30)
    import_results = test_module_imports()

    print(f"\n📊 Import Results: {import_results['successful']}/{import_results['total']} modules imported successfully")

    if import_results['failed'] > 0:
        print(f"\n❌ Failed Modules ({import_results['failed']}):")
        for failure in import_results['failures']:
            print(f"   - {failure['module']}: {failure['error']}")

    # Test 2: FastAPI App Initialization
    print("\n2. FastAPI App Initialization Test:")
    print("-" * 35)
    app_results = test_fastapi_app_initialization()

    if app_results['success']:
        print(f"✅ FastAPI app initialized successfully")
        print(f"   📍 Routes registered: {app_results['routes_count']}")
        print(f"   🔗 Sample routes: {', '.join(app_results['routes'][:5])}")
    else:
        print(f"❌ FastAPI app initialization failed: {app_results['error']}")

    # Test 3: Database Connection Test
    print("\n3. Database Connection Test:")
    print("-" * 28)
    db_results = test_database_connection()

    if db_results['success']:
        print("✅ Database connection successful")
        print(f"   🔗 Test query result: {db_results['result']}")
    else:
        print(f"❌ Database connection failed: {db_results['error']}")

    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)

    all_passed = (
        import_results['failed'] == 0 and
        app_results['success'] and
        db_results['success']
    )

    if all_passed:
        print("🎉 PHASE 0 & 1 COMPLETION: SUCCESS")
        print("✅ All core modules import successfully")
        print("✅ FastAPI application initializes correctly")
        print("✅ Database connection established")
        print(f"✅ {app_results['routes_count']} API endpoints registered")
        return 0
    else:
        print("⚠️  PHASE 0 & 1 COMPLETION: ISSUES DETECTED")
        if import_results['failed'] > 0:
            print(f"❌ {import_results['failed']} modules failed to import")
        if not app_results['success']:
            print("❌ FastAPI app initialization failed")
        if not db_results['success']:
            print("❌ Database connection failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())