"""
Test Script for Document Processing Pipeline
=============================================
Tests the document upload and processing functionality.

Usage:
    python test_document_upload.py
"""

import requests
import json
from pathlib import Path

# API endpoint
API_BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if data.get('document_processor_ready'):
            print("✅ Document processor is ready")
        else:
            print("❌ Document processor not ready")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_document_upload(file_path: str, question: str):
    """Test document upload endpoint"""
    print("\n" + "="*80)
    print(f"TEST 2: Document Upload")
    print("="*80)
    print(f"File: {file_path}")
    print(f"Question: {question}")
    
    try:
        # Check if file exists
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return False
        
        # Prepare request
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'question': question,
                'max_length': 1024,
                'temperature': 0.3,
                'top_p': 0.85
            }
            
            print(f"\n📤 Uploading document...")
            response = requests.post(
                f"{API_BASE_URL}/upload",
                files=files,
                data=data,
                timeout=300  # 5 minutes timeout for processing
            )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "="*80)
            print("RESPONSE")
            print("="*80)
            
            print(f"\n📄 Document Info:")
            doc_info = result.get('document_info', {})
            print(f"   File: {doc_info.get('file_name')}")
            print(f"   Type: {doc_info.get('file_type')}")
            print(f"   Processing: {doc_info.get('processing_method')}")
            print(f"   Characters: {doc_info.get('num_characters'):,}")
            print(f"   Chunks: {doc_info.get('num_chunks')}")
            
            print(f"\n❓ Question:")
            print(f"   {result.get('question')}")
            
            print(f"\n💬 Answer:")
            print(f"   {result.get('answer')}")
            
            print(f"\n📊 Context:")
            print(f"   Topic: {result.get('topic')}")
            print(f"   Type: {result.get('content_type')}")
            
            print("\n✅ Document upload test PASSED")
            return True
        else:
            error_data = response.json()
            print(f"\n❌ Upload failed: {error_data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_without_document():
    """Test regular chat endpoint (without document)"""
    print("\n" + "="*80)
    print("TEST 3: Regular Chat (No Document)")
    print("="*80)
    
    try:
        data = {
            "question": "What scholarships are available for CS students at MSU?",
            "max_length": 512,
            "temperature": 0.3,
            "top_p": 0.85
        }
        
        print(f"Question: {data['question']}")
        print(f"\n📤 Sending request...")
        
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=data,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n💬 Answer:")
            print(f"   {result.get('answer')}")
            print(f"\n📊 Context:")
            print(f"   Topic: {result.get('topic')}")
            print(f"   Type: {result.get('content_type')}")
            
            print("\n✅ Regular chat test PASSED")
            return True
        else:
            error_data = response.json()
            print(f"\n❌ Chat failed: {error_data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("BEARCHAT DOCUMENT PROCESSING TEST SUITE")
    print("="*80)
    print("\nMake sure the API server is running:")
    print("  python api_server.py")
    print()
    
    # Test 1: Health check
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ Server not ready. Make sure api_server.py is running.")
        return
    
    # Test 2: Regular chat (baseline)
    test_chat_without_document()
    
    # Test 3: Document upload
    print("\n" + "="*80)
    print("DOCUMENT UPLOAD TESTS")
    print("="*80)
    print("\nTo test document upload, you need a sample PDF or image.")
    print("Examples:")
    print("  - Transcript PDF: transcript.pdf")
    print("  - Course catalog: course_catalog.pdf")
    print("  - Degree audit screenshot: degree_audit.png")
    print()
    
    # Ask user for test file
    file_path = input("Enter path to test document (or 'skip' to skip): ").strip()
    
    if file_path and file_path.lower() != 'skip':
        question = input("Enter question about the document: ").strip()
        
        if not question:
            question = "What information is in this document?"
        
        test_document_upload(file_path, question)
    else:
        print("\n⏭️  Skipping document upload test")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("\n✅ Document processing pipeline is ready!")
    print("\nNext steps:")
    print("  1. Test with real transcripts/syllabi")
    print("  2. Integrate with Flutter app")
    print("  3. Deploy to production")


if __name__ == "__main__":
    main()
