<script setup>
import { ref } from 'vue'
import { useCartStore } from '../stores/cart'
import ProductCard from '../components/ProductCard.vue'

const cartStore = useCartStore()

// Sample products - in a real app, these would come from your database
const products = ref([
  {
    id: 'prod_001',
    name: 'Pro Subscription',
    description: 'Unlock all premium features for your account',
    price: 29.99,
    image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=300&fit=crop',
    category: 'subscription'
  },
  {
    id: 'prod_002',
    name: 'API Credits Pack',
    description: '10,000 API credits for your applications',
    price: 49.99,
    image: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&h=300&fit=crop',
    category: 'credits'
  },
  {
    id: 'prod_003',
    name: 'Enterprise License',
    description: 'Full access for your entire organization',
    price: 199.99,
    image: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=300&fit=crop',
    category: 'license'
  },
  {
    id: 'prod_004',
    name: 'Premium Support',
    description: '24/7 priority support with dedicated manager',
    price: 99.99,
    image: 'https://images.unsplash.com/photo-1553877522-43269d4ea984?w=400&h=300&fit=crop',
    category: 'support'
  },
  {
    id: 'prod_005',
    name: 'Data Export Tool',
    description: 'Export your data in multiple formats',
    price: 19.99,
    image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=300&fit=crop',
    category: 'tools'
  },
  {
    id: 'prod_006',
    name: 'Custom Integration',
    description: 'White-glove integration service',
    price: 499.99,
    image: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=300&fit=crop',
    category: 'service'
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
        Select products below and checkout with your favorite wallet.
      </p>

      <div class="flex flex-wrap justify-center gap-4">
        <div class="flex items-center gap-2 px-4 py-2 glass rounded-full">
          <div class="crypto-icon-eth">Ξ</div>
          <span class="text-slate-300 text-sm">Ethereum</span>
        </div>
        <div class="flex items-center gap-2 px-4 py-2 glass rounded-full">
          <div class="crypto-icon-usdc">$</div>
          <span class="text-slate-300 text-sm">USDC</span>
        </div>
        <div class="flex items-center gap-2 px-4 py-2 glass rounded-full">
          <div class="crypto-icon-usdt">₮</div>
          <span class="text-slate-300 text-sm">USDT</span>
        </div>
      </div>
    </div>

    <!-- Products Grid -->
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
