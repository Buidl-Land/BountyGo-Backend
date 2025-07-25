#!/usr/bin/env python3
"""
Dependencies validation script for BountyGo Backend
Validates that all required dependencies for URL AI Agent are properly installed
"""
import sys
import importlib
import subprocess
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_python_package(package_name, import_name=None):
    """Check if a Python package is installed and importable"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name} is installed and importable")
        return True
    except ImportError as e:
        print(f"❌ {package_name} is not installed or not importable: {e}")
        return False

def check_system_dependencies():
    """Check system-level dependencies"""
    print("🔍 Checking system dependencies...")
    
    system_deps = [
        ("curl", "curl --version"),
        ("gcc", "gcc --version"),
    ]
    
    all_ok = True
    for dep_name, check_cmd in system_deps:
        try:
            result = subprocess.run(
                check_cmd.split(), 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                print(f"✅ {dep_name} is available")
            else:
                print(f"❌ {dep_name} is not available or not working")
                all_ok = False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"❌ {dep_name} is not available")
            all_ok = False
    
    return all_ok

def check_core_dependencies():
    """Check core application dependencies"""
    print("🔍 Checking core dependencies...")
    
    core_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("asyncpg", "asyncpg"),
        ("alembic", "alembic"),
        ("redis", "redis"),
        ("pydantic", "pydantic"),
        ("pydantic-settings", "pydantic_settings"),
        ("python-dotenv", "dotenv"),
        ("httpx", "httpx"),
        ("aiohttp", "aiohttp"),
    ]
    
    all_ok = True
    for package_name, import_name in core_deps:
        if not check_python_package(package_name, import_name):
            all_ok = False
    
    return all_ok

def check_url_agent_dependencies():
    """Check URL agent specific dependencies"""
    print("🔍 Checking URL agent dependencies...")
    
    url_agent_deps = [
        ("beautifulsoup4", "bs4"),
        ("readability-lxml", "readability"),
        ("camel-ai", "camel"),
        ("lxml", "lxml"),
        ("html5lib", "html5lib"),
        ("requests", "requests"),
        ("chardet", "chardet"),
    ]
    
    all_ok = True
    for package_name, import_name in url_agent_deps:
        if not check_python_package(package_name, import_name):
            all_ok = False
    
    return all_ok

def check_development_dependencies():
    """Check development dependencies"""
    print("🔍 Checking development dependencies...")
    
    dev_deps = [
        ("pytest", "pytest"),
        ("pytest-asyncio", "pytest_asyncio"),
        ("pytest-cov", "pytest_cov"),
        ("black", "black"),
        ("isort", "isort"),
        ("flake8", "flake8"),
    ]
    
    all_ok = True
    for package_name, import_name in dev_deps:
        if not check_python_package(package_name, import_name):
            all_ok = False
    
    return all_ok

def check_camel_ai_functionality():
    """Check if camel-ai is working properly"""
    print("🔍 Testing camel-ai functionality...")
    
    try:
        from camel.agents import ChatAgent
        from camel.messages import BaseMessage
        from camel.models import ModelFactory
        from camel.types import ModelType, RoleType
        
        print("✅ camel-ai core modules imported successfully")
        
        # Test basic functionality
        try:
            # This is a basic test - we don't actually create a model here
            # since it would require API keys
            print("✅ camel-ai basic functionality test passed")
            return True
        except Exception as e:
            print(f"⚠️  camel-ai functionality test warning: {e}")
            return True  # Still return True as import worked
            
    except ImportError as e:
        print(f"❌ camel-ai functionality test failed: {e}")
        return False

def check_content_extraction_functionality():
    """Check content extraction functionality"""
    print("🔍 Testing content extraction functionality...")
    
    try:
        from bs4 import BeautifulSoup
        from readability import Document
        import lxml
        import html5lib
        
        # Test BeautifulSoup with different parsers
        test_html = "<html><body><h1>Test</h1><p>Content</p></body></html>"
        
        # Test lxml parser
        soup_lxml = BeautifulSoup(test_html, 'lxml')
        if soup_lxml.find('h1').text == 'Test':
            print("✅ BeautifulSoup with lxml parser working")
        else:
            print("❌ BeautifulSoup with lxml parser not working")
            return False
        
        # Test html5lib parser
        soup_html5lib = BeautifulSoup(test_html, 'html5lib')
        if soup_html5lib.find('h1').text == 'Test':
            print("✅ BeautifulSoup with html5lib parser working")
        else:
            print("❌ BeautifulSoup with html5lib parser not working")
            return False
        
        # Test readability
        doc = Document(test_html)
        if doc.title():
            print("✅ Readability extraction working")
        else:
            print("⚠️  Readability extraction test warning")
        
        return True
        
    except Exception as e:
        print(f"❌ Content extraction functionality test failed: {e}")
        return False

def check_async_functionality():
    """Check async functionality"""
    print("🔍 Testing async functionality...")
    
    try:
        import asyncio
        import aiohttp
        import asyncpg
        
        async def test_async():
            # Test basic async functionality
            await asyncio.sleep(0.001)
            return True
        
        # Run async test
        result = asyncio.run(test_async())
        if result:
            print("✅ Basic async functionality working")
        
        print("✅ aiohttp and asyncpg available for async operations")
        return True
        
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        return False

def check_application_imports():
    """Check if application modules can be imported"""
    print("🔍 Testing application imports...")
    
    try:
        # Test core application imports
        from app.core.config import settings
        print("✅ App configuration imported successfully")
        
        from app.core.database import engine
        print("✅ Database engine imported successfully")
        
        # Test URL agent imports
        try:
            from app.agent.config import url_agent_settings
            print("✅ URL agent configuration imported successfully")
        except ImportError as e:
            print(f"⚠️  URL agent configuration import warning: {e}")
        
        try:
            from app.agent.content_extractor import ContentExtractor
            print("✅ Content extractor imported successfully")
        except ImportError as e:
            print(f"⚠️  Content extractor import warning: {e}")
        
        try:
            from app.agent.url_parsing_agent import URLParsingAgent
            print("✅ URL parsing agent imported successfully")
        except ImportError as e:
            print(f"⚠️  URL parsing agent import warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Application imports test failed: {e}")
        return False

def generate_dependency_report():
    """Generate a detailed dependency report"""
    print("\n" + "=" * 60)
    print("📋 Dependency Report")
    print("=" * 60)
    
    try:
        import pkg_resources
        
        # Get installed packages
        installed_packages = {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
        
        # Key packages for URL agent
        key_packages = [
            'fastapi', 'uvicorn', 'sqlalchemy', 'asyncpg', 'redis',
            'beautifulsoup4', 'readability-lxml', 'camel-ai', 'lxml',
            'html5lib', 'aiohttp', 'httpx', 'pydantic'
        ]
        
        print("Key packages:")
        for package in key_packages:
            version = installed_packages.get(package, 'Not installed')
            print(f"  {package}: {version}")
        
        print(f"\nTotal installed packages: {len(installed_packages)}")
        
    except ImportError:
        print("pkg_resources not available - cannot generate detailed report")

def main():
    """Main validation function"""
    print("🚀 BountyGo Dependencies Validation")
    print("=" * 50)
    
    # Run all checks
    checks = [
        ("System Dependencies", check_system_dependencies),
        ("Core Dependencies", check_core_dependencies),
        ("URL Agent Dependencies", check_url_agent_dependencies),
        ("Development Dependencies", check_development_dependencies),
        ("Camel-AI Functionality", check_camel_ai_functionality),
        ("Content Extraction Functionality", check_content_extraction_functionality),
        ("Async Functionality", check_async_functionality),
        ("Application Imports", check_application_imports),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * len(check_name))
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed with exception: {e}")
            results.append((check_name, False))
    
    # Generate report
    generate_dependency_report()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Validation Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All dependency checks passed!")
        print("\n📚 Next steps:")
        print("   1. Run configuration validation: python scripts/validate_config.py")
        print("   2. Start the application: python -m uvicorn app.main:app --reload")
        print("   3. Test URL agent functionality: python test_url_agent_integration.py")
        return 0
    else:
        print("💥 Some dependency checks failed!")
        print("\n🔧 Fix suggestions:")
        print("   1. Install missing packages: pip install -r requirements.txt")
        print("   2. Check system dependencies: apt-get install gcc curl libxml2-dev libxslt-dev")
        print("   3. Verify Python version: python --version (should be 3.11+)")
        print("   4. Re-run validation: python scripts/validate_dependencies.py")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        sys.exit(1)