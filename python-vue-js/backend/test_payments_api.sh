#!/bin/bash

# Test script for Coinsub Payments API
# Usage: ./test_payments_api.sh
# Make sure COINSUB_API_KEY and COINSUB_MERCHANT_ID are set in your .env file

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if variables are set
if [ -z "$COINSUB_API_KEY" ] || [ "$COINSUB_API_KEY" = "your-api-key-here" ]; then
    echo "Error: COINSUB_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$COINSUB_MERCHANT_ID" ] || [ "$COINSUB_MERCHANT_ID" = "your-merchant-id-here" ]; then
    echo "Error: COINSUB_MERCHANT_ID not set in .env file"
    exit 1
fi

# Determine API URL based on environment
if [ "$COINSUB_ENV" = "production" ]; then
    API_URL="https://api.coinsub.io"
else
    API_URL="https://test-api.coinsub.io"
fi

echo "Testing Coinsub Payments API..."
echo "API URL: $API_URL"
echo "Merchant ID: $COINSUB_MERCHANT_ID"
echo ""

# Make the API request
curl --location --request GET "${API_URL}/v1/payments/all" \
--header "Merchant-ID: ${COINSUB_MERCHANT_ID}" \
--header "API-Key: ${COINSUB_API_KEY}" \
--header "Content-Type: application/json" \
--data '{
  "agreement": null,
  "status": ""
}' | python3 -m json.tool
