# Coinsub Purchase Session Integration

> 🚀 **Fast prototyping example** for integrating [Coinsub](https://coinsub.io) cryptocurrency payments using Purchase Sessions.

This repository provides a complete, production-ready example for companies looking to integrate Coinsub's crypto payment system. It features a Python Flask backend and Vue.js frontend with WalletConnect integration.

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
       │  12. Success!     │                   │
       │<──────────────────│                   │
       │                   │                   │
       │                   │ 13. Webhook       │
       │                   │<──────────────────│
       │                   │   (payment.completed)
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
python -m venv venv
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
COINSUB_WEBHOOK_SECRET=your-webhook-secret
COINSUB_ENV=test
PORT=5000
FLASK_DEBUG=true
```

**Frontend (`frontend/.env`):**
```env
VITE_WALLETCONNECT_PROJECT_ID=your-walletconnect-project-id
```

### 3. Get Your API Key

1. Sign up at [test.coinsub.io](https://test.coinsub.io) (development) or [app.coinsub.io](https://app.coinsub.io) (production)
2. Navigate to **Settings → API Keys**
3. Create a new API key and copy it to your `.env`

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
│   │   │   └── SuccessView.vue
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
| `POST` | `/api/session/<id>/message` | Request purchase message to sign |
| `POST` | `/api/session/<id>/sign` | Submit signed message |
| `POST` | `/api/session/<id>/cancel` | Cancel/expire session |
| `POST` | `/api/webhooks/coinsub` | Receive Coinsub webhooks |

### Create Session Request

```json
POST /api/create-session
{
  "items": [
    {"name": "Product 1", "price": 29.99, "quantity": 1},
    {"name": "Product 2", "price": 49.99, "quantity": 2}
  ],
  "currency": "USD",
  "customer_email": "customer@example.com",
  "metadata": {
    "order_id": "ORD-12345"
  }
}
```

### Request Message

```json
POST /api/session/{session_id}/message
{
  "wallet_address": "0x...",
  "chain_id": 1
}
```

### Submit Signature

```json
POST /api/session/{session_id}/sign
{
  "signature": "0x...",
  "wallet_address": "0x...",
  "message_id": "..."
}
```

## 🔐 Webhooks

Coinsub sends webhooks for payment lifecycle events. Configure your webhook URL in the Coinsub dashboard.

> ⚠️ **Note**: Coinsub cannot send webhooks to `localhost`. For local development, use a tunneling service like [ngrok](https://ngrok.com) to expose your local server.

### Local Webhook Testing with ngrok

```bash
# Install ngrok (https://ngrok.com/download)
# Then expose your local backend:
ngrok http 5000

# You'll get a public URL like: https://abc123.ngrok.io
# Configure this in Coinsub dashboard: https://abc123.ngrok.io/api/webhooks/coinsub
```

The **webhook secret** is used to verify that incoming webhooks are genuinely from Coinsub (not spoofed). This is critical for production but also recommended during development with ngrok.

### Webhook Events

| Event | Description |
|-------|-------------|
| `payment.created` | Payment initiated |
| `payment.processing` | Processing on-chain |
| `payment.completed` | Payment successful ✅ |
| `payment.failed` | Payment failed ❌ |
| `session.expired` | Session expired |

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

## 💼 Integrating Into Your Application

### Backend Integration Points

1. **Create Session**: Call when user initiates checkout
2. **Handle Webhooks**: Update your database when payments complete
3. **Order Fulfillment**: Grant access/ship products after `payment.completed`

```python
def handle_payment_completed(data: dict):
    session_id = data.get("session_id")
    payment_id = data.get("payment_id")
    
    # 1. Find the order in your database
    order = Order.query.filter_by(session_id=session_id).first()
    
    # 2. Update order status
    order.status = "paid"
    order.payment_id = payment_id
    db.session.commit()
    
    # 3. Fulfill the order
    fulfill_order(order)
    
    # 4. Send confirmation email
    send_confirmation_email(order.customer_email)
```

### Frontend Integration Points

1. **Wallet Connection**: Use the `wallet.js` store as-is or adapt to your needs
2. **Cart Management**: Replace `cart.js` with your existing cart system
3. **Checkout Flow**: Customize the checkout UI to match your brand

## 🌐 Supported Networks

The demo supports the following EVM chains:

- Ethereum Mainnet
- Polygon
- Arbitrum
- Optimism  
- Base

Add more chains in `frontend/src/stores/wallet.js`:

```javascript
import { bsc, avalanche } from 'viem/chains'

const chains = [mainnet, polygon, arbitrum, optimism, base, bsc, avalanche]
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
- Get testnet ETH from faucets
- Connect to Sepolia or other testnets

## 🚀 Production Deployment

### Checklist

- [ ] Switch `COINSUB_ENV` to `production`
- [ ] Use production API key from [app.coinsub.io](https://app.coinsub.io)
- [ ] Set up production webhook URL
- [ ] Enable HTTPS
- [ ] Configure CORS for your domain
- [ ] Set `FLASK_DEBUG=false`
- [ ] Use a production WSGI server (gunicorn)

### Deploy Backend

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Deploy Frontend

```bash
npm run build
# Serve the dist/ folder with your preferred static host
```

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
