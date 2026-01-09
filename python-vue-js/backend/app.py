"""
Coinsub Purchase Session Integration - Flask Backend
=====================================================

This Flask application demonstrates how to integrate Coinsub's Purchase Session API
for processing cryptocurrency payments. It uses the Purchase Session flow which is
ideal for companies with large product catalogs as it allows ad-hoc combinations
of products without pre-registering them in Coinsub.

Flow:
1. Frontend creates a cart with products
2. Backend creates a Purchase Session via Coinsub API
3. User connects wallet (WalletConnect) on frontend
4. Backend requests purchase message to sign
5. User signs the message with their wallet
6. Backend submits the signed message to complete the purchase
7. Webhooks notify your system of payment status
"""

import os
import hmac
import hashlib
import json
import queue
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Configure CORS with more permissive settings for debugging
CORS(app, 
     origins=["http://localhost:5173", "http://127.0.0.1:5173"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# Enable Flask request logging with immediate output
import logging
import sys

# Configure logging to go to both file-like stdout and stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ],
    force=True
)

app.logger.setLevel(logging.DEBUG)
app.logger.info("=" * 80)
app.logger.info("🚀 Flask app starting...")
app.logger.info("=" * 80)

# Force stdout/stderr to be unbuffered
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Also use print with flush
def log_print(*args, **kwargs):
    """Print that always flushes immediately."""
    print(*args, **kwargs, flush=True)
    app.logger.info(' '.join(str(arg) for arg in args))

# =============================================================================
# Configuration
# =============================================================================

COINSUB_API_KEY = os.getenv("COINSUB_API_KEY", "your-api-key-here")
COINSUB_MERCHANT_ID = os.getenv("COINSUB_MERCHANT_ID", "your-merchant-id-here")
# Webhook secret is optional for local dev (Coinsub can't reach localhost anyway)
# Required for production - get this from your Coinsub dashboard when configuring webhooks
COINSUB_WEBHOOK_SECRET = os.getenv("COINSUB_WEBHOOK_SECRET", "")

# Use test environment for development, production for live
COINSUB_ENV = os.getenv("COINSUB_ENV", "test")
# Base URLs for Coinsub API
COINSUB_BASE_URL = (
    "https://test-api.coinsub.io" if COINSUB_ENV == "test" 
    else "https://api.coinsub.io"
)

# In-memory storage for demo purposes (use a real database in production)
purchase_sessions = {}
completed_payments = {}

# SSE clients: session_id -> list of message queues
sse_clients = {}
sse_lock = threading.Lock()

# SSE clients: session_id -> list of message queues
sse_clients = {}
sse_lock = threading.Lock()


def get_coinsub_headers():
    """Generate headers for Coinsub API requests with required security headers."""
    import uuid
    headers = {
        "Merchant-ID": COINSUB_MERCHANT_ID,
        "API-Key": COINSUB_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Coinsub-Integration-Example/1.0",
        "X-Request-ID": str(uuid.uuid4()),
        "X-Client-Version": "1.0.0",
        "X-Platform": "python-flask"
    }
    log_print(f"🔑 Request Headers:")
    log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID and len(COINSUB_MERCHANT_ID) > 20 else f"   ⚠️  NO MERCHANT ID!")
    log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY and len(COINSUB_API_KEY) > 20 else f"   ⚠️  NO API KEY!")
    log_print(f"   User-Agent: {headers['User-Agent']}")
    log_print(f"   X-Request-ID: {headers['X-Request-ID']}")
    return headers


