<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCheckoutStore } from '../stores/checkout'

const router = useRouter()
const checkoutStore = useCheckoutStore()

const confetti = ref([])

// Generate confetti on mount
onMounted(() => {
  const colors = ['#0ea5e9', '#6366f1', '#8b5cf6', '#10b981', '#f59e0b']
  for (let i = 0; i < 50; i++) {
    confetti.value.push({
      left: Math.random() * 100,
      delay: Math.random() * 2,
      duration: 2 + Math.random() * 2,
      color: colors[Math.floor(Math.random() * colors.length)]
    })
  }
})

function goHome() {
  checkoutStore.reset()
  router.push('/')
}
</script>

<template>
  <div class="min-h-[70vh] flex items-center justify-center px-4 relative overflow-hidden">
    <!-- Confetti -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div 
        v-for="(piece, index) in confetti"
        :key="index"
        class="absolute w-2 h-2 rounded-full animate-confetti"
        :style="{
          left: `${piece.left}%`,
          backgroundColor: piece.color,
          animationDelay: `${piece.delay}s`,
          animationDuration: `${piece.duration}s`
        }"
      ></div>
    </div>

    <div class="text-center z-10">
      <!-- Success Icon -->
      <div class="relative inline-block mb-8">
        <div class="w-24 h-24 rounded-full bg-emerald-500/20 flex items-center justify-center
                    animate-[pulse_2s_ease-in-out_infinite]">
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            class="h-12 w-12 text-emerald-400" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path 
              stroke-linecap="round" 
              stroke-linejoin="round" 
              stroke-width="2" 
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" 
            />
          </svg>
        </div>
        <div class="absolute -inset-4 rounded-full border-2 border-emerald-500/30 
                    animate-ping opacity-75"></div>
      </div>

      <!-- Title -->
      <h1 class="text-4xl font-bold text-white mb-4">
        Payment Successful!
      </h1>
      
      <p class="text-xl text-slate-400 mb-8 max-w-md mx-auto">
        Your cryptocurrency payment has been processed successfully.
      </p>

      <!-- Transaction Details -->
      <div v-if="checkoutStore.transactionHash || checkoutStore.paymentId" 
           class="card max-w-md mx-auto mb-8">
        <h3 class="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
          Transaction Details
        </h3>
        <div class="space-y-3 text-left">
          <div v-if="checkoutStore.paymentId" class="flex justify-between">
            <span class="text-slate-400">Payment ID</span>
            <span class="text-white font-mono text-sm">
              {{ checkoutStore.paymentId }}
            </span>
          </div>
          <div v-if="checkoutStore.transactionHash" class="flex justify-between">
            <span class="text-slate-400">Transaction</span>
            <a 
              :href="`https://etherscan.io/tx/${checkoutStore.transactionHash}`"
              target="_blank"
              rel="noopener"
              class="text-coinsub-400 hover:text-coinsub-300 font-mono text-sm flex items-center gap-1"
            >
              {{ checkoutStore.transactionHash?.slice(0, 10) }}...
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <button @click="goHome" class="btn-primary">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Continue Shopping
        </button>
      </div>

      <!-- Support Link -->
      <p class="mt-8 text-sm text-slate-500">
        Questions about your order? 
        <a href="mailto:support@example.com" class="text-coinsub-400 hover:text-coinsub-300">
          Contact support
        </a>
      </p>
    </div>
  </div>
</template>

<style scoped>
@keyframes confetti {
  0% {
    transform: translateY(-10vh) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg);
    opacity: 0;
  }
}

.animate-confetti {
  animation: confetti linear forwards;
}
</style>
