#!/bin/bash

# Test script for anti-ban functionality
# This script demonstrates the random delays between parallel processors

echo "🛡️  Anti-Ban Test Script"
echo "========================"
echo ""

echo "This script tests the anti-ban functionality with random delays."
echo "It will show how parallel processors start with staggered delays."
echo ""

# Check if we have a test CSV file
if [ ! -f "data.csv" ]; then
    echo "❌ No data.csv found. Creating a small test file..."
    
    # Create a small test CSV file
    cat > data.csv << EOF
URL;Deal Date
https://example.com;2016-09-30
https://test.org;2017-03-15
https://demo.net;2018-01-20
EOF
    
    echo "✅ Created test data.csv with 3 URLs"
    echo ""
fi

echo "🧪 Testing anti-ban delays..."
echo ""

# Test with small splits and short delays for demonstration
echo "Running test with:"
echo "  - 2 splits (2 rows each)"
echo "  - Parallel execution"
echo "  - Shared downloads"
echo "  - Custom delays: 10-30 seconds (for testing)"
echo ""

# Run the test
./run_split.sh -r 2 -p -s --min-delay 10 --max-delay 30

echo ""
echo "🎯 Test completed!"
echo ""
echo "📊 What happened:"
echo "  1. Split 1 started immediately"
echo "  2. Split 2 waited 10-30 seconds before starting"
echo "  3. Each split had its own initial delay (10-60 seconds)"
echo "  4. Each download had increased delays between requests"
echo ""
echo "💡 For production use:"
echo "  - Use longer delays: --min-delay 60 --max-delay 300"
echo "  - Consider sequential mode for very sensitive targets"
echo "  - Monitor logs for any ban indicators"
echo "" 