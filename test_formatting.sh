#!/bin/bash
# Quick test script for the formatting improvements

echo "======================================================================"
echo "🧪 TESTING RESPONSE FORMATTING IMPROVEMENTS"
echo "======================================================================"
echo ""
echo "This script will test the new formatting system"
echo ""

# Activate virtual environment
source venv/bin/activate

# Test 1: Formatter unit tests
echo "📝 Step 1: Testing formatter function..."
echo "----------------------------------------------------------------------"
python test_formatter.py
echo ""
echo "✅ Formatter tests complete!"
echo ""

# Test 2: Syntax check
echo "📝 Step 2: Checking API server syntax..."
echo "----------------------------------------------------------------------"
python -m py_compile api_server.py
if [ $? -eq 0 ]; then
    echo "✅ No syntax errors in api_server.py"
else
    echo "❌ Syntax errors found!"
    exit 1
fi
echo ""

# Instructions for manual testing
echo "======================================================================"
echo "🚀 NEXT STEPS - Manual Testing Required"
echo "======================================================================"
echo ""
echo "1. Start the API server:"
echo "   python api_server.py"
echo ""
echo "2. In another terminal, test with your Flutter app:"
echo "   cd bearchat_ai"
echo "   flutter run"
echo ""
echo "3. Test questions to try:"
echo "   • 'What are the CS degree requirements?'"
echo "   • 'How do I apply to MSU?'"
echo "   • 'Tell me about housing options'"
echo "   • 'What scholarships are available?'"
echo ""
echo "4. What to look for:"
echo "   ✓ Proper line breaks between ideas"
echo "   ✓ Lists formatted with bullets or numbers"
echo "   ✓ No random symbols (###, ***, etc.)"
echo "   ✓ Clean, readable spacing"
echo "   ✓ No wall-of-text responses"
echo ""
echo "======================================================================"
echo "📋 CHANGES MADE"
echo "======================================================================"
echo ""
echo "✅ Enhanced system prompt with formatting rules"
echo "✅ Added post-processing formatter function"
echo "✅ Applied formatter to /chat endpoint"
echo "✅ Applied formatter to /upload endpoint"
echo "✅ Created test suite (test_formatter.py)"
echo "✅ Created documentation (FORMATTING_IMPROVEMENTS.md)"
echo ""
echo "======================================================================"
echo "🎉 Setup Complete! Ready for testing."
echo "======================================================================"
