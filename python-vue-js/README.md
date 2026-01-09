# Coinsub Purchase Session Integration

> 🚀 **Complete example** for integrating [Coinsub](https://coinsub.io) cryptocurrency payments using Purchase Sessions.

This repository provides a complete, production-ready example demonstrating Coinsub's crypto payment system integration. It features a Python Flask backend and Vue.js frontend with WalletConnect integration.

**📖 For detailed integration instructions**, see [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - a comprehensive step-by-step tutorial for integrating Coinsub into your own application.

## 📋 Overview

### Why Purchase Sessions?

Purchase Sessions are ideal for companies with **large product catalogs** because they:

- ✅ Allow ad-hoc combinations of products (like a checkout cart)
- ✅ Don't require pre-registering products in Coinsub
- ✅ Enable dynamic pricing and custom product configurations
- ✅ Provide a single API flow to handle your entire catalog

**Trade-offs:**
- Requires one API call per purchase to instantiate a session
- Product performance tracking and analytics must be done on your end

### How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │     │   Backend   │     │   Coinsub   │
│   (Vue.js)  │     │   (Flask)   │     │     API     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  1. Cart checkout │                   │
       │──────────────────>│                   │
       │                   │                   │
       │                   │ 2. Create session │
       │                   │──────────────────>│
       │                   │                   │
       │                   │ 3. Session ID     │
       │                   │<──────────────────│
       │                   │                   │
       │  4. Connect wallet│                   │
       │   (WalletConnect) │                   │
       │                   │                   │
       │  5. Request msg   │                   │
       │──────────────────>│                   │
       │                   │ 6. Get EIP-712    │
       │                   │──────────────────>│
       │                   │                   │
       │                   │ 7. Typed data     │
       │                   │<──────────────────│
       │                   │                   │
       │  8. Sign message  │                   │
       │   (in wallet)     │                   │
       │                   │                   │
       │  9. Submit sig    │                   │
       │──────────────────>│                   │
       │                   │ 10. Complete      │
       │                   │──────────────────>│
       │                   │                   │
       │                   │ 11. Payment ID    │
       │                   │<──────────────────│
       │                   │                   │
       │  12. Success page │                   │
       │   (SSE connect)   │                   │
       │──────────────────>│                   │
       │                   │                   │
       │                   │ 13. Webhook       │
       │                   │<──────────────────│
       │                   │   (type: payment, │
       │                   │    status: completed)
       │                   │                   │
       │                   │ 14. Push tx hash  │
       │  15. Receive hash  │                   │
       │<──────────────────│   (via SSE)      │
       │                   │                   │
       │  16. Show tx link  │                   │
       │                   │                   │
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Coinsub account ([test.coinsub.io](https://test.coinsub.io) for development)
- WalletConnect Project ID ([cloud.walletconnect.com](https://cloud.walletconnect.com))

### 1. Clone and Setup

```bash
# Navigate to the python example
cd python

# Setup backend
cd backend
python -m venv venv # or python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Setup frontend
cd ../frontend
npm install
cp .env.example .env
```

### 2. Configure Environment

**Backend (`backend/.env`):**
```env
COINSUB_API_KEY=your-api-key-here
COINSUB_MERCHANT_ID=your-merchant-id-here
COINSUB_WEBHOOK_SECRET=your-webhook-secret
COINSUB_ENV=test
PORT=5001
FLASK_DEBUG=true
```

**Frontend (`frontend/.env`):**
```env
VITE_WALLETCONNECT_PROJECT_ID=your-walletconnect-project-id
VITE_COINSUB_ENV=test
```

**Note:** Set `VITE_COINSUB_ENV=production` for production mode. In test mode, WalletConnect will support testnets (Ethereum Sepolia, Polygon Amoy, Base Sepolia). In production mode, it will support mainnets (Ethereum, Polygon, Base).

### 3. Get Your API Key and Merchant ID

1. Sign up at [test.coinsub.io](https://test.coinsub.io) (development) or [app.coinsub.io](https://app.coinsub.io) (production)
2. Navigate to [API Keys](https://app.coinsub.io/merchant/profile/apikeys) in your merchant profile
3. Copy your **Merchant ID** and create a new **API key** (both are available on the same page)
4. Add both `COINSUB_MERCHANT_ID` and `COINSUB_API_KEY` to your `.env` file

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173) to see the demo!

## 📁 Project Structure

```
python/
├── backend/
│   ├── app.py              # Flask application with all endpoints
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
│
├── frontend/
│   ├── src/
│   │   ├── components/     # Vue components
│   │   │   ├── NavBar.vue
│   │   │   ├── ProductCard.vue
│   │   │   ├── CartItem.vue
│   │   │   └── CheckoutSteps.vue
│   │   ├── views/          # Page components
│   │   │   ├── HomeView.vue
│   │   │   ├── CheckoutView.vue
│   │   │   ├── SuccessView.vue  # Connects to SSE for real-time updates
│   │   │   ├── AdminLoginView.vue  # Merchant admin login
│   │   │   └── AdminDashboardView.vue  # Payment history dashboard
│   │   ├── stores/         # Pinia stores
│   │   │   ├── wallet.js   # WalletConnect integration
│   │   │   ├── cart.js     # Shopping cart state
│   │   │   └── checkout.js # Checkout flow state
│   │   ├── assets/
│   │   │   └── main.css    # Tailwind styles
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── .env.example
│
└── README.md               # This file
```

## 🔌 API Reference

### Backend Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/create-session` | Create a purchase session |
| `GET` | `/api/session/<id>/status` | Get session status |
| `GET` | `/api/session/<id>/events` | **SSE stream** for real-time payment updates |
| `POST` | `/api/session/<id>/message` | Request purchase message to sign |
| `POST` | `/api/session/<id>/sign` | Submit signed message |
| `POST` | `/api/session/<id>/cancel` | Cancel/expire session |
| `POST` | `/api/webhooks/coinsub` | Receive Coinsub webhooks |
| `POST` | `/api/admin/login` | Admin login (demo: admin/admin) |
| `POST` | `/api/admin/payments` | Get all payments (requires admin auth) |

### Admin Endpoints

The demo includes a merchant admin dashboard for viewing payment history.

**Login:**
```json
POST /api/admin/login
{
  "username": "admin",
  "password": "admin"
}
```

**Get Payments:**
```json
POST /api/admin/payments
Headers: {
  "Authorization": "Bearer admin_token"
}
Body: {
  "agreement": null,
  "status": ""  // Optional: "completed", "pending", "failed", or "" for all
}
```

**Note:** The backend proxies the request to Coinsub's API endpoint (`GET /v1/payments/all`) which accepts a JSON body for filtering.

**Access the Admin Dashboard:**
1. Navigate to `/admin/login` in your browser
2. Login with credentials: `admin` / `admin`
3. View all payments sorted by date (descending)

**Note:** This is a demo implementation with simple authentication. In production, use proper JWT tokens, session management, and role-based access control.

### Create Session Request

```json
POST /api/create-session
{
  "items": [
    {"id": "merch_001", "name": "Coinsub Logo T-Shirt", "price": 0.25, "quantity": 1},
    {"id": "merch_002", "name": "Coinsub Hoodie", "price": 0.30, "quantity": 1}
  ],
  "currency": "USDC",
  "customer_email": "customer@example.com",
  "metadata": {
    "order_id": "ORD-12345",
    "source": "coinsub-demo"
  }
}
```

**Note:** Prices are in USDC (not USD). For testing, use small amounts (cents) to work within the Circle Faucet's 1 USDC limit.

### Request Message

```json
POST /api/session/{session_id}/message
{
  "wallet_address": "0x...",
  "chain_id": 80002
}
```

**Note:** Use the appropriate chain ID for your network:
- Ethereum Sepolia: `11155111`
- Polygon Amoy: `80002`
- Base Sepolia: `84532`
- Ethereum Mainnet: `1`
- Polygon Mainnet: `137`
- Base Mainnet: `8453`

### Submit Signature

```json
POST /api/session/{session_id}/sign
{
  "signature": "0x...",
  "wallet_address": "0x...",
  "chain_id": 80002,
  "message_id": "..."
}
```

**Note:** The `chain_id` parameter is required and should match the chain used for signing.

### SSE Events Endpoint

The frontend connects to this endpoint using Server-Sent Events (SSE) to receive real-time transaction hash updates when webhooks arrive:

```javascript
// Frontend automatically connects on success page
const eventSource = new EventSource(`/api/session/${sessionId}/events`)

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'payment.completed') {
    // Transaction hash received!
    console.log('Transaction:', data.transaction_hash)
  }
}
```

**How it works:**
1. Frontend connects to SSE endpoint after payment submission
2. Backend receives webhook from Coinsub
3. Backend pushes transaction hash to connected SSE clients
4. Frontend receives transaction hash instantly (no polling needed)

## 🔐 Webhooks & Real-Time Updates

Coinsub sends webhooks for payment lifecycle events. Configure your webhook URL in your merchant profile settings.

> ⚠️ **Note**: Coinsub cannot send webhooks to `localhost`. For local development, use a tunneling service like [ngrok](https://ngrok.com) to expose your local server.

### Configuring Webhooks

1. **Test Environment**: Go to [https://test.coinsub.io/merchant/profile/edit](https://test.coinsub.io/merchant/profile/edit)
2. **Production Environment**: Go to [https://app.coinsub.io/merchant/profile/edit](https://app.coinsub.io/merchant/profile/edit)
3. Enter your **complete webhook URL** in the webhook configuration section:
   - Must include the full path: `https://your-domain.com/api/webhooks/coinsub`
   - Do NOT enter just the base domain (e.g., `https://your-domain.com`)
4. Copy the webhook secret and add it to your `.env` file as `COINSUB_WEBHOOK_SECRET`

### Local Webhook Testing with ngrok

Webhooks are server-to-server notifications. When Coinsub processes a payment, it sends a webhook to your backend server. The frontend (Vue.js) doesn't receive webhooks directly.

## Why Webhooks + SSE Are Essential

This demo uses **webhooks as the primary source of truth** for payment status, with **SSE for real-time frontend updates**:

### Webhook Benefits:
- ⚡ **Real-time**: Instant notification when payment status changes
- 🎯 **Efficient**: Only one request per event (no polling)
- 🔒 **Reliable**: Works even if user closes browser (backend still receives notifications)
- 📊 **Scalable**: Better for production with many concurrent payments
- 🎪 **Complete**: Receive all event types (payment.completed, payment.failed, etc.)
- ✅ **Production-ready**: Industry standard for payment processing

### SSE Benefits:
- 🚀 **Instant UI updates**: Frontend receives transaction hash immediately when webhook arrives
- 🔄 **No polling**: Eliminates constant HTTP requests
- 💡 **Efficient**: Single persistent connection instead of repeated requests
- ⚡ **Real-time**: User sees transaction hash as soon as it's available

### How It Works:

1. **User signs transaction** → Frontend submits signature to backend
2. **Backend submits to Coinsub** → Payment processing begins
3. **User redirected** → Success page
4. **Frontend connects** → Opens SSE connection to `/api/session/<id>/events`
5. **Webhook arrives** → Coinsub sends webhook to backend when payment completes
6. **Backend processes** → Extracts transaction hash and pushes to SSE clients
7. **Frontend receives** → Transaction hash appears instantly via SSE
8. **User sees** → Transaction hash and blockchain explorer link displayed

**Note:** The demo uses webhooks + SSE for real-time updates. No polling is used. When a webhook arrives, it means the payment went through successfully, and the transaction hash is immediately pushed to the frontend via SSE.

**For production**, you should:
- Store webhook data in a **database** (not memory)
- Process webhooks **asynchronously** for order fulfillment
- Send confirmation emails based on webhook events
- Update order status in your database when webhooks arrive 

```bash
# Install ngrok (https://ngrok.com/download)
# Sign up and setup your ngrok auth token
ngrok config add-authtoken your-token-goes-here

# Then expose your local backend:
ngrok http 5001

# You'll get a public URL like: https://abc123.ngrok-free.dev
```

**⚠️ IMPORTANT:** When configuring your webhook URL in Coinsub, you must include the full path:

1. Go to [https://test.coinsub.io/merchant/profile/edit](https://test.coinsub.io/merchant/profile/edit)
2. Enter the **complete webhook URL** (not just the base domain):
   ```
   https://abc123.ngrok-free.dev/api/webhooks/coinsub
   ```
   **NOT:** `https://abc123.ngrok-free.dev` ❌  
   **YES:** `https://abc123.ngrok-free.dev/api/webhooks/coinsub` ✅

3. Copy the webhook secret from the same page and add it to your `.env` file as `COINSUB_WEBHOOK_SECRET`

**Note:** If you only enter the base ngrok URL (without `/api/webhooks/coinsub`), Coinsub will send webhooks to `/` which will result in a 404 or 500 error. Always include the full path!

**Note:** Signature verification is disabled in this demo for simplicity. In production, you should verify webhook signatures to ensure they're authentic and prevent spoofing.

### Webhook Events

Coinsub sends webhooks with `type: "payment"` and a `status` field indicating the payment state:

| Event Type | Status | Description |
|------------|--------|-------------|
| `payment` | `completed` | Payment successful ✅ |
| `payment` | `failed` | Payment failed ❌ |
| `payment` | `processing` | Processing on-chain |
| `session.expired` | - | Session expired |

**Webhook Structure:**
```json
{
  "type": "payment",
  "status": "completed",
  "origin_id": "sess_935fb78b-5fd6-47e6-a2d6-627c42edca8c",
  "payment_id": "paym_0d55a60f-7e37-47dc-92b6-da49cba792cf",
  "amount": 0.25,
  "currency": "USDC",
  "transaction_details": {
    "transaction_hash": "0x0266ef66d8e36640c46f3439b7bafb2943540f9605907a28e7bc6fc20b04c1ad",
    "chain_id": 80002
  }
}
```

**Note:** The `origin_id` field contains the purchase session ID. Use `origin_id` (not `session_id`) to match webhooks to your purchase sessions.

### Webhook Verification

Always verify webhook signatures to ensure authenticity:

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

## 👨‍💼 Merchant Admin Dashboard

The demo includes a merchant admin dashboard where merchants can view their payment history directly from the Coinsub API.

### Features

- **Login System**: Simple authentication (demo: `admin` / `admin`)
- **Payment History**: View all payments sorted by date (newest first)
- **Status Filtering**: Filter payments by status (completed, pending, failed, or all)
- **Transaction Details**: View transaction hashes with blockchain explorer links
- **Real-time Data**: Fetches directly from Coinsub API

### Accessing the Admin Dashboard

1. Navigate to `/admin/login` (or click "Admin" in the navigation bar)
2. Login with credentials: `admin` / `admin`
3. View your payment history with transaction details

### Implementation Details

The admin dashboard proxies requests to Coinsub's `/v1/payments/all` endpoint, which:
- Returns all payments for your merchant account
- Supports filtering by `agreement` and `status`
- Returns payments sorted by creation date (descending)

**Note:** This is a demo implementation with simple token-based authentication. In production, you should:
- Use proper JWT tokens or session management
- Implement role-based access control (RBAC)
- Add rate limiting to prevent abuse
- Store admin sessions securely
- Use HTTPS only for admin endpoints

## 💼 Integrating Into Your Application

> 📖 **For detailed integration instructions**, see [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - a comprehensive step-by-step tutorial covering:
> - Backend implementation details
> - Frontend implementation details  
> - Wallet integration with WalletConnect
> - EIP-712 message signing
> - Webhook handling
> - Admin dashboard implementation
> - Error handling
> - Security best practices
> - Testing strategies

### Quick Integration Overview

**Backend Integration Points:**
1. **Create Session**: Call when user initiates checkout
2. **Handle Webhooks**: Update your database when payments complete
3. **Order Fulfillment**: Grant access/ship products after `payment.completed`

**Frontend Integration Points:**
1. **Wallet Connection**: Use the `wallet.js` store as-is or adapt to your needs
2. **Cart Management**: Replace `cart.js` with your existing cart system
3. **Checkout Flow**: Customize the checkout UI to match your brand

## 🌐 Supported Networks

The demo supports the following EVM chains:

**Test Mode** (when `VITE_COINSUB_ENV=test`):
- Ethereum Sepolia
- Polygon Amoy
- Base Sepolia

**Production Mode** (when `VITE_COINSUB_ENV=production`):
- Ethereum Mainnet
- Polygon Mainnet
- Base Mainnet

Add more chains in `frontend/src/stores/wallet.js`:

```javascript
import { bsc, avalanche, arbitrum, optimism } from 'viem/chains'

// Add to the chains array based on environment
const chains = isTestMode 
  ? [sepolia, polygonAmoy, baseSepolia, /* your testnets */]
  : [mainnet, polygon, base, bsc, avalanche, arbitrum, optimism]
```

## 🎨 Customization

### Styling

The frontend uses **Tailwind CSS** with custom design tokens. Edit `tailwind.config.js` to match your brand:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#your-brand-color',
      // ...
    }
  }
}
```

### Adding Products

Products in the demo are hardcoded. In production, fetch from your database:

```javascript
// In HomeView.vue
import { onMounted, ref } from 'vue'
import axios from 'axios'

const products = ref([])

onMounted(async () => {
  const { data } = await axios.get('/api/products')
  products.value = data
})
```

## 🧪 Testing

### Test Environment

Use `test.coinsub.io` for development. Test payments don't move real funds.

### Test Wallets

For testing, use any Web3 wallet on test networks:
- Get testnet ETH from faucets (e.g., [Sepolia Faucet](https://sepoliafaucet.com))
- Get testnet USDC from [Circle Faucet](https://faucet.circle.com/) (max 1 USDC per 2 hours)
- Connect to Sepolia, Polygon Amoy, or Base Sepolia testnets
- **Note:** Product prices in the demo are set in cents (0.10-0.30 USDC) to allow multiple test purchases within the Circle Faucet limit

## 📚 Resources

- [Coinsub Developer Documentation](https://developers.coinsub.io)
- [Purchase Sessions API](https://developers.coinsub.io/purchase-sessions)
- [Headless API Guide](https://developers.coinsub.io/headless-api)
- [WalletConnect Docs](https://docs.walletconnect.com)

## 🤝 Support

- Email: support@coinsub.io
- Documentation: [developers.coinsub.io](https://developers.coinsub.io)

## 📄 License

MIT License - Feel free to use this code as a starting point for your integration.
