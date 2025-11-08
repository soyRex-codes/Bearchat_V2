"""
Test the response formatting function
Run this to see how the formatter cleans up messy model outputs
"""

import re

def format_response_text(text):
    """
    Post-process model output to ensure clean, readable formatting.
    
    This function:
    - Removes excessive whitespace and random symbols
    - Ensures proper line breaks between ideas
    - Formats lists with bullets or numbers
    - Cleans up formatting artifacts from model output
    """
    if not text or len(text.strip()) == 0:
        return text
    
    # 1. Remove excessive whitespace (multiple spaces, tabs)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 2. Remove random special characters that don't belong (but keep bullets, numbers, basic punctuation)
    # Keep: . , ! ? : ; - • () [] "" '' 1234567890
    # Remove: weird unicode, excessive symbols
    text = re.sub(r'[^\w\s.,!?:;\-•()\[\]"\'•\n1-9]', '', text)
    
    # 3. Fix line breaks - ensure proper spacing
    # Remove excessive newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 4. Add line breaks before numbered lists if missing
    # Pattern: "text1. Item" -> "text\n1. Item"
    text = re.sub(r'([a-z])\s*(\d+\.)', r'\1\n\n\2', text)
    
    # 5. Add line breaks before bullet points if missing
    # Pattern: "text• Item" -> "text\n• Item"
    text = re.sub(r'([a-z])\s*(•)', r'\1\n\n\2', text)
    
    # 6. Ensure space after sentence-ending punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    
    # 7. Clean up common model artifacts
    text = text.replace('###', '')  # Remove training format markers
    text = text.replace('***', '')  # Remove excessive asterisks
    text = text.replace('---', '')  # Remove separator lines
    
    # 8. Ensure proper spacing around list items
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a list item (bullet or number)
        is_list_item = bool(re.match(r'^[•\-\*]|\d+\.', line))
        
        # Add proper spacing before list items
        if is_list_item and formatted_lines and not re.match(r'^[•\-\*]|\d+\.', formatted_lines[-1]):
            # Add blank line before first list item
            if formatted_lines[-1]:  # Only if previous line wasn't blank
                formatted_lines.append('')
        
        formatted_lines.append(line)
    
    # 9. Join lines back together
    text = '\n'.join(formatted_lines)
    
    # 10. Final cleanup: remove leading/trailing whitespace
    text = text.strip()
    
    # 11. Ensure no more than 2 consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text


# Test cases showing different formatting issues
test_cases = [
    # Test 1: Wall of text with no line breaks
    {
        "name": "Wall of Text",
        "input": "The Computer Science program at Missouri State requires several core courses.You need to take CS101, CS102, and CS201.Additionally you'll need Math courses and electives.The total is 120 credit hours.",
        "expected_fix": "Adds spaces after periods, breaks into readable sentences"
    },
    
    # Test 2: List without proper formatting
    {
        "name": "Unformatted List",
        "input": "Requirements include:1. Complete application2. Submit transcripts3. Pay application fee4. Write essay",
        "expected_fix": "Adds line breaks before numbered items"
    },
    
    # Test 3: Random symbols and artifacts
    {
        "name": "Random Symbols",
        "input": "Missouri State offers ###several programs*** including---Computer Science, Engineering, and Business. @#$ You can apply online.",
        "expected_fix": "Removes ###, ***, ---, @#$"
    },
    
    # Test 4: Excessive whitespace
    {
        "name": "Excessive Whitespace",
        "input": "The tuition    for   in-state students    is   $7,588.\n\n\n\n\nOut-of-state    is  $15,898.",
        "expected_fix": "Normalizes spacing and newlines"
    },
    
    # Test 5: Bullet points without spacing
    {
        "name": "Bullet Points",
        "input": "Benefits include• Scholarships available• Modern facilities• Expert faculty• Career support",
        "expected_fix": "Adds line breaks before bullets"
    }
]


def run_tests():
    print("=" * 80)
    print("RESPONSE FORMATTER TEST SUITE")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 TEST {i}: {test['name']}")
        print(f"Expected Fix: {test['expected_fix']}")
        print("-" * 80)
        
        print("\n❌ BEFORE (messy model output):")
        print(repr(test['input']))  # repr shows \n explicitly
        print(f"\n{test['input']}")
        
        formatted = format_response_text(test['input'])
        
        print("\n✅ AFTER (cleaned & formatted):")
        print(repr(formatted))
        print(f"\n{formatted}")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    run_tests()
    
    print("\n\n🎉 FORMATTER IS READY!")
    print("\nThe formatting improvements will:")
    print("  ✓ Remove excessive whitespace")
    print("  ✓ Clean up random symbols and artifacts")
    print("  ✓ Add proper line breaks before lists")
    print("  ✓ Format bullet points and numbered items")
    print("  ✓ Ensure readable spacing throughout")
    print("\nTest your API server with: python api_server.py")
