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

# Configure logging
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app.logger.setLevel(logging.INFO)

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
    return headers


# =============================================================================
# API Routes - Purchase Session Flow
# =============================================================================

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def root():
    """Root endpoint - catches misconfigured webhooks."""
    if request.method == "POST":
        app.logger.warning("POST request received at root (/) endpoint - might be misconfigured webhook")
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
    return jsonify({
        "status": "healthy",
        "environment": COINSUB_ENV,
        "api_url": COINSUB_BASE_URL,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.errorhandler(Exception)
def handle_exception(e):
    """Log all exceptions."""
    import traceback
    app.logger.error(f"Exception: {type(e).__name__}: {str(e)}", exc_info=True)
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
    try:
        data = request.get_json()
        
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
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/session/start"
        
        response = requests.post(
            api_endpoint,
            headers=get_coinsub_headers(),
            json=session_payload,
            timeout=30
        )
        
        if response.status_code == 201 or response.status_code == 200:
            response_json = response.json()
            
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
                app.logger.error("Could not extract session_id from Coinsub response")
                return jsonify({"error": "Failed to extract session ID from Coinsub response"}), 500
            
            app.logger.info(f"Purchase session created: {session_id}")
            
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
            
            app.logger.error(f"Coinsub API error creating session (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to create purchase session",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except requests.RequestException as e:
        app.logger.error(f"Network error creating session: {str(e)}", exc_info=True)
        return jsonify({"error": "Network error connecting to Coinsub"}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error creating session: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/session/<session_id>/events", methods=["GET"])
def stream_session_events(session_id):
    """
    Server-Sent Events (SSE) endpoint for real-time payment updates.
    Frontend connects here and receives transaction hash when webhook arrives.
    """
    def event_stream():
        # Create a message queue for this client
        message_queue = queue.Queue()
        
        # Register this client
        with sse_lock:
            if session_id not in sse_clients:
                sse_clients[session_id] = []
            sse_clients[session_id].append(message_queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Check if transaction hash is already available (webhook arrived before SSE connection)
            hash_already_sent = False
            if session_id in purchase_sessions:
                session_info = purchase_sessions[session_id]
                if session_info.get("transaction_hash"):
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
            app.logger.debug(f"SSE client disconnected for session {session_id}")
        finally:
            # Unregister this client
            with sse_lock:
                if session_id in sse_clients:
                    try:
                        sse_clients[session_id].remove(message_queue)
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
    try:
        # First check local session storage (updated by webhooks)
        if session_id in purchase_sessions:
            session_info = purchase_sessions[session_id]
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
        response = requests.get(
            f"{COINSUB_BASE_URL}/purchase-sessions/{session_id}",
            headers=get_coinsub_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            coinsub_data = response.json()
            return jsonify(coinsub_data)
        else:
            return jsonify({
                "error": "Session not found",
                "details": response.json() if response.text else None
            }), 404
            
    except Exception as e:
        app.logger.error(f"Error fetching session status: {str(e)}", exc_info=True)
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
    try:
        data = request.get_json()
        
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
        
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/message/request"
        
        response = requests.post(
            api_endpoint,
            headers=get_coinsub_headers(),
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            response_json = response.json()
            
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
            
            if not primary_type:
                app.logger.error("Missing primary_type in Coinsub API response")
                return jsonify({"error": "Invalid response from Coinsub API: missing primary_type"}), 500
            
            if not domain or not types or not message:
                app.logger.error("Missing required typed data fields in Coinsub API response")
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
            
            app.logger.error(f"Coinsub API error requesting message (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to request purchase message",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error requesting purchase message: {str(e)}", exc_info=True)
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
    try:
        data = request.get_json()
        
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
        
        api_endpoint = f"{COINSUB_BASE_URL}/v1/purchase/message/sign"
        
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
            
            app.logger.info(f"Signature submitted successfully for session {session_id}")
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
            
            app.logger.error(f"Coinsub API error submitting signature (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to submit signed message",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error submitting signed message: {str(e)}", exc_info=True)
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
    
    Note: Signature verification is disabled in this demo for simplicity.
    In production, you should verify webhook signatures for security.
    """
    if not COINSUB_WEBHOOK_SECRET:
        app.logger.warning("Webhook secret not configured - skipping signature verification")
        return True
    
    if not signature:
        return False
    
    # Extract signature value (may have prefix like "sha256=...")
    signature_value = signature.split('=', 1)[1] if '=' in signature else signature
    
    # Calculate expected signature
    expected_signature = hmac.new(
        COINSUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(signature_value, expected_signature)
    
    if not is_valid:
        app.logger.warning("Webhook signature verification failed")
    
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
    try:
        event = request.get_json()
        
        if not event:
            app.logger.warning("Empty webhook event received")
            return jsonify({"error": "Empty event data"}), 400
        
        event_type = event.get("type")
        # Coinsub webhooks can have data nested in "data" field OR be flat at root level
        event_data = event.get("data", event)
        event_status = event.get("status")
        
        if not event_type:
            app.logger.warning("Webhook missing event type")
            return jsonify({"error": "Missing event type"}), 400
        
        app.logger.info(f"Webhook received: {event_type} (status: {event_status})")
        
        # Handle "payment" event type (check status field)
        if event_type == "payment":
            if event_status == "completed":
                handle_payment_completed(event_data)
            elif event_status == "failed":
                handle_payment_failed(event_data)
            elif event_status == "processing":
                handle_payment_processing(event_data)
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
            app.logger.info(f"Unhandled webhook type: {event_type}")
        
        # Always return 200 quickly to acknowledge receipt
        return jsonify({"received": True, "event_type": event_type})
        
    except Exception as e:
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
    
    app.logger.info(f"Payment completed: {payment_id} (session: {session_id}, tx: {transaction_hash})")
    
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
                for client_queue in sse_clients[session_id]:
                    try:
                        client_queue.put(event_data)
                    except Exception as e:
                        app.logger.error(f"Failed to push to SSE client: {e}")
            else:
                # If no session_id or session_id not found, push to ALL active SSE clients
                # This handles cases where webhook doesn't include session_id
                for sid, client_list in sse_clients.items():
                    # Update event_data with the correct session_id for each client
                    event_data["session_id"] = sid
                    for client_queue in client_list:
                        try:
                            client_queue.put(event_data)
                        except Exception as e:
                            app.logger.error(f"Failed to push to SSE client for session {sid}: {e}")
    
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
    
    return jsonify({
        "success": True,
        "payments": payments_list,
        "count": len(payments_list)
    })

# =============================================================================
# Admin Endpoints
# =============================================================================

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """
    Simple admin login endpoint.
    For demo purposes, accepts admin/admin credentials.
    """
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        if username == "admin" and password == "admin":
            return jsonify({
                "success": True,
                "token": "admin_token"  # Simple token for demo
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid credentials"
            }), 401
    except Exception as e:
        app.logger.error(f"Admin login error: {str(e)}", exc_info=True)
        return jsonify({"error": "Login failed"}), 500


@app.route("/api/admin/payments", methods=["POST"])
def admin_get_payments():
    """
    Get all payments from Coinsub API.
    Requires admin authentication (simple token check for demo).
    """
    try:
        # Simple token check (in production, use proper JWT/session)
        auth_header = request.headers.get("Authorization")
        if not auth_header or auth_header != "Bearer admin_token":
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json() or {}
        agreement = data.get("agreement")
        status = data.get("status", "")
        
        # Call Coinsub API to get all payments
        # Note: Coinsub API uses GET with JSON body (non-standard but supported)
        api_endpoint = f"{COINSUB_BASE_URL}/v1/payments/all"
        
        payload = {
            "agreement": agreement,
            "status": status
        }
        
        # Use requests.request() for GET with JSON body (non-standard but required by API)
        headers = get_coinsub_headers()
        response = requests.request(
            method='GET',
            url=api_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Log the full response structure for debugging
            app.logger.info("=== Coinsub API Response Structure ===")
            app.logger.info(f"Response keys: {list(response_data.keys())}")
            app.logger.info(f"Full response (first 2000 chars): {str(response_data)[:2000]}")
            
            # Extract payments from nested data structure: data.data
            data_obj = response_data.get("data", {})
            app.logger.info(f"data_obj type: {type(data_obj)}")
            app.logger.info(f"data_obj keys: {list(data_obj.keys()) if isinstance(data_obj, dict) else 'N/A (not a dict)'}")
            
            if isinstance(data_obj, dict) and "data" in data_obj:
                payments = data_obj["data"]
                app.logger.info(f"Extracted payments from data.data: {len(payments)} payments")
            elif isinstance(data_obj, list):
                payments = data_obj
                app.logger.info(f"Extracted payments from data (list): {len(payments)} payments")
            elif isinstance(data_obj, dict) and "payments" in data_obj:
                payments = data_obj["payments"]
                app.logger.info(f"Extracted payments from data.payments: {len(payments)} payments")
            else:
                payments = []
                app.logger.warning(f"No payments found in response structure")
            
            # Log first payment structure if available
            if payments and len(payments) > 0:
                app.logger.info(f"First payment keys: {list(payments[0].keys())}")
                app.logger.info(f"First payment sample: {str(payments[0])[:500]}")
            
            # Process payments: use the flat structure from API response
            # API returns: payment_id, amount (already in USD value, e.g., 0.0985), status, transaction_date,
            # block_explorer_url, transaction_hash, currency, token_name, network_id
            # Note: amount is already formatted - no need to convert using 10^6 or 10^18
            processed_payments = []
            for idx, payment in enumerate(payments):
                processed_payment = payment.copy()
                
                # Log payment structure for debugging (first payment only)
                if idx == 0:
                    app.logger.info(f"Processing payment {idx}: keys = {list(payment.keys())}")
                
                # Map fields to expected frontend format
                # payment_id -> id (for frontend compatibility)
                if "payment_id" in payment:
                    processed_payment["id"] = payment["payment_id"]
                
                # amount is already in USD value (e.g., 0.0985) - no conversion needed
                # currency and token_name are already present
                processed_payment["display_amount"] = payment.get("amount", 0)
                processed_payment["token_symbol"] = payment.get("currency") or payment.get("token_name", "USDC")
                
                # block_explorer_url -> confirmation_url (for frontend compatibility)
                if "block_explorer_url" in payment:
                    processed_payment["confirmation_url"] = payment["block_explorer_url"]
                
                # transaction_hash -> txhash (for frontend compatibility)
                if "transaction_hash" in payment:
                    processed_payment["txhash"] = payment["transaction_hash"]
                
                # network_id -> chain_id (for frontend compatibility)
                if "network_id" in payment:
                    processed_payment["chain_id"] = payment["network_id"]
                
                # transaction_date -> payment_date (for frontend compatibility)
                if "transaction_date" in payment:
                    processed_payment["payment_date"] = payment["transaction_date"]
                
                if idx == 0:
                    app.logger.info(f"Processed payment - id: {processed_payment.get('id')}, amount: {processed_payment.get('display_amount')}, token: {processed_payment.get('token_symbol')}, confirmation_url: {processed_payment.get('confirmation_url')}")
                
                processed_payments.append(processed_payment)
            
            # Sort by transaction_date descending (newest first)
            processed_payments.sort(
                key=lambda x: x.get("transaction_date") or x.get("payment_date") or "",
                reverse=True
            )
            
            return jsonify({
                "success": True,
                "payments": processed_payments,
                "count": len(processed_payments)
            })
        else:
            error_details = None
            try:
                error_details = response.json() if response.text else None
            except:
                error_details = response.text
            
            app.logger.error(f"Coinsub API error getting payments (status {response.status_code}): {error_details}")
            
            return jsonify({
                "error": "Failed to fetch payments",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except requests.RequestException as e:
        app.logger.error(f"Network error fetching payments: {str(e)}", exc_info=True)
        return jsonify({"error": "Network error connecting to Coinsub"}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error fetching payments: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# Demo Endpoints
# =============================================================================

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
