<script setup>
import { ref } from 'vue'
import { useCartStore } from '../stores/cart'
import ProductCard from '../components/ProductCard.vue'

const cartStore = useCartStore()

// Coinsub merchandise - in a real app, these would come from your database
// Prices are in cents to allow testing with Circle faucet (max 1 USDC per 2 hours)
const products = ref([
  {
    id: 'merch_001',
    name: 'Coinsub Logo T-Shirt',
    description: 'Premium cotton t-shirt with Coinsub logo. Available in multiple sizes.',
    price: 0.25, // 25 cents
    image: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=300&fit=crop',
    category: 'apparel'
  },
  {
    id: 'merch_002',
    name: 'Coinsub Hoodie',
    description: 'Comfortable hoodie perfect for coding sessions. Soft fleece interior.',
    price: 0.30, // 30 cents
    image: 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&h=300&fit=crop',
    category: 'apparel'
  },
  {
    id: 'merch_003',
    name: 'Coinsub Coffee Mug',
    description: 'Ceramic mug with Coinsub branding. Perfect for your morning coffee.',
    price: 0.15, // 15 cents
    image: 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=400&h=300&fit=crop',
    category: 'accessories'
  },
  {
    id: 'merch_004',
    name: 'Coinsub Stickers Pack',
    description: 'Set of 10 vinyl stickers featuring Coinsub designs. Waterproof and durable.',
    price: 0.10, // 10 cents
    image: 'https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=400&h=300&fit=crop',
    category: 'accessories'
  },
  {
    id: 'merch_005',
    name: 'Coinsub Laptop Sleeve',
    description: 'Protective laptop sleeve with Coinsub logo. Fits 13-15 inch laptops.',
    price: 0.20, // 20 cents
    image: 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=400&h=300&fit=crop',
    category: 'accessories'
  },
  {
    id: 'merch_006',
    name: 'Coinsub Cap',
    description: 'Adjustable baseball cap with embroidered Coinsub logo. One size fits all.',
    price: 0.15, // 15 cents
    image: 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=400&h=300&fit=crop',
    category: 'apparel'
  }
])

function addToCart(product) {
  cartStore.addItem(product)
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <!-- Hero Section -->
    <div class="text-center mb-16">
      <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full 
                  bg-coinsub-500/10 border border-coinsub-500/20 mb-6">
        <span class="w-2 h-2 rounded-full bg-coinsub-400 animate-pulse"></span>
        <span class="text-coinsub-400 text-sm font-medium">Powered by Coinsub</span>
      </div>
      
      <h1 class="text-4xl md:text-6xl font-bold text-white mb-6">
        Pay with
        <span class="bg-gradient-to-r from-coinsub-400 via-indigo-400 to-purple-400 
                     bg-clip-text text-transparent">
          Cryptocurrency
        </span>
      </h1>
      
      <p class="text-xl text-slate-400 max-w-2xl mx-auto mb-8">
        Experience seamless crypto payments with WalletConnect integration.
        Browse our merchandise below and checkout with your favorite wallet.
      </p>

      <!-- Testnet USDC Faucet Info -->
      <div class="max-w-2xl mx-auto mb-8 p-4 rounded-xl bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border border-blue-500/20">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 mt-1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div class="flex-1">
            <h3 class="text-sm font-semibold text-white mb-1">Need Testnet USDC?</h3>
            <p class="text-sm text-slate-300 mb-3">
              Get free testnet USDC from Circle's faucet to test payments. You can claim up to 1 USDC per network every 2 hours.
            </p>
            <a 
              href="https://faucet.circle.com/" 
              target="_blank" 
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
            >
              Get Testnet USDC
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Merchandise Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <ProductCard 
        v-for="product in products"
        :key="product.id"
        :product="product"
        @add-to-cart="addToCart"
      />
    </div>

    <!-- Cart Summary (Fixed at bottom) -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="translate-y-full opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-300 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-full opacity-0"
    >
      <div 
        v-if="cartStore.itemCount > 0"
        class="fixed bottom-0 left-0 right-0 p-4 glass-darker border-t border-white/10"
      >
        <div class="max-w-7xl mx-auto flex items-center justify-between">
          <div class="flex items-center gap-4">
            <span class="text-slate-400">
              {{ cartStore.itemCount }} item{{ cartStore.itemCount === 1 ? '' : 's' }} in cart
            </span>
            <span class="text-2xl font-bold text-white">
              ${{ cartStore.total.toFixed(2) }}
            </span>
          </div>
          <router-link to="/checkout" class="btn-primary">
            Proceed to Checkout
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </router-link>
        </div>
      </div>
    </Transition>
  </div>
</template>
