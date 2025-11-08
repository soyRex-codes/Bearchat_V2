#!/usr/bin/env python3
"""
Quick test to verify LoRA adapter scaling fix
"""

import requests
import json

API_URL = "http://localhost:5000/chat"

test_questions = [
    {
        "name": "Course Numbers Test",
        "question": "What do you know about MSU CS program?",
        "should_contain": ["CSC 130", "CSC 131", "CSC 232"],
        "should_not_contain": ["CSC 1300", "CSC 1400", "CS 101"]
    },
    {
        "name": "Math Course Test",
        "question": "What math courses are required for CS?",
        "should_contain": ["MTH 261", "MTH 280", "MTH 314"],
        "should_not_contain": ["MATH 1313", "MATH 1325", "STAT 1502"]
    },
    {
        "name": "Prerequisites Test",
        "question": "What are the prerequisites for CSC 232?",
        "should_contain": ["CSC 131", "MTH 314"],
        "should_not_contain": ["CSC 130", "CSC 1300"]
    },
    {
        "name": "Course Details Test",
        "question": "Tell me about CSC 131",
        "should_contain": ["Computational Thinking", "4 credit"],
        "should_not_contain": ["Programming", "3 credit"]
    },
    {
        "name": "Contact Info Test",
        "question": "How do I contact the CS department?",
        "should_contain": ["(417) 836-4157", "ComputerScience@missouristate.edu"],
        "should_not_contain": []
    }
]

def test_api():
    print("="*80)
    print("🧪 TESTING LORA ADAPTER SCALING FIX")
    print("="*80)
    print("\nThis test verifies that the model outputs REAL MSU courses,")
    print("not hallucinated generic course numbers.\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_questions)}: {test['name']}")
        print(f"{'='*80}")
        print(f"Question: {test['question']}\n")
        
        try:
            response = requests.post(
                API_URL,
                json={"question": test['question']},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                failed += 1
                continue
            
            data = response.json()
            answer = data['response']
            
            print(f"Response:\n{answer}\n")
            
            # Check should_contain
            contains_all = True
            for item in test['should_contain']:
                if item in answer:
                    print(f"  ✅ Contains: {item}")
                else:
                    print(f"  ❌ Missing: {item}")
                    contains_all = False
            
            # Check should_not_contain
            contains_none = True
            for item in test['should_not_contain']:
                if item in answer:
                    print(f"  ❌ Hallucinated: {item} (should NOT be in response!)")
                    contains_none = False
                else:
                    print(f"  ✅ Correctly avoided: {item}")
            
            if contains_all and contains_none:
                print(f"\n✅ TEST PASSED")
                passed += 1
            else:
                print(f"\n❌ TEST FAILED")
                failed += 1
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Error: Cannot connect to API server")
            print(f"   Make sure API server is running: python api_server.py")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"📊 TEST RESULTS")
    print(f"{'='*80}")
    print(f"Passed: {passed}/{len(test_questions)}")
    print(f"Failed: {failed}/{len(test_questions)}")
    
    if failed == 0:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"\nThe LoRA adapter scaling fix is working correctly.")
        print(f"Model is outputting REAL MSU course information.")
    else:
        print(f"\n⚠️  SOME TESTS FAILED")
        print(f"\nIf model is still hallucinating:")
        print(f"1. Check that API server restarted with scaling applied")
        print(f"2. Look for '⚡ APPLYING QUICK FIX: Scaling LoRA adapters 2x...'")
        print(f"3. If issue persists, retrain with alpha=64 (see A100_TRAINING_GUIDE.md)")

if __name__ == "__main__":
    test_api()
