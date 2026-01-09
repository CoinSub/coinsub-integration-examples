<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useWalletStore } from '../stores/wallet'
import { useCartStore } from '../stores/cart'

const router = useRouter()
const walletStore = useWalletStore()
const cartStore = useCartStore()

const shortAddress = computed(() => {
  if (!walletStore.address) return ''
  return `${walletStore.address.slice(0, 6)}...${walletStore.address.slice(-4)}`
})
</script>

<template>
  <nav class="glass-darker sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <router-link to="/" class="flex items-center gap-3 group">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-coinsub-500 to-indigo-500 
                      flex items-center justify-center text-white font-bold text-lg
                      group-hover:scale-110 transition-transform duration-300">
            C
          </div>
          <span class="text-xl font-semibold text-white">
            Coinsub Demo
          </span>
        </router-link>

        <!-- Right side -->
        <div class="flex items-center gap-4">
          <!-- Admin link -->
          <router-link 
            to="/admin/login"
            class="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Admin
          </router-link>
          
          <!-- Cart indicator -->
          <router-link 
            v-if="cartStore.itemCount > 0"
            to="/checkout"
            class="relative p-2 text-slate-400 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span class="absolute -top-1 -right-1 w-5 h-5 bg-coinsub-500 rounded-full 
                         text-xs text-white flex items-center justify-center font-medium">
              {{ cartStore.itemCount }}
            </span>
          </router-link>

          <!-- Wallet connection -->
          <div v-if="walletStore.isConnected" class="flex items-center gap-3">
            <div class="flex items-center gap-2 px-4 py-2 glass rounded-xl">
              <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
              <span class="text-sm font-mono text-slate-300">{{ shortAddress }}</span>
            </div>
            <button 
              @click="walletStore.disconnect"
              class="p-2 text-slate-400 hover:text-red-400 transition-colors"
              title="Disconnect wallet"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
          <button 
            v-else
            @click="walletStore.connect"
            class="btn-primary text-sm"
          >
            Connect Wallet
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
