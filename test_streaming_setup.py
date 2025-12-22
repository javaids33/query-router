#!/usr/bin/env python3
"""
Test script to validate streaming ingestion setup without requiring running services.
This validates the configuration, scripts, and documentation.
"""

import os
import sys

def test_files_exist():
    """Test that all required files exist."""
    print("🔍 Checking if all required files exist...")
    
    required_files = [
        "docker-compose.yml",
        "STREAMING.md",
        "examples/streaming_ingestion.py",
        "examples/requirements.txt",
        "examples/README.md",
        "README.md"
    ]
    
    missing = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing.append(file_path)
            print(f"  ❌ Missing: {file_path}")
        else:
            print(f"  ✅ Found: {file_path}")
    
    if missing:
        print(f"\n❌ Test Failed: {len(missing)} files missing")
        return False
    
    print("✅ All required files exist\n")
    return True


def test_docker_compose():
    """Test docker-compose configuration."""
    print("🔍 Validating docker-compose.yml...")
    
    with open("docker-compose.yml", "r") as f:
        content = f.read()
    
    required_services = ["kafka", "zookeeper", "flink-jobmanager", "flink-taskmanager"]
    missing = []
    
    for service in required_services:
        if service in content:
            print(f"  ✅ Service found: {service}")
        else:
            missing.append(service)
            print(f"  ❌ Service missing: {service}")
    
    if missing:
        print(f"\n❌ Test Failed: {len(missing)} services missing from docker-compose.yml")
        return False
    
    print("✅ docker-compose.yml contains all streaming services\n")
    return True


def test_streaming_documentation():
    """Test that STREAMING.md contains key sections."""
    print("🔍 Validating STREAMING.md...")
    
    with open("STREAMING.md", "r") as f:
        content = f.read()
    
    required_sections = [
        "Kafka",
        "Flink",
        "Iceberg",
        "Nessie",
        "Architecture",
        "Getting Started",
        "Use Cases"
    ]
    
    missing = []
    for section in required_sections:
        if section.lower() in content.lower():
            print(f"  ✅ Section found: {section}")
        else:
            missing.append(section)
            print(f"  ❌ Section missing: {section}")
    
    if missing:
        print(f"\n❌ Test Failed: {len(missing)} sections missing from STREAMING.md")
        return False
    
    print("✅ STREAMING.md contains all required sections\n")
    return True


def test_readme_updates():
    """Test that README.md was updated with streaming info."""
    print("🔍 Validating README.md updates...")
    
    with open("README.md", "r") as f:
        content = f.read()
    
    required_mentions = [
        "streaming",
        "Kafka",
        "Flink",
        "STREAMING.md"
    ]
    
    missing = []
    for mention in required_mentions:
        if mention in content:
            print(f"  ✅ Mentioned: {mention}")
        else:
            missing.append(mention)
            print(f"  ❌ Not mentioned: {mention}")
    
    if missing:
        print(f"\n❌ Test Failed: {len(missing)} items not mentioned in README.md")
        return False
    
    print("✅ README.md contains streaming information\n")
    return True


def test_streaming_script():
    """Test that streaming script has proper structure."""
    print("🔍 Validating streaming_ingestion.py...")
    
    with open("examples/streaming_ingestion.py", "r") as f:
        content = f.read()
    
    required_classes = ["StreamingProducer", "StreamingConsumer", "IcebergWriter"]
    required_functions = ["demo_streaming_pipeline", "verify_nessie_connection", "query_streaming_data"]
    
    all_present = True
    
    for cls in required_classes:
        if f"class {cls}" in content:
            print(f"  ✅ Class found: {cls}")
        else:
            print(f"  ❌ Class missing: {cls}")
            all_present = False
    
    for func in required_functions:
        if f"def {func}" in content:
            print(f"  ✅ Function found: {func}")
        else:
            print(f"  ❌ Function missing: {func}")
            all_present = False
    
    if not all_present:
        print("\n❌ Test Failed: streaming_ingestion.py missing required components")
        return False
    
    print("✅ streaming_ingestion.py has proper structure\n")
    return True


def test_syntax():
    """Test Python syntax of streaming script."""
    print("🔍 Checking Python syntax...")
    
    try:
        import py_compile
        py_compile.compile("examples/streaming_ingestion.py", doraise=True)
        print("  ✅ streaming_ingestion.py syntax is valid")
        print("✅ Python syntax check passed\n")
        return True
    except Exception as e:
        print(f"  ❌ Syntax error: {e}")
        print("❌ Python syntax check failed\n")
        return False


def main():
    """Run all tests."""
    print("=" * 80)
    print("🧪 STREAMING INGESTION SETUP VALIDATION")
    print("=" * 80)
    print()
    
    tests = [
        ("Files Exist", test_files_exist),
        ("Docker Compose", test_docker_compose),
        ("Streaming Documentation", test_streaming_documentation),
        ("README Updates", test_readme_updates),
        ("Streaming Script", test_streaming_script),
        ("Python Syntax", test_syntax)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}\n")
            results.append((test_name, False))
    
    print("=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Next Steps:")
        print("  1. Start services: docker compose up -d")
        print("  2. Install dependencies: pip install -r examples/requirements.txt")
        print("  3. Run streaming demo: python examples/streaming_ingestion.py")
        print()
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
