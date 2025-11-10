#!/usr/bin/env python3
"""
Backend API Test Script
Tests all endpoints to verify the backend is working correctly
"""
import requests
import json
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api"

def print_test(test_name, status, details=""):
    """Pretty print test results"""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {test_name}")
    if details:
        print(f"   {details}")
    print()

def test_health_check():
    """Test health check endpoint"""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        data = response.json()

        if response.status_code == 200:
            print_test(
                "Health Check",
                True,
                f"Status: {data.get('status')}, Qdrant: {data.get('qdrant_connected')}, Docs: {data.get('documents_count')}"
            )
            return True
        else:
            print_test("Health Check", False, f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_test("Health Check", False, "⚠️  Backend is not running! Start it with: python -m uvicorn backend.app.main:app --reload")
        return False
    except Exception as e:
        print_test("Health Check", False, f"Error: {str(e)}")
        return False

def test_upload_file():
    """Test file upload endpoint"""
    print("=" * 60)
    print("TEST 2: File Upload")
    print("=" * 60)

    # Create a test file
    test_content = """
    # Test Document

    This is a test document for the AI search system.

    ## Machine Learning
    Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computers to improve their performance on a specific task through experience.

    ## Key Concepts
    - Supervised Learning
    - Unsupervised Learning
    - Neural Networks
    - Deep Learning
    """

    test_file_path = Path("/tmp/test_document.md")
    test_file_path.write_text(test_content)

    try:
        files = {'file': ('test_document.md', open(test_file_path, 'rb'), 'text/markdown')}
        data = {'conversation_id': 'test-conversation-123'}

        print("Uploading test file...")
        response = requests.post(f"{API_BASE_URL}/upload", files=files, data=data, timeout=30)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print_test(
                "File Upload",
                True,
                f"File: {result.get('file_name')}, Chunks: {result.get('chunks_created')}, Time: {result.get('processing_time')}s"
            )
            return result.get('file_id')
        else:
            print_test("File Upload", False, f"Error: {result.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_test("File Upload", False, f"Error: {str(e)}")
        return None
    finally:
        if test_file_path.exists():
            test_file_path.unlink()

def test_list_documents(conversation_id="test-conversation-123"):
    """Test list documents endpoint"""
    print("=" * 60)
    print("TEST 3: List Documents")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/documents", params={'conversation_id': conversation_id}, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            doc_count = result.get('total_count', 0)
            print_test(
                "List Documents",
                True,
                f"Found {doc_count} document(s) in conversation"
            )

            if doc_count > 0:
                doc = result['documents'][0]
                print(f"   Sample: {doc.get('file_name')} ({doc.get('chunk_count')} chunks)")
            return True
        else:
            print_test("List Documents", False, f"Error: {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_test("List Documents", False, f"Error: {str(e)}")
        return False

def test_search_files_only(conversation_id="test-conversation-123"):
    """Test search with files_only mode"""
    print("=" * 60)
    print("TEST 4: Search (files_only mode)")
    print("=" * 60)

    try:
        payload = {
            "query": "What is machine learning?",
            "top_k": 5,
            "search_mode": "files_only",
            "reasoning_mode": "non_reasoning",
            "conversation_id": conversation_id
        }

        print("Searching uploaded documents...")
        response = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=30)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print_test(
                "Search (files_only)",
                True,
                f"Found {result.get('total_results')} results in {result.get('processing_time')}s"
            )

            if result.get('answer'):
                print(f"   Answer: {result['answer'][:100]}...")
            return True
        else:
            print_test("Search (files_only)", False, f"Error: {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_test("Search (files_only)", False, f"Error: {str(e)}")
        return False

def test_search_auto_mode(conversation_id="test-conversation-123"):
    """Test search with auto mode (AI selects best mode)"""
    print("=" * 60)
    print("TEST 5: Search (auto mode)")
    print("=" * 60)

    try:
        payload = {
            "query": "What are the latest developments in AI?",
            "top_k": 5,
            "search_mode": "auto",
            "reasoning_mode": "non_reasoning",
            "conversation_id": conversation_id
        }

        print("AI is selecting the best search mode...")
        response = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=30)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            selected_mode = result.get('selected_mode', 'unknown')
            reasoning = result.get('mode_reasoning', 'N/A')

            print_test(
                "Search (auto mode)",
                True,
                f"AI selected: {selected_mode}"
            )
            print(f"   Reasoning: {reasoning[:150]}...")
            return True
        else:
            print_test("Search (auto mode)", False, f"Error: {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_test("Search (auto mode)", False, f"Error: {str(e)}")
        return False

def test_delete_document(file_id):
    """Test delete document endpoint"""
    print("=" * 60)
    print("TEST 6: Delete Document")
    print("=" * 60)

    if not file_id:
        print_test("Delete Document", False, "No file_id available (upload test may have failed)")
        return False

    try:
        response = requests.delete(f"{API_BASE_URL}/documents/{file_id}", timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get('success'):
            print_test(
                "Delete Document",
                True,
                f"Deleted {result.get('deleted_count')} chunk(s)"
            )
            return True
        else:
            print_test("Delete Document", False, f"Error: {result.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print_test("Delete Document", False, f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 Backend API Test Suite")
    print("=" * 60)
    print(f"Testing: {API_BASE_URL}")
    print("=" * 60 + "\n")

    start_time = time.time()

    # Run tests in order
    results = []

    # Test 1: Health check
    results.append(("Health Check", test_health_check()))

    if not results[-1][1]:
        print("\n❌ Backend is not running. Please start it first:")
        print("   python -m uvicorn backend.app.main:app --reload")
        return

    # Test 2: Upload file
    file_id = test_upload_file()
    results.append(("File Upload", file_id is not None))

    # Test 3: List documents
    results.append(("List Documents", test_list_documents()))

    # Test 4: Search files only
    results.append(("Search (files_only)", test_search_files_only()))

    # Test 5: Search auto mode
    results.append(("Search (auto)", test_search_auto_mode()))

    # Test 6: Delete document
    results.append(("Delete Document", test_delete_document(file_id)))

    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    for test_name, result in results:
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}")

    print("=" * 60)
    print(f"Passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    print(f"Time: {total_time:.2f}s")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! Backend is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")

if __name__ == "__main__":
    main()