# =============================================================================
# API Routes - Purchase Session Flow
# =============================================================================

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def root():
    """Root endpoint - catches misconfigured webhooks."""
    if request.method == "POST":
        log_print("=" * 80)
        log_print("⚠️  POST request received at root (/) endpoint")
        log_print("   This might be a misconfigured webhook!")
        log_print(f"   Expected webhook URL: /api/webhooks/coinsub")
        log_print(f"   Headers: {dict(request.headers)}")
        log_print(f"   Body: {request.get_data()[:200]}")
        log_print("=" * 80)
        return jsonify({
            "error": "Webhook endpoint not found",
            "message": "Please configure your webhook URL to: /api/webhooks/coinsub",
            "expected_url": "/api/webhooks/coinsub"
        }), 404
    return jsonify({
        "status": "healthy",
        "environment": COINSUB_ENV,
        "api_url": COINSUB_BASE_URL,
        "webhook_endpoint": "/api/webhooks/coinsub",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/health", methods=["GET", "OPTIONS"])
def health_check():
    """Health check endpoint."""
    log_print("✅ Health check called")
    return jsonify({
        "status": "healthy",
        "environment": COINSUB_ENV,
        "api_url": COINSUB_BASE_URL,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route("/api/test", methods=["GET", "POST", "OPTIONS"])
def test_endpoint():
    """Test endpoint to verify requests are reaching Flask."""
    log_print("🧪 TEST ENDPOINT CALLED")
    return jsonify({
        "message": "Flask is receiving requests!",
        "method": request.method,
        "path": request.path,
        "headers": dict(request.headers)
    })

@app.before_request
def log_request_info():
    """Log all incoming requests - including OPTIONS (CORS preflight)."""
    log_print(f"\n{'='*80}")
    log_print(f"🔵 INCOMING REQUEST: {request.method} {request.path}")
    if request.method == "OPTIONS":
        log_print(f"   ⚠️  CORS PREFLIGHT REQUEST")
    log_print(f"   Full URL: {request.url}")
    log_print(f"   Remote Address: {request.remote_addr}")
    log_print(f"   Headers:")
    for key, value in request.headers:
        log_print(f"      {key}: {value}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        if request.is_json:
            try:
                data = request.get_json()
                log_print(f"   JSON Body:")
                log_print(json.dumps(data, indent=2))
            except Exception as e:
                log_print(f"   Could not parse JSON: {e}")
        elif request.form:
            log_print(f"   Form Data: {dict(request.form)}")
        elif request.data:
            log_print(f"   Raw Data: {request.data[:500]}")
    log_print(f"{'='*80}")

@app.after_request
def log_response_info(response):
    """Log all outgoing responses."""
    log_print(f"\n{'='*80}")
    log_print(f"🟢 OUTGOING RESPONSE: {request.method} {request.path}")
    log_print(f"   Status Code: {response.status_code}")
    log_print(f"   Response Headers:")
    for key, value in response.headers:
        log_print(f"      {key}: {value}")
    if response.status_code >= 400:
        log_print(f"   ⚠️  ERROR RESPONSE!")
        try:
            if response.is_json:
                log_print(f"   Response Body: {response.get_json()}")
            else:
                log_print(f"   Response Text: {response.get_data(as_text=True)[:500]}")
        except:
            pass
    log_print(f"{'='*80}\n")
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Log all exceptions."""
    import traceback
    log_print(f"\n{'='*80}")
    log_print(f"❌❌❌ EXCEPTION CAUGHT ❌❌❌")
    log_print(f"   Type: {type(e).__name__}")
    log_print(f"   Message: {str(e)}")
    log_print(f"   Traceback:")
    log_print(traceback.format_exc())
    log_print(f"{'='*80}\n")
    return jsonify({"error": str(e)}), 500


@app.route("/api/create-session", methods=["POST"])
def create_purchase_session():
    """
    Create a Coinsub Purchase Session for the cart.
    
    This endpoint receives cart data from the frontend and creates a purchase
    session with Coinsub. Purchase sessions are ideal for dynamic pricing and
    ad-hoc product combinations.
    
    Request Body:
    {
        "items": [
            {"name": "Product 1", "price": 29.99, "quantity": 1},
            {"name": "Product 2", "price": 49.99, "quantity": 2}
        ],
        "currency": "USD",
        "customer_email": "customer@example.com",
        "metadata": {"order_id": "ORD-12345"}
    }
    """
    log_print("=" * 80)
    log_print("📥 CREATE SESSION REQUEST RECEIVED")
    log_print(f"Headers: {dict(request.headers)}")
    log_print(f"Method: {request.method}")
    log_print(f"URL: {request.url}")
    
    try:
        data = request.get_json()
        log_print(f"📦 Request data: {json.dumps(data, indent=2)}")
        
        if not data or "items" not in data:
            return jsonify({"error": "Missing cart items"}), 400
        
        # Calculate total amount
        total_amount = sum(
            item.get("price", 0) * item.get("quantity", 1) 
            for item in data["items"]
        )
        
        # Build purchase session payload for Coinsub
        # Combine all items into a single description
        item_names = [item.get("name", "Item") for item in data["items"]]
        session_name = ", ".join(item_names) if len(item_names) <= 3 else f"{len(data['items'])} items"
        
        session_payload = {
            "name": session_name,
            "details": f"Purchase of {len(data['items'])} item(s)",
            "currency": "USDC",  # Coinsub uses USDC/USDT, not USD
            "recurring": False,
            "amount": total_amount,
            "metadata": {
                "items": data["items"],
                "customer_email": data.get("customer_email"),
                **(data.get("metadata", {}))
            },
            "success_url": data.get("success_url") or "https://dev.communitygaming.io",
            "cancel_url": data.get("cancel_url") or "https://dev.communitygaming.io"
        }
        
        # Create purchase session via Coinsub API
        # Using the correct endpoint: /v1/purchase/session/start
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/session/start"
        log_print("=" * 80)
        log_print(f"📤 CALLING COINSUB API - CREATE SESSION")
        log_print(f"   URL: {api_endpoint}")
        log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID and len(COINSUB_MERCHANT_ID) > 20 else "   ⚠️  NO MERCHANT ID!")
        log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY and len(COINSUB_API_KEY) > 20 else "   ⚠️  NO API KEY!")
        log_print(f"   Payload:")
        log_print(json.dumps(session_payload, indent=2))
        log_print("=" * 80)
        
        response = requests.post(
            api_endpoint,
            headers=get_coinsub_headers(),
            json=session_payload,
            timeout=30
        )
        
        log_print("=" * 80)
        log_print(f"📥 COINSUB API RESPONSE - CREATE SESSION")
        log_print(f"   Status Code: {response.status_code}")
        log_print(f"   Response Headers: {dict(response.headers)}")
        log_print(f"   Response Text: {response.text[:500]}")  # First 500 chars
        log_print("=" * 80)
        
        if response.status_code == 201 or response.status_code == 200:
            response_json = response.json()
            log_print(f"📋 Full Coinsub Response Structure:")
            log_print(json.dumps(response_json, indent=2))
            
            # Coinsub API wraps response in "data" object
            session_data = response_json.get("data", response_json)
            
            # Extract session ID - try multiple possible fields
            session_id = (
                session_data.get("id") or 
                session_data.get("session_id") or 
                session_data.get("purchase_session_id") or
                response_json.get("id") or
                response_json.get("session_id")
            )
            
            if not session_id:
                log_print("❌ ERROR: Could not extract session_id from Coinsub response!")
                log_print(f"   Available keys in session_data: {list(session_data.keys())}")
                log_print(f"   Available keys in response_json: {list(response_json.keys())}")
                return jsonify({"error": "Failed to extract session ID from Coinsub response"}), 500
            
            log_print(f"✅ Extracted session_id: {session_id}")
            
            # Store session locally for tracking
            purchase_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "amount": total_amount,
                "currency": data.get("currency", "USD"),
                "items": data["items"],
                "status": "created",
                "coinsub_data": session_data,
                "metadata": data.get("metadata", {})  # Store metadata for message request
            }
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "amount": total_amount,
                "currency": data.get("currency", "USD"),
                "checkout_url": session_data.get("checkout_url"),
                "expires_at": session_data.get("expires_at")
            })
        else:
            error_details = None
            try:
                error_details = response.json() if response.text else None
            except:
                error_details = response.text
            
            log_print("=" * 80)
            log_print(f"❌❌❌ COINSUB API ERROR - CREATE SESSION ❌❌❌")
            log_print(f"   Status Code: {response.status_code}")
            log_print(f"   Request URL: {api_endpoint}")
            log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID else "   ⚠️  NO MERCHANT ID SET!")
            log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY else "   ⚠️  NO API KEY SET!")
            log_print(f"   Response Headers: {dict(response.headers)}")
            log_print(f"   Error Details: {error_details}")
            log_print(f"   Full Response Text: {response.text}")
            log_print("=" * 80)
            app.logger.error(f"Coinsub API error (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to create purchase session",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except requests.RequestException as e:
        error_msg = f"Network error: {str(e)}"
        app.logger.error(error_msg)
        log_print("=" * 80)
        log_print(f"❌ NETWORK ERROR: {error_msg}")
        log_print(f"Exception type: {type(e)}")
        import traceback
        log_print(traceback.format_exc())
        log_print("=" * 80)
        return jsonify({"error": "Network error connecting to Coinsub"}), 503
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        app.logger.error(error_msg)
        log_print("=" * 80)
        log_print(f"❌ UNEXPECTED ERROR: {error_msg}")
        log_print(f"Exception type: {type(e)}")
        import traceback
        log_print(traceback.format_exc())
        log_print("=" * 80)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/session/<session_id>/events", methods=["GET"])
def stream_session_events(session_id):
    """
    Server-Sent Events (SSE) endpoint for real-time payment updates.
    Frontend connects here and receives transaction hash when webhook arrives.
    """
    log_print("=" * 80)
    log_print(f"📡 SSE CONNECTION REQUEST - Session: {session_id}")
    log_print("=" * 80)
    
    def event_stream():
        # Create a message queue for this client
        message_queue = queue.Queue()
        
        # Register this client
        with sse_lock:
            if session_id not in sse_clients:
                sse_clients[session_id] = []
            sse_clients[session_id].append(message_queue)
            log_print(f"✅ SSE client registered for session {session_id}")
            log_print(f"   Total clients for this session: {len(sse_clients[session_id])}")
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Check if transaction hash is already available (webhook arrived before SSE connection)
            hash_already_sent = False
            if session_id in purchase_sessions:
                session_info = purchase_sessions[session_id]
                if session_info.get("transaction_hash"):
                    log_print(f"✅ Transaction hash already available, sending immediately")
                    event_data = {
                        'type': 'payment.completed',
                        'session_id': session_id,
                        'payment_id': session_info.get('payment_id'),
                        'transaction_hash': session_info.get('transaction_hash'),
                        'chain_id': session_info.get('chain_id'),
                        'amount': session_info.get('amount'),
                        'currency': session_info.get('currency', 'USDC')
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    # Mark that we've sent the hash, so we don't enter the loop
                    hash_already_sent = True
            
            # Keep connection alive and wait for messages (only if hash not already sent)
            if not hash_already_sent:
                while True:
                    try:
                        # Wait for message with timeout to send keepalive
                        message = message_queue.get(timeout=30)
                        if message is None:  # None means close connection
                            break
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send keepalive ping
                        yield f": keepalive\n\n"
        except GeneratorExit:
            log_print(f"🔌 SSE client disconnected for session {session_id}")
        finally:
            # Unregister this client
            with sse_lock:
                if session_id in sse_clients:
                    try:
                        sse_clients[session_id].remove(message_queue)
                        log_print(f"✅ SSE client unregistered for session {session_id}")
                        if not sse_clients[session_id]:
                            del sse_clients[session_id]
                    except ValueError:
                        pass
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route("/api/session/<session_id>/status", methods=["GET"])
def get_session_status(session_id):
    """
    Get the status of a purchase session.
    
    Returns local session status (updated by webhooks) or fetches from Coinsub API.
    
    Possible statuses:
    - created: Session was just created
    - pending: Waiting for payment
    - processing: Payment is being processed
    - completed: Payment successful
    - expired: Session expired
    - cancelled: Session was cancelled
    """
    log_print("=" * 80)
    log_print(f"📥 GET SESSION STATUS REQUEST - Session: {session_id}")
    log_print(f"   Headers: {dict(request.headers)}")
    log_print(f"   Method: {request.method}")
    log_print(f"   URL: {request.url}")
    log_print("=" * 80)
    
    try:
        # First check local session storage (updated by webhooks)
        if session_id in purchase_sessions:
            session_info = purchase_sessions[session_id]
            log_print(f"✅ Found local session: {session_id}")
            log_print(f"   Status: {session_info.get('status', 'unknown')}")
            log_print(f"   Transaction Hash: {session_info.get('transaction_hash', 'N/A')}")
            return jsonify({
                "session_id": session_id,
                "status": session_info.get("status", "created"),
                "amount": session_info.get("amount"),
                "currency": session_info.get("currency"),
                "payment_id": session_info.get("payment_id"),
                "transaction_hash": session_info.get("transaction_hash"),
                "chain_id": session_info.get("chain_id"),
                "created_at": session_info.get("created_at")
            })
        
        # If not found locally, try to fetch from Coinsub API
        log_print(f"⚠️  Session not found locally, fetching from Coinsub API...")
        response = requests.get(
            f"{COINSUB_BASE_URL}/purchase-sessions/{session_id}",
            headers=get_coinsub_headers(),
            timeout=30
        )
        
        log_print(f"📥 Coinsub API Response: {response.status_code}")
        
        if response.status_code == 200:
            coinsub_data = response.json()
            log_print(f"✅ Coinsub API Response: {json.dumps(coinsub_data, indent=2)}")
            return jsonify(coinsub_data)
        else:
            log_print(f"❌ Coinsub API Error: {response.status_code}")
            return jsonify({
                "error": "Session not found",
                "details": response.json() if response.text else None
            }), 404
            
    except Exception as e:
        log_print(f"❌ Error fetching session status: {str(e)}")
        import traceback
        log_print(traceback.format_exc())
        app.logger.error(f"Error fetching session status: {str(e)}")
        return jsonify({"error": "Failed to fetch session status"}), 500


@app.route("/api/session/<session_id>/message", methods=["POST"])
def request_purchase_message(session_id):
    """
    Request a purchase message for the user to sign.
    
    This is part of the headless checkout flow where the user signs
    an EIP-712 structured message with their wallet to authorize the payment.
    
    Request Body:
    {
        "wallet_address": "0x...",
        "chain_id": 1
    }
    """
    log_print("=" * 80)
    log_print(f"📥 REQUEST MESSAGE REQUEST RECEIVED - Session: {session_id}")
    log_print(f"   Headers: {dict(request.headers)}")
    log_print(f"   Method: {request.method}")
    log_print(f"   URL: {request.url}")
    
    try:
        data = request.get_json()
        log_print(f"📦 Request data: {json.dumps(data, indent=2)}")
        
        if not data or "wallet_address" not in data:
            return jsonify({"error": "Missing wallet address"}), 400
        
        # Get session data to extract product info
        session_info = purchase_sessions.get(session_id, {})
        if not session_info:
            return jsonify({"error": "Session not found"}), 404
        
        coinsub_data = session_info.get("coinsub_data", {})
        items = session_info.get("items", [])
        
        # Build product name from items
        if items:
            item_names = [item.get("name", "Item") for item in items]
            product_name = ", ".join(item_names) if len(item_names) <= 3 else f"{len(items)} items"
            # Get price from total amount
            price = session_info.get("amount", 0)
        else:
            product_name = "Purchase"
            price = session_info.get("amount", 0)
        
        # Get metadata from session (nested structure)
        session_metadata = session_info.get("metadata", {})
        
        # Request purchase message from Coinsub
        # Using the correct payload structure
        payload = {
            "purchase_session_id": session_id,
            "wallet_address": data["wallet_address"],
            "product_name": product_name,
            "price": price,
            "metadata": session_metadata,  # Use metadata from session
            "token": "USDC",
            "recurring": False,
            "duration": "One-time",
            "frequency": "One-time",
            "interval": "One-time",
            "chainId": data.get("chain_id", 80002)  # Default to Polygon Amoy for test
        }
        
        # Using the correct endpoint: /v1/purchase/message/request
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/message/request"
        log_print("=" * 80)
        log_print(f"📤 CALLING COINSUB API - REQUEST MESSAGE")
        log_print(f"   URL: {api_endpoint}")
        log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID and len(COINSUB_MERCHANT_ID) > 20 else "   ⚠️  NO MERCHANT ID!")
        log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY and len(COINSUB_API_KEY) > 20 else "   ⚠️  NO API KEY!")
        log_print(f"   Payload:")
        log_print(json.dumps(payload, indent=2))
        log_print("=" * 80)
        
        response = requests.post(
            api_endpoint,
            headers=get_coinsub_headers(),
            json=payload,
            timeout=30
        )
        
        log_print("=" * 80)
        log_print(f"📥 COINSUB API RESPONSE - REQUEST MESSAGE")
        log_print(f"   Status Code: {response.status_code}")
        log_print(f"   Response Headers: {dict(response.headers)}")
        log_print(f"   Response Text: {response.text[:500]}")  # First 500 chars
        log_print("=" * 80)
        
        if response.status_code == 200 or response.status_code == 201:
            response_json = response.json()
            log_print(f"✅ SUCCESS! Full Response Structure:")
            log_print(json.dumps(response_json, indent=2))
            
            # Coinsub API wraps response in "data" object
            data_wrapper = response_json.get("data", response_json)
            
            # The typed data is in "typedDataMessage" field (camelCase)
            typed_data_message = data_wrapper.get("typedDataMessage") or data_wrapper.get("typed_data_message") or data_wrapper.get("typed_data")
            
            # If typedDataMessage exists, extract from it, otherwise try data_wrapper itself
            if typed_data_message:
                domain = typed_data_message.get("domain")
                types = typed_data_message.get("types")
                primary_type = typed_data_message.get("primaryType") or typed_data_message.get("primary_type")
                message = typed_data_message.get("message")
            else:
                # Fallback: try extracting from data_wrapper directly
                domain = data_wrapper.get("domain")
                types = data_wrapper.get("types")
                primary_type = data_wrapper.get("primaryType") or data_wrapper.get("primary_type")
                message = data_wrapper.get("message")
            
            # Get message_id from data_wrapper
            message_id = data_wrapper.get("message_id") or data_wrapper.get("messageId") or data_wrapper.get("purchase_session_id")
            
            log_print(f"📋 Extracted fields:")
            log_print(f"   domain: {domain}")
            log_print(f"   primary_type: {primary_type}")
            log_print(f"   has types: {bool(types)}")
            log_print(f"   has message: {bool(message)}")
            log_print(f"   message_id: {message_id}")
            
            if not primary_type:
                log_print("❌ ERROR: primary_type is missing!")
                log_print(f"   Available keys in typedDataMessage: {list(typed_data_message.keys()) if typed_data_message else 'N/A'}")
                log_print(f"   Available keys in data_wrapper: {list(data_wrapper.keys())}")
                return jsonify({"error": "Invalid response from Coinsub API: missing primary_type"}), 500
            
            if not domain or not types or not message:
                log_print("❌ ERROR: Missing required typed data fields!")
                log_print(f"   domain: {domain}")
                log_print(f"   types: {types}")
                log_print(f"   message: {message}")
                return jsonify({"error": "Invalid response from Coinsub API: missing domain, types, or message"}), 500
            
            return jsonify({
                "success": True,
                "message": message,
                "typed_data": typed_data_message or data_wrapper,
                "domain": domain,
                "types": types,
                "primary_type": primary_type,
                "message_id": message_id
            })
        else:
            error_details = None
            try:
                error_details = response.json() if response.text else None
            except:
                error_details = response.text
            
            log_print("=" * 80)
            log_print(f"❌❌❌ COINSUB API ERROR - REQUEST MESSAGE ❌❌❌")
            log_print(f"   Status Code: {response.status_code}")
            log_print(f"   Request URL: {api_endpoint}")
            log_print(f"   Session ID: {session_id}")
            log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID else "   ⚠️  NO MERCHANT ID SET!")
            log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY else "   ⚠️  NO API KEY SET!")
            log_print(f"   Response Headers: {dict(response.headers)}")
            log_print(f"   Error Details: {error_details}")
            log_print(f"   Full Response Text: {response.text}")
            log_print("=" * 80)
            app.logger.error(f"Coinsub API error requesting message (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to request purchase message",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        error_msg = f"Error requesting purchase message: {str(e)}"
        app.logger.error(error_msg)
        log_print("=" * 80)
        log_print(f"❌ EXCEPTION IN REQUEST MESSAGE: {error_msg}")
        log_print(f"Exception type: {type(e)}")
        import traceback
        log_print(traceback.format_exc())
        log_print("=" * 80)
        return jsonify({"error": "Failed to request purchase message"}), 500


@app.route("/api/session/<session_id>/sign", methods=["POST"])
def submit_signed_message(session_id):
    """
    Submit a signed purchase message to complete the payment.
    
    After the user signs the EIP-712 message with their wallet,
    submit the signature here to authorize and process the payment.
    
    Request Body:
    {
        "signature": "0x...",
        "wallet_address": "0x...",
        "message_id": "..."
    }
    """
    log_print("=" * 80)
    log_print(f"📥 SUBMIT SIGNATURE REQUEST RECEIVED - Session: {session_id}")
    log_print(f"   Headers: {dict(request.headers)}")
    log_print(f"   Method: {request.method}")
    log_print(f"   URL: {request.url}")
    
    try:
        data = request.get_json()
        truncated_data = {**data, 'signature': data.get('signature', '')[:20] + '...' if data.get('signature') else None}
        log_print(f"📦 Request data (signature truncated): {json.dumps(truncated_data, indent=2)}")
        
        if not data or "signature" not in data:
            return jsonify({"error": "Missing signature"}), 400
        
        if not data.get("wallet_address"):
            return jsonify({"error": "Missing wallet address"}), 400
        
        # Get chain ID from wallet store or request, default to Polygon Amoy for test
        chain_id = data.get("chain_id", 80002)
        
        # Submit signed message to Coinsub
        # Using the correct payload structure
        payload = {
            "purchase_session_id": session_id,
            "signed_typed_data": {
                "signature": data["signature"],
                "signing_address": data["wallet_address"],
                "chainId": chain_id
            }
        }
        
        # Using the correct endpoint: /v1/purchase/message/sign
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/message/sign"
        log_print("=" * 80)
        log_print(f"📤 CALLING COINSUB API - SUBMIT SIGNATURE")
        log_print(f"   URL: {api_endpoint}")
        log_print(f"   API Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY and len(COINSUB_API_KEY) > 20 else "   ⚠️  NO API KEY!")
        log_print(f"   Payload:")
        log_print(json.dumps(payload, indent=2))
        log_print("=" * 80)
        
        response = requests.post(
            api_endpoint,
            headers=get_coinsub_headers(),
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            
            # Update local session status
            if session_id in purchase_sessions:
                purchase_sessions[session_id]["status"] = "processing"
            
            return jsonify({
                "success": True,
                "status": result.get("status"),
                "transaction_hash": result.get("transaction_hash"),
                "payment_id": result.get("payment_id")
            })
        else:
            error_details = None
            try:
                error_details = response.json() if response.text else None
            except:
                error_details = response.text
            
            log_print("=" * 80)
            log_print(f"❌❌❌ COINSUB API ERROR - SUBMIT SIGNATURE ❌❌❌")
            log_print(f"   Status Code: {response.status_code}")
            log_print(f"   Request URL: {api_endpoint}")
            log_print(f"   Session ID: {session_id}")
            log_print(f"   Merchant-ID: {COINSUB_MERCHANT_ID[:20]}..." if COINSUB_MERCHANT_ID else "   ⚠️  NO MERCHANT ID SET!")
            log_print(f"   API-Key: {COINSUB_API_KEY[:20]}..." if COINSUB_API_KEY else "   ⚠️  NO API KEY SET!")
            log_print(f"   Response Headers: {dict(response.headers)}")
            log_print(f"   Error Details: {error_details}")
            log_print(f"   Full Response Text: {response.text}")
            log_print("=" * 80)
            app.logger.error(f"Coinsub API error submitting signature (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to submit signed message",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        error_msg = f"Error submitting signed message: {str(e)}"
        app.logger.error(error_msg)
        log_print("=" * 80)
        log_print(f"❌ EXCEPTION IN SUBMIT SIGNATURE: {error_msg}")
        log_print(f"Exception type: {type(e)}")
        import traceback
        log_print(traceback.format_exc())
        log_print("=" * 80)
        return jsonify({"error": "Failed to submit signed message"}), 500


@app.route("/api/session/<session_id>/cancel", methods=["POST"])
def cancel_session(session_id):
    """Cancel or expire a purchase session."""
    try:
        response = requests.post(
            f"{COINSUB_BASE_URL}/purchase-sessions/{session_id}/expire",
            headers=get_coinsub_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            if session_id in purchase_sessions:
                purchase_sessions[session_id]["status"] = "cancelled"
            return jsonify({"success": True, "status": "cancelled"})
        else:
            return jsonify({
                "error": "Failed to cancel session",
                "details": response.json() if response.text else None
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error cancelling session: {str(e)}")
        return jsonify({"error": "Failed to cancel session"}), 500


# =============================================================================
# Webhook Handler
# =============================================================================

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the webhook signature from Coinsub.
    
    Coinsub signs webhook payloads using HMAC-SHA256 with your webhook secret.
    Always verify signatures to ensure webhooks are authentic.
    
    Note: Coinsub cannot send webhooks to localhost. For local development:
    1. Use ngrok or similar: ngrok http 5001
    2. Configure the ngrok URL as your webhook endpoint in Coinsub dashboard
    3. Copy the webhook secret to your .env file
    """
    if not COINSUB_WEBHOOK_SECRET:
        log_print("⚠️  Webhook secret not configured! Skipping signature verification.")
        app.logger.warning(
            "Webhook secret not configured! "
            "Skipping signature verification (OK for development without webhooks)"
        )
        # In development without webhooks configured, skip verification
        # In production, you should ALWAYS have a webhook secret set
        return True
    
    if not signature:
        log_print("❌ No signature provided in webhook request")
        return False
    
    # Coinsub may send signature in different formats:
    # - Plain hex: "abc123..."
    # - With prefix: "sha256=abc123..." or "hmac-sha256=abc123..."
    # Extract the actual signature value
    signature_value = signature
    if '=' in signature:
        signature_value = signature.split('=', 1)[1]
    
    log_print(f"🔐 Verifying signature:")
    log_print(f"   Received: {signature_value[:20]}...")
    log_print(f"   Secret configured: {'Yes' if COINSUB_WEBHOOK_SECRET else 'No'}")
    log_print(f"   Secret length: {len(COINSUB_WEBHOOK_SECRET) if COINSUB_WEBHOOK_SECRET else 0}")
    
    # Calculate expected signature
    expected_signature = hmac.new(
        COINSUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    log_print(f"   Expected: {expected_signature[:20]}...")
    
    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(signature_value, expected_signature)
    
    if not is_valid:
        log_print("❌ Signature verification FAILED")
        log_print(f"   Received: {signature_value}")
        log_print(f"   Expected: {expected_signature}")
    else:
        log_print("✅ Signature verification PASSED")
    
    return is_valid


@app.route("/api/webhooks/coinsub", methods=["POST"])
def handle_coinsub_webhook():
    """
    Handle webhooks from Coinsub.
    
    Coinsub sends webhooks for various payment events:
    - payment.created: Payment initiated
    - payment.processing: Payment being processed on-chain
    - payment.completed: Payment successful
    - payment.failed: Payment failed
    - session.expired: Purchase session expired
    
    Note: Signature verification is disabled for development.
    Respond quickly (< 5 seconds) and do heavy processing asynchronously.
    """
    log_print("=" * 80)
    log_print("🔔 WEBHOOK RECEIVED")
    log_print(f"   Method: {request.method}")
    log_print(f"   URL: {request.url}")
    log_print(f"   Headers: {dict(request.headers)}")
    log_print(f"   Content-Type: {request.content_type}")
    log_print(f"   Content-Length: {request.content_length}")
    log_print("=" * 80)
    
    try:
        # Log raw data for debugging
        raw_data = request.get_data()
        log_print(f"📦 Raw webhook data: {raw_data[:500]}")  # First 500 chars
        
        # Note: Signature verification disabled for development
        # In production, you should verify webhook signatures for security
        signature = request.headers.get("X-Coinsub-Signature", "")
        if signature:
            log_print(f"🔐 Signature header present: {signature[:50]}... (not verified)")
        else:
            log_print("⚠️  No signature header present")
        
        # Parse JSON
        try:
            event = request.get_json()
            log_print(f"✅ Parsed JSON successfully")
            log_print("=" * 80)
            log_print("📦 FULL WEBHOOK PAYLOAD:")
            log_print("=" * 80)
            log_print(json.dumps(event, indent=2))
            log_print("=" * 80)
        except Exception as json_error:
            log_print(f"❌ Failed to parse JSON: {json_error}")
            log_print(f"   Raw data: {raw_data}")
            return jsonify({"error": "Invalid JSON", "details": str(json_error)}), 400
        
        if not event:
            log_print("❌ Event is None or empty")
            return jsonify({"error": "Empty event data"}), 400
        
        event_type = event.get("type")
        # Coinsub webhooks can have data nested in "data" field OR be flat at root level
        event_data = event.get("data", event)
        event_status = event.get("status")
        
        log_print(f"📋 Event Type: {event_type}")
        log_print(f"📋 Event Status: {event_status}")
        log_print(f"📋 Event Data: {json.dumps(event_data, indent=2)}")
        
        if not event_type:
            log_print("❌ Missing event type")
            return jsonify({"error": "Missing event type"}), 400
        
        # Handle different event types
        log_print(f"🔄 Processing event: {event_type}")
        
        # Handle "payment" event type (check status field)
        if event_type == "payment":
            if event_status == "completed":
                log_print("✅ Payment status is 'completed', handling as payment.completed")
                handle_payment_completed(event_data)
            elif event_status == "failed":
                log_print("❌ Payment status is 'failed', handling as payment.failed")
                handle_payment_failed(event_data)
            elif event_status == "processing":
                log_print("⏳ Payment status is 'processing', handling as payment.processing")
                handle_payment_processing(event_data)
            else:
                log_print(f"⚠️  Unknown payment status: {event_status}")
        # Handle legacy event types (for backwards compatibility)
        elif event_type == "payment.completed":
            handle_payment_completed(event_data)
        elif event_type == "payment.failed":
            handle_payment_failed(event_data)
        elif event_type == "session.expired":
            handle_session_expired(event_data)
        elif event_type == "payment.processing":
            handle_payment_processing(event_data)
        else:
            log_print(f"⚠️  Unhandled webhook type: {event_type}")
            app.logger.info(f"Unhandled webhook type: {event_type}")
        
        log_print("✅ Webhook processed successfully")
        # Always return 200 quickly to acknowledge receipt
        return jsonify({"received": True, "event_type": event_type})
        
    except Exception as e:
        import traceback
        log_print("=" * 80)
        log_print(f"❌❌❌ WEBHOOK ERROR ❌❌❌")
        log_print(f"   Error: {str(e)}")
        log_print(f"   Type: {type(e).__name__}")
        log_print(f"   Traceback:")
        log_print(traceback.format_exc())
        log_print("=" * 80)
        app.logger.error(f"Webhook error: {str(e)}", exc_info=True)
        # Still return 200 to prevent retries for parsing errors
        return jsonify({"received": True, "error": str(e)}), 200


def handle_payment_completed(data: dict):
    """Handle successful payment completion."""
    # Extract data from webhook - handle nested transaction_details
    transaction_details = data.get("transaction_details", {})
    transaction_hash = transaction_details.get("transaction_hash") or data.get("transaction_hash")
    chain_id = transaction_details.get("chain_id") or data.get("chain_id")
    
    # Try to find session_id from origin_id (Coinsub uses origin_id for purchase sessions)
    # or session_id field (for backwards compatibility)
    session_id = data.get("origin_id") or data.get("session_id")
    payment_id = data.get("payment_id")
    
    log_print("=" * 80)
    log_print(f"✅ PAYMENT COMPLETED WEBHOOK RECEIVED")
    log_print(f"   Payment ID: {payment_id}")
    log_print(f"   Session ID: {session_id}")
    log_print(f"   Transaction Hash: {transaction_hash}")
    log_print(f"   Chain ID: {chain_id}")
    log_print(f"   Amount: {data.get('amount')} {data.get('currency', 'USDC')}")
    log_print(f"   Full Webhook Data: {json.dumps(data, indent=2)}")
    
    # Log SSE client status
    with sse_lock:
        log_print(f"   Active SSE sessions: {list(sse_clients.keys())}")
        for sid, clients in sse_clients.items():
            log_print(f"   Session {sid}: {len(clients)} client(s)")
    log_print("=" * 80)
    
    app.logger.info(f"Payment completed: {payment_id}")
    
    # Update ALL sessions - webhook might not have session_id, so update any session that matches
    # This ensures the transaction hash is available for the current user's session
    updated_any = False
    for sid, session_info in purchase_sessions.items():
        # Update if session_id matches, or if this session doesn't have a payment_id yet
        # (meaning it's likely the current active session)
        if (session_id and sid == session_id) or (not session_info.get("payment_id") and not updated_any):
            purchase_sessions[sid]["status"] = "completed"
            purchase_sessions[sid]["payment_id"] = payment_id
            purchase_sessions[sid]["transaction_hash"] = transaction_hash
            purchase_sessions[sid]["chain_id"] = chain_id
            log_print(f"✅ Updated session {sid} with payment info")
            updated_any = True
            # If we matched by session_id, we're done
            if session_id and sid == session_id:
                break
    
    # Store completed payment
    if payment_id and transaction_hash:
        completed_payments[payment_id] = {
            "payment_id": payment_id,
            "session_id": session_id,
            "amount": data.get("amount"),
            "currency": data.get("currency", "USDC"),
            "transaction_hash": transaction_hash,
            "chain_id": chain_id,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        log_print(f"✅ Payment stored: {payment_id}")
        log_print(f"   Transaction Hash: {transaction_hash}")
        log_print(f"   Chain ID: {chain_id}")
        log_print(f"   Explorer URL will be generated based on chain_id")
        log_print(f"   Total completed payments: {len(completed_payments)}")
    
    # Push transaction hash to SSE clients
    if transaction_hash:
        with sse_lock:
            event_data = {
                "type": "payment.completed",
                "session_id": session_id,
                "payment_id": payment_id,
                "transaction_hash": transaction_hash,
                "chain_id": chain_id,
                "amount": data.get("amount"),
                "currency": data.get("currency", "USDC")
            }
            
            # If we have a session_id, try to push to that specific session's clients
            if session_id and session_id in sse_clients:
                log_print(f"📤 Pushing to SSE clients for session {session_id}")
                for client_queue in sse_clients[session_id]:
                    try:
                        client_queue.put(event_data)
                        log_print(f"✅ Pushed transaction hash to SSE client for session {session_id}")
                    except Exception as e:
                        log_print(f"❌ Failed to push to SSE client: {e}")
            else:
                # If no session_id or session_id not found, push to ALL active SSE clients
                # This handles cases where webhook doesn't include session_id
                log_print(f"⚠️  Session ID '{session_id}' not found in SSE clients, pushing to ALL active clients")
                log_print(f"   Active SSE sessions: {list(sse_clients.keys())}")
                pushed_count = 0
                for sid, client_list in sse_clients.items():
                    # Update event_data with the correct session_id for each client
                    event_data["session_id"] = sid
                    for client_queue in client_list:
                        try:
                            client_queue.put(event_data)
                            pushed_count += 1
                            log_print(f"✅ Pushed transaction hash to SSE client for session {sid}")
                        except Exception as e:
                            log_print(f"❌ Failed to push to SSE client for session {sid}: {e}")
                if pushed_count > 0:
                    log_print(f"📤 Pushed transaction hash to {pushed_count} SSE client(s)")
                else:
                    log_print(f"⚠️  No SSE clients found to push to")
    
    log_print("=" * 80)
    
    # TODO: Fulfill the order in your system
    # - Send confirmation email
    # - Grant access to purchased items
    # - Update order status in database
    # - etc.


def handle_payment_failed(data: dict):
    """Handle failed payment."""
    session_id = data.get("origin_id") or data.get("session_id")
    reason = data.get("reason")
    
    app.logger.warning(f"Payment failed for session {session_id}: {reason}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "failed"
        purchase_sessions[session_id]["failure_reason"] = reason
    
    # TODO: Notify customer of failed payment


def handle_session_expired(data: dict):
    """Handle expired purchase session."""
    session_id = data.get("origin_id") or data.get("session_id")
    
    app.logger.info(f"Session expired: {session_id}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "expired"


def handle_payment_processing(data: dict):
    """Handle payment processing notification."""
    session_id = data.get("origin_id") or data.get("session_id")
    
    app.logger.info(f"Payment processing for session {session_id}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "processing"


# =============================================================================
# Demo/Debug Endpoints (Remove in production)
# =============================================================================

@app.route("/api/payments", methods=["GET"])
def list_completed_payments():
    """List all completed payments."""
    log_print("=" * 80)
    log_print("📋 GET PAYMENTS REQUEST")
    log_print(f"   Total payments in memory: {len(completed_payments)}")
    if completed_payments:
        log_print(f"   Payment IDs: {list(completed_payments.keys())}")
        for pid, pdata in completed_payments.items():
            log_print(f"   Payment {pid}: {json.dumps(pdata, indent=2)}")
    log_print("=" * 80)
    
    # Convert dict to list and sort by completion date (newest first)
    payments_list = [
        {
            "payment_id": payment_id,
            **payment_data
        }
        for payment_id, payment_data in completed_payments.items()
    ]
    # Sort by completed_at descending
    payments_list.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    
    log_print(f"✅ Returning {len(payments_list)} payment(s)")
    
    return jsonify({
        "success": True,
        "payments": payments_list,
        "count": len(payments_list)
    })

@app.route("/api/demo/sessions", methods=["GET"])
def list_sessions():
    """List all purchase sessions (demo only)."""
    return jsonify({
        "sessions": purchase_sessions,
        "completed_payments": completed_payments
    })


@app.route("/api/demo/clear", methods=["POST"])
def clear_sessions():
    """Clear all sessions (demo only)."""
    purchase_sessions.clear()
    completed_payments.clear()
    return jsonify({"success": True})


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║          Coinsub Integration Example - Flask Backend          ║
╠═══════════════════════════════════════════════════════════════╣
║  Environment: {COINSUB_ENV:^10}                                     ║
║  API URL: {COINSUB_BASE_URL:^45}  ║
║  Port: {port:^5}                                                ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    if COINSUB_API_KEY == "your-api-key-here":
        print("⚠️  WARNING: Using default API key. Set COINSUB_API_KEY in .env")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
