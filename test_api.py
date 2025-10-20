"""
Test script for the MSU Chatbot API
Run this AFTER starting the API server in another terminal
"""

import requests
import json

# API base URL (change if using different IP/port)
API_URL = "http://localhost:8080"

def test_health():
    """Test the health endpoint"""
    print(" Testing /health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_single_chat(question):
    """Test single question chat"""
    print(f" Testing /chat endpoint...")
    print(f"Question: {question}")
    
    response = requests.post(
        f"{API_URL}/chat",
        json={"question": question}
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        print(f"Answer: {result['answer']}")
        print(f"Topic: {result['topic']}")
        print(f"Content Type: {result['content_type']}\n")
    else:
        print(f"Error: {result.get('error')}\n")

def test_batch_chat(questions):
    """Test batch chat with multiple questions"""
    print(f" Testing /batch endpoint...")
    print(f"Questions: {questions}")
    
    response = requests.post(
        f"{API_URL}/batch",
        json={"questions": questions}
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    
    if result.get('success'):
        for i, item in enumerate(result['results'], 1):
            print(f"\n--- Question {i} ---")
            print(f"Q: {item['question']}")
            print(f"A: {item['answer']}")
            print(f"Topic: {item['topic']}")
    else:
        print(f"Error: {result.get('error')}\n")

if __name__ == "__main__":
    print("="*80)
    print(" MSU CHATBOT API TESTS")
    print("="*80)
    print("\n  Make sure the API server is running first!")
    print("   Start it in another terminal: python api_server.py\n")
    
    try:
        # Test 1: Health check
        test_health()
        
        # Test 2: Single questions
        test_single_chat("What courses do I need for a CS degree?")
        test_single_chat("What scholarships are available?")
        
        # Test 3: Batch questions
        test_batch_chat([
            "How do I apply to MSU?",
            "What is the tuition cost?",
            "Tell me about housing options"
        ])
        
        print("="*80)
        print(" All tests completed!")
        print("="*80)
        
    except requests.exceptions.ConnectionError:
        print(" ERROR: Cannot connect to API server!")
        print("   Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f" ERROR: {e}")
