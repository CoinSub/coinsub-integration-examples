<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCheckoutStore } from '../stores/checkout'

const router = useRouter()
const checkoutStore = useCheckoutStore()

const confetti = ref([])
const transactionHash = ref(null)
const chainId = ref(null)
const paymentId = ref(null)
const waitingForWebhook = ref(true)
let eventSource = null

function getExplorerUrl(chainId, txHash) {
  if (!txHash) return null
  
  // Chain ID to explorer mapping
  const explorers = {
    1: `https://etherscan.io/tx/${txHash}`,           // Ethereum Mainnet
    11155111: `https://sepolia.etherscan.io/tx/${txHash}`, // Ethereum Sepolia
    137: `https://polygonscan.com/tx/${txHash}`,      // Polygon Mainnet
    80002: `https://amoy.polygonscan.com/tx/${txHash}`, // Polygon Amoy
    8453: `https://basescan.org/tx/${txHash}`,        // Base Mainnet
    84532: `https://sepolia.basescan.org/tx/${txHash}` // Base Sepolia
  }
  
  return explorers[chainId] || `https://etherscan.io/tx/${txHash}`
}

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
  
  // Connect to SSE endpoint to receive transaction hash when webhook arrives
  if (checkoutStore.sessionId) {
    const sseUrl = `/api/session/${checkoutStore.sessionId}/events`
    eventSource = new EventSource(sseUrl)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'payment.completed') {
          transactionHash.value = data.transaction_hash
          chainId.value = data.chain_id
          paymentId.value = data.payment_id
          waitingForWebhook.value = false
          
          // Close the connection once we have the transaction hash
          if (eventSource) {
            eventSource.close()
            eventSource = null
          }
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error)
      }
    }
    
    eventSource.onerror = () => {
      // Don't close on error - EventSource will auto-reconnect
      // But if we've been waiting too long, stop waiting
      setTimeout(() => {
        if (!transactionHash.value && waitingForWebhook.value) {
          waitingForWebhook.value = false
          if (eventSource) {
            eventSource.close()
            eventSource = null
          }
        }
      }, 60000) // 60 second timeout
    }
  } else {
    waitingForWebhook.value = false
  }
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
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
        <span v-if="transactionHash">Payment Successful!</span>
        <span v-else>Waiting for Confirmation...</span>
      </h1>
      
      <p v-if="transactionHash" class="text-xl text-slate-400 mb-8 max-w-md mx-auto">
        Your payment has been confirmed on the blockchain.
      </p>
      <p v-else class="text-xl text-slate-400 mb-8 max-w-md mx-auto">
        Your payment has been submitted. Waiting for blockchain confirmation...
      </p>
      
      <!-- Waiting Indicator -->
      <div v-if="waitingForWebhook && !transactionHash" class="mb-8 max-w-md mx-auto">
        <div class="flex items-center justify-center gap-3 text-slate-400">
          <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="text-sm">Waiting for webhook confirmation...</span>
        </div>
      </div>

      <!-- Transaction Details -->
      <div v-if="transactionHash" class="card max-w-md mx-auto mb-8">
        <h3 class="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
          Transaction Details
        </h3>
        <div class="space-y-3 text-left">
          <div v-if="paymentId" class="flex justify-between">
            <span class="text-slate-400">Payment ID</span>
            <span class="text-white font-mono text-sm">
              {{ paymentId }}
            </span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Transaction</span>
            <a 
              :href="getExplorerUrl(chainId, transactionHash)"
              target="_blank"
              rel="noopener"
              class="text-coinsub-400 hover:text-coinsub-300 font-mono text-sm flex items-center gap-1 transition-colors"
            >
              {{ transactionHash.slice(0, 10) }}...{{ transactionHash.slice(-8) }}
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
          <div v-if="chainId" class="flex justify-between">
            <span class="text-slate-400">Network</span>
            <span class="text-white text-sm">
              {{ chainId === 84532 ? 'Base Sepolia' : chainId === 80002 ? 'Polygon Amoy' : chainId === 11155111 ? 'Ethereum Sepolia' : `Chain ${chainId}` }}
            </span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex flex-col sm:flex-row gap-4 justify-center">
        <button @click="goHome" class="btn-primary whitespace-nowrap">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          <span>Continue Shopping</span>
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
