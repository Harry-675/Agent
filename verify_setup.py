#!/usr/bin/env python3
"""Verify that the project structure is set up correctly."""

import os
import sys
from pathlib import Path


def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} missing: {path}")
        return False


def check_directory(path: str, description: str) -> bool:
    """Check if a directory exists."""
    if Path(path).is_dir():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} missing: {path}")
        return False


def main():
    """Run verification checks."""
    print("🔍 Verifying project setup...\n")
    
    checks = []
    
    # Check configuration files
    print("📋 Configuration Files:")
    checks.append(check_file("requirements.txt", "Requirements file"))
    checks.append(check_file(".env.example", "Environment template"))
    checks.append(check_file(".gitignore", "Git ignore file"))
    checks.append(check_file("pytest.ini", "Pytest configuration"))
    checks.append(check_file("docker-compose.yml", "Docker Compose file"))
    checks.append(check_file("README.md", "README file"))
    print()
    
    # Check source directories
    print("📁 Source Directories:")
    checks.append(check_directory("src", "Source directory"))
    checks.append(check_directory("src/config", "Config module"))
    checks.append(check_directory("src/database", "Database module"))
    checks.append(check_directory("src/cache", "Cache module"))
    print()
    
    # Check source files
    print("📄 Source Files:")
    checks.append(check_file("src/__init__.py", "Source init"))
    checks.append(check_file("src/config/__init__.py", "Config init"))
    checks.append(check_file("src/config/settings.py", "Settings module"))
    checks.append(check_file("src/database/__init__.py", "Database init"))
    checks.append(check_file("src/database/connection.py", "Database connection"))
    checks.append(check_file("src/cache/__init__.py", "Cache init"))
    checks.append(check_file("src/cache/connection.py", "Cache connection"))
    checks.append(check_file("src/main.py", "Main application"))
    print()
    
    # Check test directories
    print("🧪 Test Directories:")
    checks.append(check_directory("tests", "Tests directory"))
    checks.append(check_directory("tests/unit", "Unit tests"))
    checks.append(check_directory("tests/property", "Property tests"))
    checks.append(check_directory("tests/integration", "Integration tests"))
    checks.append(check_directory("tests/fixtures", "Test fixtures"))
    print()
    
    # Check test files
    print("📝 Test Files:")
    checks.append(check_file("tests/unit/test_config.py", "Config unit tests"))
    print()
    
    # Check config directory
    print("⚙️  Config Directory:")
    checks.append(check_directory("config", "Config directory"))
    checks.append(check_file("config/news_sources.example.json", "News sources example"))
    print()
    
    # Check setup scripts
    print("🛠️  Setup Scripts:")
    checks.append(check_file("setup.sh", "Linux/Mac setup script"))
    checks.append(check_file("setup.bat", "Windows setup script"))
    checks.append(check_file("verify_setup.py", "Verification script"))
    print()
    
    # Summary
    total = len(checks)
    passed = sum(checks)
    failed = total - passed
    
    print("=" * 50)
    print(f"📊 Summary: {passed}/{total} checks passed")
    
    if failed > 0:
        print(f"❌ {failed} checks failed")
        return 1
    else:
        print("✅ All checks passed!")
        print("\n🎉 Project infrastructure is set up correctly!")
        print("\nNext steps:")
        print("1. Run setup script: ./setup.sh (or setup.bat on Windows)")
        print("2. Edit .env file with your configuration")
        print("3. Edit config/news_sources.json with your news sources")
        print("4. Install dependencies: pip install -r requirements.txt")
        print("5. Run tests: pytest")
        return 0


if __name__ == "__main__":
    sys.exit(main())
