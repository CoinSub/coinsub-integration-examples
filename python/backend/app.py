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
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# =============================================================================
# Configuration
# =============================================================================

COINSUB_API_KEY = os.getenv("COINSUB_API_KEY", "your-api-key-here")
# Webhook secret is optional for local dev (Coinsub can't reach localhost anyway)
# Required for production - get this from your Coinsub dashboard when configuring webhooks
COINSUB_WEBHOOK_SECRET = os.getenv("COINSUB_WEBHOOK_SECRET", "")

# Use test environment for development, production for live
COINSUB_ENV = os.getenv("COINSUB_ENV", "test")
COINSUB_BASE_URL = (
    "https://test.coinsub.io/api" if COINSUB_ENV == "test" 
    else "https://app.coinsub.io/api"
)

# In-memory storage for demo purposes (use a real database in production)
purchase_sessions = {}
completed_payments = {}


def get_coinsub_headers():
    """Generate headers for Coinsub API requests."""
    return {
        "Authorization": f"Bearer {COINSUB_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


# =============================================================================
# API Routes - Purchase Session Flow
# =============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "environment": COINSUB_ENV,
        "timestamp": datetime.utcnow().isoformat()
    })


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
        session_payload = {
            "amount": total_amount,
            "currency": data.get("currency", "USD"),
            "description": f"Purchase of {len(data['items'])} item(s)",
            "metadata": {
                "items": data["items"],
                "customer_email": data.get("customer_email"),
                **(data.get("metadata", {}))
            },
            # Optional: specify success/cancel URLs for hosted checkout
            "success_url": data.get("success_url"),
            "cancel_url": data.get("cancel_url")
        }
        
        # Create purchase session via Coinsub API
        response = requests.post(
            f"{COINSUB_BASE_URL}/purchase-sessions",
            headers=get_coinsub_headers(),
            json=session_payload,
            timeout=30
        )
        
        if response.status_code == 201 or response.status_code == 200:
            session_data = response.json()
            session_id = session_data.get("id") or session_data.get("session_id")
            
            # Store session locally for tracking
            purchase_sessions[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "amount": total_amount,
                "currency": data.get("currency", "USD"),
                "items": data["items"],
                "status": "created",
                "coinsub_data": session_data
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
            app.logger.error(f"Coinsub API error: {response.text}")
            return jsonify({
                "error": "Failed to create purchase session",
                "details": response.json() if response.text else None
            }), response.status_code
            
    except requests.RequestException as e:
        app.logger.error(f"Network error: {str(e)}")
        return jsonify({"error": "Network error connecting to Coinsub"}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/session/<session_id>/status", methods=["GET"])
def get_session_status(session_id):
    """
    Get the status of a purchase session.
    
    Possible statuses:
    - created: Session was just created
    - pending: Waiting for payment
    - processing: Payment is being processed
    - completed: Payment successful
    - expired: Session expired
    - cancelled: Session was cancelled
    """
    try:
        response = requests.get(
            f"{COINSUB_BASE_URL}/purchase-sessions/{session_id}",
            headers=get_coinsub_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "error": "Failed to get session status",
                "details": response.json() if response.text else None
            }), response.status_code
            
    except Exception as e:
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
    try:
        data = request.get_json()
        
        if not data or "wallet_address" not in data:
            return jsonify({"error": "Missing wallet address"}), 400
        
        # Request purchase message from Coinsub
        payload = {
            "session_id": session_id,
            "wallet_address": data["wallet_address"],
            "chain_id": data.get("chain_id", 1)  # Default to Ethereum mainnet
        }
        
        response = requests.post(
            f"{COINSUB_BASE_URL}/purchase-messages/request",
            headers=get_coinsub_headers(),
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200 or response.status_code == 201:
            message_data = response.json()
            return jsonify({
                "success": True,
                "message": message_data.get("message"),
                "typed_data": message_data.get("typed_data"),
                "domain": message_data.get("domain"),
                "types": message_data.get("types"),
                "primary_type": message_data.get("primary_type"),
                "message_id": message_data.get("message_id")
            })
        else:
            return jsonify({
                "error": "Failed to request purchase message",
                "details": response.json() if response.text else None
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error requesting purchase message: {str(e)}")
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
        
        # Submit signed message to Coinsub
        payload = {
            "session_id": session_id,
            "signature": data["signature"],
            "wallet_address": data["wallet_address"],
            "message_id": data.get("message_id")
        }
        
        response = requests.post(
            f"{COINSUB_BASE_URL}/purchase-messages/submit",
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
            return jsonify({
                "error": "Failed to submit signed message",
                "details": response.json() if response.text else None
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Error submitting signed message: {str(e)}")
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
    1. Use ngrok or similar: ngrok http 5000
    2. Configure the ngrok URL as your webhook endpoint in Coinsub dashboard
    3. Copy the webhook secret to your .env file
    """
    if not COINSUB_WEBHOOK_SECRET:
        app.logger.warning(
            "Webhook secret not configured! "
            "Skipping signature verification (OK for development without webhooks)"
        )
        # In development without webhooks configured, skip verification
        # In production, you should ALWAYS have a webhook secret set
        return True
    
    expected_signature = hmac.new(
        COINSUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


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
    
    Always verify the webhook signature and respond quickly (< 5 seconds).
    Do heavy processing asynchronously.
    """
    try:
        # Get the signature from headers
        signature = request.headers.get("X-Coinsub-Signature", "")
        
        # Verify signature
        if not verify_webhook_signature(request.data, signature):
            app.logger.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 401
        
        event = request.get_json()
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        app.logger.info(f"Received webhook: {event_type}")
        
        # Handle different event types
        if event_type == "payment.completed":
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
        return jsonify({"received": True})
        
    except Exception as e:
        app.logger.error(f"Webhook error: {str(e)}")
        # Still return 200 to prevent retries for parsing errors
        return jsonify({"received": True, "error": str(e)}), 200


def handle_payment_completed(data: dict):
    """Handle successful payment completion."""
    session_id = data.get("session_id")
    payment_id = data.get("payment_id")
    
    app.logger.info(f"Payment completed for session {session_id}")
    
    # Update local storage
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "completed"
        purchase_sessions[session_id]["payment_id"] = payment_id
    
    # Store completed payment
    completed_payments[payment_id] = {
        "session_id": session_id,
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "wallet_address": data.get("wallet_address"),
        "transaction_hash": data.get("transaction_hash"),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    # TODO: Fulfill the order in your system
    # - Send confirmation email
    # - Grant access to purchased items
    # - Update order status in database
    # - etc.


def handle_payment_failed(data: dict):
    """Handle failed payment."""
    session_id = data.get("session_id")
    reason = data.get("reason")
    
    app.logger.warning(f"Payment failed for session {session_id}: {reason}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "failed"
        purchase_sessions[session_id]["failure_reason"] = reason
    
    # TODO: Notify customer of failed payment


def handle_session_expired(data: dict):
    """Handle expired purchase session."""
    session_id = data.get("session_id")
    
    app.logger.info(f"Session expired: {session_id}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "expired"


def handle_payment_processing(data: dict):
    """Handle payment processing notification."""
    session_id = data.get("session_id")
    
    app.logger.info(f"Payment processing for session {session_id}")
    
    if session_id in purchase_sessions:
        purchase_sessions[session_id]["status"] = "processing"


# =============================================================================
# Demo/Debug Endpoints (Remove in production)
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
