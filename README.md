# Coinsub Integration Examples

> 🚀 **Complete integration examples** for integrating [Coinsub](https://coinsub.io) cryptocurrency payments into your applications.

This repository provides production-ready example implementations demonstrating how to integrate Coinsub's crypto payment system into various technology stacks.

## 📋 What is Coinsub?

[Coinsub](https://coinsub.io) is a cryptocurrency payment platform that enables businesses to accept crypto payments from customers. Coinsub handles the complexity of blockchain transactions, wallet management, and payment processing, allowing you to focus on your core business.

### Key Features

- ✅ **Multiple Payment Methods**: Support for USDC, USDT, and other cryptocurrencies
- ✅ **Multiple Networks**: Ethereum, Polygon, Base, and more
- ✅ **WalletConnect Integration**: Connect with MetaMask, Rainbow, Coinbase Wallet, and 300+ other wallets
- ✅ **Purchase Sessions**: Flexible API for dynamic product catalogs
- ✅ **Webhook Support**: Real-time payment notifications
- ✅ **Test Mode**: Full testing environment with testnet support

## 📁 Available Examples

### [Python + Vue.js](./python-vue-js/)

A complete full-stack example featuring:
- **Backend**: Python Flask server with Coinsub API integration
- **Frontend**: Vue.js 3 with WalletConnect for wallet connections
- **Features**: Shopping cart, checkout flow, real-time payment updates via SSE
- **Use Case**: E-commerce stores, SaaS applications, digital marketplaces

**Quick Start:**
```bash
cd python-vue-js
# See README.md for detailed setup instructions
```

### [Unity embed balance](./unity/RocketrampEmbedBalanceIntegration)

Embed button example featuring:
- **Unity**: Unity application with external browser link for access token usage

## 🚀 Getting Started

1. **Choose an example** that matches your tech stack
2. **Follow the setup instructions** in the example's README
3. **Get your API credentials** from [Coinsub Dashboard](https://app.coinsub.io)
4. **Start accepting crypto payments!**

## 📚 Documentation

- **[Coinsub Developer Documentation](https://developers.coinsub.io)** - Complete API reference
- **[Purchase Sessions Guide](https://developers.coinsub.io/purchase-sessions)** - Learn about Purchase Sessions
- **[Webhook Guide](https://developers.coinsub.io/webhooks)** - Setting up webhooks

## 🤝 Support

- **Documentation**: [developers.coinsub.io](https://developers.coinsub.io)
- **Email**: support@coinsub.io
- **GitHub Issues**: Report bugs or request features in this repository

## 📄 License

MIT License - Feel free to use these examples as a starting point for your integration.

---

**Note**: These examples are for demonstration purposes. For production use, ensure you:
- Implement proper error handling
- Add input validation
- Set up proper logging and monitoring
- Use environment-specific configurations
- Verify webhook signatures
- Follow security best practices
