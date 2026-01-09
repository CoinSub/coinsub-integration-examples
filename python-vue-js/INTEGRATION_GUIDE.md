# Coinsub Integration Guide

This guide walks you through integrating Coinsub cryptocurrency payments into your application using the **Purchase Session** flow with **WalletConnect** for wallet linking.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Backend Implementation](#backend-implementation)
3. [Frontend Implementation](#frontend-implementation)
4. [Wallet Integration](#wallet-integration)
5. [Message Signing (EIP-712)](#message-signing-eip-712)
6. [Webhook Handling](#webhook-handling)
7. [Admin Dashboard](#admin-dashboard)
8. [Error Handling](#error-handling)
9. [Security Best Practices](#security-best-practices)
10. [Testing](#testing)

---

## Architecture Overview

### The Purchase Session Flow

Unlike product-based integrations where you pre-register products in Coinsub, **Purchase Sessions** allow you to create ad-hoc payment requests. This is ideal when:

- You have a large product catalog
- Products are dynamically priced
- You want to support custom product combinations
- You need maximum flexibility in your checkout flow

### System Components

```
┌──────────────────────────────────────────────────────────────────┐
│                         YOUR SYSTEM                               │
├─────────────────────────┬────────────────────────────────────────┤
│                         │                                         │
│  ┌─────────────────┐    │    ┌─────────────────────────────┐     │
│  │    Frontend     │    │    │         Backend             │     │
│  │    (Vue.js)     │────│────│         (Flask)             │     │
│  │                 │    │    │                             │     │
│  │  • Shopping UI  │    │    │  • API Proxy                │     │
│  │  • Wallet UI    │    │    │  • Session Management       │     │
│  │  • Checkout     │    │    │  • Webhook Handler          │     │
│  │                 │    │    │  • Order Fulfillment        │     │
│  └────────┬────────┘    │    └─────────────┬───────────────┘     │
│           │             │                   │                     │
└───────────│─────────────┴───────────────────│─────────────────────┘
            │                                 │
            │  WalletConnect                  │  HTTPS
            │                                 │
            ▼                                 ▼
    ┌───────────────┐               ┌─────────────────┐
    │    User's     │               │    Coinsub      │
    │    Wallet     │               │      API        │
    │   (MetaMask,  │               │                 │
    │   Rainbow,    │               │ test.coinsub.io │
    │   etc.)       │               │ app.coinsub.io  │
    └───────────────┘               └─────────────────┘
```

---

## Backend Implementation

### 1. Setting Up Flask

```python
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

COINSUB_API_KEY = os.getenv("COINSUB_API_KEY")
COINSUB_MERCHANT_ID = os.getenv("COINSUB_MERCHANT_ID")
COINSUB_ENV = os.getenv("COINSUB_ENV", "test")
COINSUB_BASE_URL = (
    "https://test-api.coinsub.io" if COINSUB_ENV == "test" 
    else "https://api.coinsub.io"
)
```

### 2. Creating a Purchase Session

When the user clicks "Checkout", create a session with their cart data:

```python
@app.route("/api/create-session", methods=["POST"])
def create_purchase_session():
    data = request.get_json()
    
    # Calculate total from cart items
    total = sum(
        item["price"] * item["quantity"] 
        for item in data["items"]
    )
    
    # Create session with Coinsub
    response = requests.post(
        f"{COINSUB_BASE_URL}/v1/purchase/session/start",
        headers={
            "Merchant-ID": COINSUB_MERCHANT_ID,
            "API-Key": COINSUB_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "name": f"Order with {len(data['items'])} items",
            "details": f"Order with {len(data['items'])} items",
            "currency": data.get("currency", "USDC"),
            "amount": total,
            "recurring": False,
            "metadata": {
                "items": data["items"],
                "customer_email": data.get("customer_email")
            }
        }
    )
    
    if response.ok:
        session = response.json()
        return jsonify({
            "success": True,
            "session_id": session["id"],
            "amount": total
        })
    
    return jsonify({"error": "Failed to create session"}), 500
```

### 3. Requesting Purchase Message

After the user connects their wallet, request the EIP-712 message they need to sign:

```python
@app.route("/api/session/<session_id>/message", methods=["POST"])
def request_message(session_id):
    data = request.get_json()
    
    # Get session data to extract product info
    session_info = purchase_sessions.get(session_id, {})
    items = session_info.get("items", [])
    product_name = ", ".join([item.get("name", "Item") for item in items]) if items else "Purchase"
    price = session_info.get("amount", 0)
    
    response = requests.post(
        f"{COINSUB_BASE_URL}/v1/purchase/message/request",
        headers={
            "Merchant-ID": COINSUB_MERCHANT_ID,
            "API-Key": COINSUB_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "purchase_session_id": session_id,
            "wallet_address": data["wallet_address"],
            "product_name": product_name,
            "price": price,
            "metadata": session_info.get("metadata", {}),
            "token": "USDC",
            "recurring": False,
            "duration": "One-time",
            "frequency": "One-time",
            "interval": "One-time",
            "chainId": data.get("chain_id", 80002)
        }
    )
    
    if response.ok:
        message = response.json()
        return jsonify({
            "success": True,
            "typed_data": message["typed_data"],
            "domain": message["domain"],
            "types": message["types"],
            "primary_type": message["primary_type"],
            "message": message["message"],
            "message_id": message["message_id"]
        })
    
    return jsonify({"error": "Failed to request message"}), 500
```

### 4. Submitting Signed Message

After the user signs in their wallet, submit the signature:

```python
@app.route("/api/session/<session_id>/sign", methods=["POST"])
def submit_signature(session_id):
    data = request.get_json()
    
    response = requests.post(
        f"{COINSUB_BASE_URL}/v1/purchase/message/sign",
        headers={
            "Merchant-ID": COINSUB_MERCHANT_ID,
            "API-Key": COINSUB_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "purchase_session_id": session_id,
            "signed_typed_data": {
                "signature": data["signature"],
                "signing_address": data["wallet_address"],
                "chainId": data.get("chain_id", 80002)
            }
        }
    )
    
    if response.ok:
        result = response.json()
        return jsonify({
            "success": True,
            "status": result["status"],
            "payment_id": result.get("payment_id"),
            "transaction_hash": result.get("transaction_hash")
        })
    
    return jsonify({"error": "Failed to submit signature"}), 500
```

---

## Frontend Implementation

### 1. Cart Store

Manage cart state with Pinia:

```javascript
// stores/cart.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  
  const total = computed(() => 
    items.value.reduce((sum, item) => 
      sum + (item.price * item.quantity), 0
    )
  )
  
  function addItem(product) {
    const existing = items.value.find(i => i.id === product.id)
    if (existing) {
      existing.quantity++
    } else {
      items.value.push({ ...product, quantity: 1 })
    }
  }
  
  function getCartData() {
    return {
      items: items.value,
      currency: 'USD'
    }
  }
  
  return { items, total, addItem, getCartData }
})
```

### 2. Checkout Store

Handle the Coinsub checkout flow:

```javascript
// stores/checkout.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useCheckoutStore = defineStore('checkout', () => {
  const sessionId = ref(null)
  const messageData = ref(null)
  const status = ref('idle')
  const error = ref(null)
  
  async function createSession(cartData) {
    status.value = 'creating'
    try {
      const { data } = await axios.post('/api/create-session', cartData)
      sessionId.value = data.session_id
      status.value = 'created'
      return data
    } catch (e) {
      error.value = e.message
      status.value = 'error'
      throw e
    }
  }
  
  async function requestMessage(walletAddress, chainId) {
    try {
      const { data } = await axios.post(
        `/api/session/${sessionId.value}/message`,
        { wallet_address: walletAddress, chain_id: chainId }
      )
      messageData.value = data
      status.value = 'ready'
      return data
    } catch (e) {
      error.value = e.message
      status.value = 'error'
      throw e
    }
  }
  
  async function submitSignature(signature, walletAddress) {
    status.value = 'processing'
    try {
      const { data } = await axios.post(
        `/api/session/${sessionId.value}/sign`,
        { 
          signature, 
          wallet_address: walletAddress,
          message_id: messageData.value?.message_id
        }
      )
      status.value = 'completed'
      return data
    } catch (e) {
      error.value = e.message
      status.value = 'error'
      throw e
    }
  }
  
  return { 
    sessionId, messageData, status, error,
    createSession, requestMessage, submitSignature 
  }
})
```

---

## Wallet Integration

### Setting Up WalletConnect with Wagmi

```javascript
// stores/wallet.js
import { createWeb3Modal, defaultWagmiConfig } from '@web3modal/wagmi'
import { mainnet, polygon, arbitrum } from 'viem/chains'
import { 
  getAccount, 
  disconnect, 
  signTypedData, 
  watchAccount,
  reconnect 
} from '@wagmi/core'

const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID
const chains = [mainnet, polygon, arbitrum]

const wagmiConfig = defaultWagmiConfig({
  chains,
  projectId,
  metadata: {
    name: 'Your App',
    description: 'Pay with crypto',
    url: window.location.origin,
    icons: [`${window.location.origin}/icon.png`]
  }
})

// Create the modal
const web3Modal = createWeb3Modal({
  wagmiConfig,
  projectId,
  chains,
  themeMode: 'dark'
})
```

### Connecting Wallet

```javascript
async function connect() {
  await web3Modal.open()
}

async function disconnect() {
  await disconnectWagmi(wagmiConfig)
}
```

### Getting Account State

```javascript
// Watch for account changes
watchAccount(wagmiConfig, {
  onChange: (account) => {
    if (account.isConnected) {
      walletAddress.value = account.address
      chainId.value = account.chainId
    } else {
      walletAddress.value = null
      chainId.value = null
    }
  }
})
```

---

## Message Signing (EIP-712)

### What is EIP-712?

EIP-712 is a standard for signing typed structured data. It provides:
- Human-readable signing prompts in wallets
- Protection against signature replay attacks
- Clear display of what the user is authorizing

### Signing the Purchase Message

```javascript
import { signTypedData } from '@wagmi/core'

async function signPurchaseMessage(typedData) {
  const signature = await signTypedData(wagmiConfig, {
    domain: typedData.domain,
    types: typedData.types,
    primaryType: typedData.primaryType,
    message: typedData.message
  })
  
  return signature
}
```

### Complete Checkout Flow

```javascript
async function handlePayment() {
  const cart = cartStore.getCartData()
  const wallet = walletStore
  
  // 1. Create session
  await checkoutStore.createSession(cart)
  
  // 2. Get message to sign
  await checkoutStore.requestMessage(
    wallet.address,
    wallet.chainId
  )
  
  // 3. Sign in wallet
  const signature = await wallet.signMessage({
    domain: checkoutStore.messageData.domain,
    types: checkoutStore.messageData.types,
    primaryType: checkoutStore.messageData.primary_type,
    message: checkoutStore.messageData.message
  })
  
  // 4. Submit signature
  await checkoutStore.submitSignature(signature, wallet.address)
  
  // 5. Success!
  router.push('/success')
}
```

---

## Webhook Handling

### Important: Webhooks and Localhost

Coinsub **cannot** send webhooks to `localhost` - they need a publicly accessible URL. 

**For local development**, you have two options:

1. **Skip webhooks entirely** - The demo works without webhooks. You can check payment status via the API polling instead.

2. **Use ngrok for webhook testing**:
   ```bash
   # Install ngrok from https://ngrok.com
   ngrok http 5000
   
   # You'll get a URL like: https://abc123.ngrok.io
   # Set your webhook URL in Coinsub dashboard to:
   # https://abc123.ngrok.io/api/webhooks/coinsub
   ```

The **webhook secret** is used to verify that incoming webhooks are genuinely from Coinsub. This prevents attackers from sending fake payment confirmations to your server.

### Setting Up Webhook Endpoint

```python
import hmac
import hashlib

WEBHOOK_SECRET = os.getenv("COINSUB_WEBHOOK_SECRET")

@app.route("/api/webhooks/coinsub", methods=["POST"])
def handle_webhook():
    # Verify signature
    signature = request.headers.get("X-Coinsub-Signature", "")
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        request.data,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected):
        return jsonify({"error": "Invalid signature"}), 401
    
    event = request.get_json()
    event_type = event.get("type")
    event_status = event.get("status")
    # Coinsub webhooks can have data nested in "data" field OR be flat at root level
    event_data = event.get("data", event)
    
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
    
    return jsonify({"received": True})
```

### Handling Payment Completion

```python
def handle_payment_completed(data):
    # Extract session_id from origin_id (Coinsub uses origin_id for purchase sessions)
    session_id = data.get("origin_id") or data.get("session_id")
    payment_id = data.get("payment_id")
    
    # Extract transaction details
    transaction_details = data.get("transaction_details", {})
    transaction_hash = transaction_details.get("transaction_hash")
    chain_id = transaction_details.get("chain_id")
    
    # 1. Find the order
    order = Order.query.filter_by(
        coinsub_session_id=session_id
    ).first()
    
    if not order:
        app.logger.error(f"Order not found for session {session_id}")
        return
    
    # 2. Update order status
    order.status = "paid"
    order.payment_id = payment_id
    order.transaction_hash = transaction_hash
    order.chain_id = chain_id
    order.paid_at = datetime.utcnow()
    db.session.commit()
    
    # 3. Fulfill the order
    if order.type == "digital":
        grant_access(order.customer_id, order.products)
    elif order.type == "physical":
        create_shipping_label(order)
    
    # 4. Notify customer
    send_confirmation_email(order)
    
    # 5. Push transaction hash to SSE clients (if using SSE for real-time updates)
    # See SSE implementation in the main README
```

---

## Admin Dashboard

### Overview

The admin dashboard allows merchants to view their payment history directly from the Coinsub API. This is useful for:
- Reviewing all transactions
- Filtering payments by status
- Viewing transaction hashes and blockchain explorer links
- Monitoring payment activity

### Backend Implementation

#### 1. Admin Login Endpoint

```python
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """
    Simple admin login endpoint.
    For demo purposes, accepts admin/admin credentials.
    In production, use proper authentication (JWT, OAuth, etc.)
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if username == "admin" and password == "admin":
        # In production, generate a proper JWT token
        return jsonify({
            "success": True,
            "token": "admin_token"  # Replace with JWT in production
        })
    else:
        return jsonify({
            "success": False,
            "error": "Invalid credentials"
        }), 401
```

#### 2. Get Payments Endpoint

```python
@app.route("/api/admin/payments", methods=["POST"])
def admin_get_payments():
    """
    Get all payments from Coinsub API.
    Requires admin authentication.
    """
    # Verify authentication token
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != "Bearer admin_token":
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json() or {}
    agreement = data.get("agreement")
    status = data.get("status", "")
    
    # Call Coinsub API
    api_endpoint = f"{COINSUB_BASE_URL}/v1/payments/all"
    
    payload = {
        "agreement": agreement,
        "status": status
    }
    
    # Note: Coinsub API uses GET with JSON body (non-standard)
    response = requests.request(
        method='GET',
        url=api_endpoint,
        headers={
            "Merchant-ID": COINSUB_MERCHANT_ID,
            "API-Key": COINSUB_API_KEY,
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        response_data = response.json()
        
        # Extract payments from nested data structure: data.data
        data_obj = response_data.get("data", {})
        if isinstance(data_obj, dict) and "data" in data_obj:
            payments = data_obj["data"]
        elif isinstance(data_obj, list):
            payments = data_obj
        else:
            payments = []
        
        # Process payments: map fields for frontend compatibility
        # API returns: payment_id, amount (already in USD), status, transaction_date,
        # block_explorer_url, transaction_hash, currency, token_name, network_id
        processed_payments = []
        for payment in payments:
            processed_payment = payment.copy()
            
            # Map fields to expected frontend format
            if "payment_id" in payment:
                processed_payment["id"] = payment["payment_id"]
            if "block_explorer_url" in payment:
                processed_payment["confirmation_url"] = payment["block_explorer_url"]
            if "transaction_hash" in payment:
                processed_payment["txhash"] = payment["transaction_hash"]
            if "network_id" in payment:
                processed_payment["chain_id"] = payment["network_id"]
            if "transaction_date" in payment:
                processed_payment["payment_date"] = payment["transaction_date"]
            
            # amount is already in USD value (e.g., 0.0985) - no conversion needed
            processed_payment["display_amount"] = payment.get("amount", 0)
            processed_payment["token_symbol"] = payment.get("currency") or payment.get("token_name", "USDC")
            
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
        return jsonify({
            "error": "Failed to fetch payments",
            "status_code": response.status_code
        }), response.status_code
```

### Frontend Implementation

#### 1. Admin Login Component

```vue
<!-- views/AdminLoginView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center">
    <form @submit.prevent="handleLogin">
      <input v-model="username" type="text" placeholder="Username" />
      <input v-model="password" type="password" placeholder="Password" />
      <button type="submit" :disabled="loading">
        {{ loading ? 'Logging in...' : 'Sign in' }}
      </button>
      <div v-if="error" class="error">{{ error }}</div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await axios.post('/api/admin/login', {
      username: username.value,
      password: password.value
    })
    
    if (response.data.success) {
      // Store token in sessionStorage
      sessionStorage.setItem('admin_token', response.data.token)
      router.push('/admin/dashboard')
    } else {
      error.value = response.data.error || 'Login failed'
    }
  } catch (err) {
    error.value = err.response?.data?.error || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>
```

#### 2. Admin Dashboard Component

```vue
<!-- views/AdminDashboardView.vue -->
<template>
  <div>
    <h1>Payment History</h1>
    
    <!-- Filters -->
    <div>
      <select v-model="filters.status" @change="fetchPayments">
        <option value="">All</option>
        <option value="completed">Completed</option>
        <option value="pending">Pending</option>
        <option value="failed">Failed</option>
      </select>
      <button @click="fetchPayments" :disabled="loading">
        {{ loading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>
    
    <!-- Payments Table -->
    <table>
      <thead>
        <tr>
          <th>Payment ID</th>
          <th>Amount</th>
          <th>Status</th>
          <th>Date</th>
          <th>Transaction</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="payment in payments" :key="payment.id || payment.payment_id">
          <td>{{ payment.id || payment.payment_id }}</td>
          <td>
            <span v-if="payment.display_amount !== undefined">
              {{ formatAmount(payment.display_amount) }} {{ payment.token_symbol || payment.currency || 'USDC' }}
            </span>
            <span v-else>
              {{ payment.amount }} {{ payment.currency || 'USDC' }}
            </span>
          </td>
          <td>
            <span :class="`status-${payment.status}`">
              {{ payment.status }}
            </span>
          </td>
          <td>{{ formatDate(payment.transaction_date || payment.payment_date) }}</td>
          <td>
            <a 
              v-if="payment.confirmation_url || payment.block_explorer_url"
              :href="payment.confirmation_url || payment.block_explorer_url"
              target="_blank"
            >
              {{ truncateHash(payment.txhash || payment.transaction_hash) }}
            </a>
            <span v-else>-</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const payments = ref([])
const loading = ref(false)
const filters = ref({ status: '', agreement: null })

const getAuthToken = () => sessionStorage.getItem('admin_token')

const fetchPayments = async () => {
  const token = getAuthToken()
  if (!token) {
    router.push('/admin/login')
    return
  }
  
  loading.value = true
  
  try {
    const response = await axios.post(
      '/api/admin/payments',
      filters.value,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )
    
    if (response.data.success) {
      payments.value = response.data.payments || []
    }
  } catch (err) {
    if (err.response?.status === 401) {
      sessionStorage.removeItem('admin_token')
      router.push('/admin/login')
    }
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString()
}

const formatAmount = (amount) => {
  if (amount === undefined || amount === null) return '-'
  // Format to show up to 6 decimal places, removing trailing zeros
  return parseFloat(amount.toFixed(6)).toString()
}

const truncateHash = (hash) => {
  if (!hash) return ''
  return `${hash.substring(0, 6)}...${hash.substring(hash.length - 4)}`
}

onMounted(() => {
  if (!getAuthToken()) {
    router.push('/admin/login')
  } else {
    fetchPayments()
  }
})
</script>
```

### Production Considerations

1. **Authentication**: Replace simple token with JWT or OAuth2
2. **Authorization**: Implement role-based access control
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Session Management**: Use secure, HTTP-only cookies
5. **HTTPS Only**: Enforce HTTPS for all admin endpoints
6. **Audit Logging**: Log all admin actions for security
7. **Input Validation**: Validate and sanitize all inputs
8. **Error Handling**: Don't expose sensitive error details

---

## Error Handling

### Backend Error Handling

```python
from functools import wraps

def handle_coinsub_errors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.Timeout:
            return jsonify({
                "error": "Payment service timeout"
            }), 504
        except requests.RequestException as e:
            app.logger.error(f"Coinsub API error: {e}")
            return jsonify({
                "error": "Payment service unavailable"
            }), 503
    return decorated

@app.route("/api/create-session", methods=["POST"])
@handle_coinsub_errors
def create_session():
    # ... implementation
```

### Frontend Error Handling

```javascript
async function handlePayment() {
  try {
    // ... payment flow
  } catch (error) {
    if (error.code === 'ACTION_REJECTED') {
      // User rejected the signature
      showMessage('Transaction cancelled')
    } else if (error.message.includes('insufficient funds')) {
      showMessage('Insufficient balance')
    } else {
      showMessage('Payment failed. Please try again.')
      console.error(error)
    }
  }
}
```

---

## Security Best Practices

### 1. API Key Security

```python
# Never expose API keys in frontend code
# Always proxy through your backend

# ❌ Bad - API key in frontend
fetch('https://api.coinsub.io/sessions', {
    headers: { 'Authorization': 'Bearer sk_live_xxx' }
})

# ✅ Good - Proxy through backend
fetch('/api/create-session', { 
    method: 'POST',
    body: JSON.stringify(cartData)
})
```

### 2. Webhook Verification

```python
# Always verify webhook signatures
def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### 3. Input Validation

```python
from marshmallow import Schema, fields, validate

class CartItemSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(max=200))
    price = fields.Float(required=True, validate=validate.Range(min=0.01))
    quantity = fields.Int(required=True, validate=validate.Range(min=1, max=100))

class CreateSessionSchema(Schema):
    items = fields.List(fields.Nested(CartItemSchema), required=True)
    currency = fields.Str(validate=validate.OneOf(['USD', 'EUR', 'GBP']))
```

### 4. CORS Configuration

```python
# Be specific about allowed origins
CORS(app, origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com"
])

# Not this:
# CORS(app, origins="*")  # ❌ Too permissive
```

---

## Testing

### Test Environment

Use `test.coinsub.io` for development:

```python
COINSUB_ENV=test  # Uses test.coinsub.io
```

### Mock Wallet for Testing

```javascript
// Create a mock wallet for automated testing
const mockWallet = {
  address: '0x1234567890123456789012345678901234567890',
  chainId: 1,
  
  async signMessage(typedData) {
    // Return a mock signature
    return '0x' + 'ab'.repeat(65)
  }
}
```

### Integration Tests

```python
def test_checkout_flow():
    # 1. Create session
    response = client.post('/api/create-session', json={
        'items': [{'name': 'Test', 'price': 10.00, 'quantity': 1}],
        'currency': 'USD'
    })
    assert response.status_code == 200
    session_id = response.json['session_id']
    
    # 2. Request message
    response = client.post(f'/api/session/{session_id}/message', json={
        'wallet_address': '0x1234...',
        'chain_id': 1
    })
    assert response.status_code == 200
    assert 'typed_data' in response.json
```

---

## Additional Resources

- [Coinsub API Reference](https://developers.coinsub.io)
- [EIP-712 Specification](https://eips.ethereum.org/EIPS/eip-712)
- [WalletConnect Documentation](https://docs.walletconnect.com)
- [Wagmi Documentation](https://wagmi.sh)
- [Viem Documentation](https://viem.sh)

---

## Getting Help

- **Documentation**: [developers.coinsub.io](https://developers.coinsub.io)
- **Support**: support@coinsub.io
- **GitHub Issues**: Report bugs in this repository
