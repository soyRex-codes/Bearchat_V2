"""
Test script to demonstrate conversation memory feature

This shows how the model remembers previous Q&A pairs and can answer follow-up questions.
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_conversation_memory():
    """Test conversation memory with follow-up questions"""
    
    print("="*80)
    print("TESTING CONVERSATION MEMORY")
    print("="*80)
    
    # Simulated conversation history
    conversation_history = []
    
    # Question 1: Ask about CS program
    print("\n[USER] What is the Computer Science program at Missouri State?")
    response1 = requests.post(
        f"{BASE_URL}/chat",
        json={
            "question": "What is the Computer Science program at Missouri State?",
            "conversation_history": conversation_history
        }
    )
    
    if response1.status_code == 200:
        answer1 = response1.json()['answer']
        print(f"\n[BOOMER] {answer1[:200]}...")  # First 200 chars
        
        # Add to history
        conversation_history.append({
            "question": "What is the Computer Science program at Missouri State?",
            "answer": answer1
        })
    else:
        print(f"ERROR: {response1.status_code}")
        return
    
    print("\n" + "-"*80)
    
    # Question 2: Follow-up without context (should use pronoun reference)
    print("\n[USER] What courses are in the first year?")
    response2 = requests.post(
        f"{BASE_URL}/chat",
        json={
            "question": "What courses are in the first year?",
            "conversation_history": conversation_history  # Include previous Q&A
        }
    )
    
    if response2.status_code == 200:
        answer2 = response2.json()['answer']
        print(f"\n[BOOMER] {answer2[:200]}...")
        
        # Add to history
        conversation_history.append({
            "question": "What courses are in the first year?",
            "answer": answer2
        })
    else:
        print(f"ERROR: {response2.status_code}")
        return
    
    print("\n" + "-"*80)
    
    # Question 3: Another follow-up (using "it" - should know what "it" refers to)
    print("\n[USER] How long does it take to complete?")
    response3 = requests.post(
        f"{BASE_URL}/chat",
        json={
            "question": "How long does it take to complete?",
            "conversation_history": conversation_history  # Include all previous Q&As
        }
    )
    
    if response3.status_code == 200:
        answer3 = response3.json()['answer']
        print(f"\n[BOOMER] {answer3}")
        
        # Add to history
        conversation_history.append({
            "question": "How long does it take to complete?",
            "answer": answer3
        })
    else:
        print(f"ERROR: {response3.status_code}")
        return
    
    print("\n" + "="*80)
    print("CONVERSATION HISTORY MAINTAINED:")
    print(f"Total exchanges: {len(conversation_history)}")
    print("="*80)

if __name__ == "__main__":
    # Check server health first
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("\nServer is running!")
            test_conversation_memory()
        else:
            print("\nERROR: Server not healthy")
    except Exception as e:
        print(f"\nERROR: Cannot connect to server at {BASE_URL}")
        print(f"Make sure api_server.py is running!")
        print(f"Error: {e}")
