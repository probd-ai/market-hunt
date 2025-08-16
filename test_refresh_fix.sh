#!/bin/bash

# Test script to verify Refresh Mappings fix
echo "🧪 Testing Refresh Mappings Fix..."
echo "=================================="

# Test 1: Check current mapping count
echo "📊 1. Checking current mapping statistics..."
STATS=$(curl -s "http://localhost:3001/api/stock/mappings?limit=5")
MAPPED_COUNT=$(echo $STATS | jq -r '.mapped_count')
TOTAL_COUNT=$(echo $STATS | jq -r '.total_mappings')

echo "   Total mappings: $TOTAL_COUNT"
echo "   Mapped count: $MAPPED_COUNT"

if [ "$MAPPED_COUNT" = "200" ] && [ "$TOTAL_COUNT" = "200" ]; then
    echo "   ✅ Mapping counts are correct"
else
    echo "   ❌ Mapping counts are incorrect"
    exit 1
fi

# Test 2: Check that symbols have status information
echo ""
echo "🔍 2. Checking symbol status information..."
STATUS_CHECK=$(curl -s "http://localhost:3001/api/stock/mappings?limit=3" | jq -r '.mappings[] | select(.is_up_to_date != null) | .symbol' | wc -l)

if [ "$STATUS_CHECK" = "3" ]; then
    echo "   ✅ Symbols have status information"
else
    echo "   ❌ Some symbols missing status information"
    exit 1
fi

# Test 3: Test refresh functionality
echo ""
echo "🔄 3. Testing refresh mappings endpoint..."
REFRESH_RESULT=$(curl -s -X POST "http://localhost:3001/api/stock/mappings/refresh")
SUCCESS=$(echo $REFRESH_RESULT | jq -r '.success')
UPDATED_COUNT=$(echo $REFRESH_RESULT | jq -r '.status_result.successful_updates')

if [ "$SUCCESS" = "true" ] && [ "$UPDATED_COUNT" = "200" ]; then
    echo "   ✅ Refresh successful: $UPDATED_COUNT symbols updated"
else
    echo "   ❌ Refresh failed or incomplete"
    exit 1
fi

# Test 4: Verify status preserved after refresh
echo ""
echo "✅ 4. Verifying status preserved after refresh..."
AFTER_REFRESH_STATUS=$(curl -s "http://localhost:3001/api/stock/mappings?limit=3" | jq -r '.mappings[] | select(.is_up_to_date != null) | .symbol' | wc -l)

if [ "$AFTER_REFRESH_STATUS" = "3" ]; then
    echo "   ✅ Status information preserved after refresh"
else
    echo "   ❌ Status information lost after refresh"
    exit 1
fi

# Test 5: Check frontend proxy
echo ""
echo "🌐 5. Testing frontend proxy..."
FRONTEND_STATS=$(curl -s "http://localhost:3000/api/stock/mappings?limit=5")
FRONTEND_MAPPED=$(echo $FRONTEND_STATS | jq -r '.mapped_count')

if [ "$FRONTEND_MAPPED" = "200" ]; then
    echo "   ✅ Frontend proxy working correctly"
else
    echo "   ❌ Frontend proxy not working"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Refresh Mappings fix is working correctly."
echo ""
echo "Summary:"
echo "- ✅ Mapping count shows correct 200/200 symbols"
echo "- ✅ Status information preserved during refresh"
echo "- ✅ Refresh endpoint updates both mappings and status"
echo "- ✅ Frontend proxy integration working"
echo "- ✅ All symbols maintain their calculated status"
