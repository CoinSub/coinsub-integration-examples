<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '../stores/cart'
import { useWalletStore } from '../stores/wallet'
import { useCheckoutStore } from '../stores/checkout'
import CartItem from '../components/CartItem.vue'
import CheckoutSteps from '../components/CheckoutSteps.vue'

const router = useRouter()
const cartStore = useCartStore()
const walletStore = useWalletStore()
const checkoutStore = useCheckoutStore()

const currentStep = ref(1)
const isSigning = ref(false)

// Steps configuration
const steps = [
  { id: 1, name: 'Review Cart', description: 'Verify your items' },
  { id: 2, name: 'Connect Wallet', description: 'Link your crypto wallet' },
  { id: 3, name: 'Confirm Payment', description: 'Sign the transaction' }
]

// Computed
const canProceed = computed(() => {
  if (currentStep.value === 1) return !cartStore.isEmpty
  if (currentStep.value === 2) return walletStore.isConnected && !checkoutStore.isLoading
  if (currentStep.value === 3) return checkoutStore.canPay
  return false
})

// Watch for wallet connection
watch(() => walletStore.isConnected, async (isConnected) => {
  if (isConnected && currentStep.value === 2 && !checkoutStore.isLoading && !checkoutStore.sessionId) {
    console.log('Wallet connected, initializing checkout...')
    await initializeCheckout()
  }
})

// Watch for step changes - initialize when reaching step 2 with wallet already connected
watch(() => currentStep.value, async (step) => {
  if (step === 2 && walletStore.isConnected && !checkoutStore.isLoading && !checkoutStore.sessionId) {
    console.log('Reached step 2 with wallet connected, initializing checkout...')
    await initializeCheckout()
  }
})

// Check if wallet is already connected on mount
onMounted(async () => {
  if (walletStore.isConnected && currentStep.value === 2 && !checkoutStore.sessionId && !checkoutStore.isLoading) {
    console.log('Component mounted with wallet connected on step 2, initializing checkout...')
    await initializeCheckout()
  }
})

// Initialize checkout when wallet connects
async function initializeCheckout() {
  // Prevent duplicate initialization
  if (checkoutStore.isLoading || checkoutStore.sessionId) {
    console.log('⚠️ Checkout already initializing or initialized, skipping...', {
      isLoading: checkoutStore.isLoading,
      sessionId: checkoutStore.sessionId
    })
    return
  }

  try {
    console.log('🚀 Starting checkout initialization...', {
      address: walletStore.address,
      chainId: walletStore.chainId,
      cartItems: cartStore.items.length,
      cartData: cartStore.getCartData()
    })
    
    // Step 1: Create session
    console.log('📝 Step 1: Creating session...')
    const sessionResult = await checkoutStore.createSession(cartStore.getCartData())
    console.log('✅ Step 1 complete - Session created:', {
      sessionId: checkoutStore.sessionId,
      sessionData: sessionResult
    })
    
    if (!checkoutStore.sessionId) {
      throw new Error('Session ID is missing after creation')
    }
    
    // Step 2: Request purchase message
    console.log('📝 Step 2: Requesting purchase message...', {
      walletAddress: walletStore.address,
      chainId: walletStore.chainId
    })
    await checkoutStore.requestMessage(
      walletStore.address,
      walletStore.chainId
    )
    console.log('✅ Step 2 complete - Message requested, moving to step 3')
    
    // Move to payment step
    currentStep.value = 3
    console.log('✅ Checkout initialization complete, moved to step 3')
  } catch (error) {
    console.error('❌ Checkout initialization failed:', error)
    console.error('   Error details:', {
      message: error.message,
      stack: error.stack,
      checkoutError: checkoutStore.error,
      checkoutStatus: checkoutStore.status
    })
    // Error is already set in checkoutStore.error, so it will be displayed
  }
}

// Handle payment signing
async function handlePayment() {
  console.log('🔐 handlePayment called', {
    canPay: checkoutStore.canPay,
    messageData: checkoutStore.messageData,
    status: checkoutStore.status,
    isSigning: isSigning.value
  })
  
  if (!checkoutStore.messageData) {
    console.error('❌ Cannot pay: messageData is missing')
    checkoutStore.error = 'Payment message not available. Please try again.'
    return
  }
  
  if (!checkoutStore.canPay) {
    console.error('❌ Cannot pay:', {
      canPay: checkoutStore.canPay,
      status: checkoutStore.status,
      hasMessageData: !!checkoutStore.messageData
    })
    return
  }
  
  try {
    isSigning.value = true
    console.log('📝 Getting typed data for signing...')
    console.log('📋 Full messageData:', checkoutStore.messageData)
    
    // Validate messageData structure
    if (!checkoutStore.messageData.domain) {
      throw new Error('Missing domain in message data')
    }
    if (!checkoutStore.messageData.types) {
      throw new Error('Missing types in message data')
    }
    if (!checkoutStore.messageData.primary_type && !checkoutStore.messageData.primaryType) {
      throw new Error('Missing primary_type in message data')
    }
    if (!checkoutStore.messageData.message) {
      throw new Error('Missing message in message data')
    }
    
    // Get the typed data for signing
    // Handle both snake_case and camelCase
    const typedData = {
      domain: checkoutStore.messageData.domain,
      types: checkoutStore.messageData.types,
      primaryType: checkoutStore.messageData.primary_type || checkoutStore.messageData.primaryType,
      message: checkoutStore.messageData.message
    }
    
    console.log('✍️ Requesting signature from wallet...', {
      domain: typedData.domain,
      primaryType: typedData.primaryType,
      hasTypes: !!typedData.types,
      hasMessage: !!typedData.message
    })
    
    if (!typedData.primaryType) {
      throw new Error('primaryType is null or undefined')
    }
    
    // Sign with wallet
    const signature = await walletStore.signMessage(typedData)
    console.log('✅ Signature received:', signature.substring(0, 20) + '...')
    
    // Submit signature
    console.log('📤 Submitting signature to backend...')
    await checkoutStore.submitSignature(signature, walletStore.address, walletStore.chainId)
    console.log('✅ Payment completed!')
    
    // Clear cart and redirect
    cartStore.clearCart()
    router.push('/success')
    
  } catch (error) {
    console.error('❌ Payment failed:', error)
    console.error('   Error details:', {
      message: error.message,
      stack: error.stack,
      response: error.response?.data
    })
    checkoutStore.error = error.message || 'Payment failed. Please try again.'
  } finally {
    isSigning.value = false
  }
}

// Go to next step
function nextStep() {
  if (currentStep.value < 3 && canProceed.value) {
    currentStep.value++
  }
}

// Go to a specific step
function goToStep(stepId) {
  if (stepId >= 1 && stepId <= 3 && stepId <= currentStep.value) {
    // If going back from step 3, reset checkout state
    if (currentStep.value === 3 && stepId < 3) {
      checkoutStore.reset()
    }
    currentStep.value = stepId
  }
}

// Cleanup on unmount
onUnmounted(() => {
  if (checkoutStore.status !== 'completed') {
    checkoutStore.cancelSession()
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-3xl font-bold text-white mb-4">Checkout</h1>
      <p class="text-slate-400">Complete your purchase with cryptocurrency</p>
    </div>

    <!-- Steps Indicator -->
    <CheckoutSteps 
      :steps="steps" 
      :current-step="currentStep" 
      @step-click="goToStep"
      class="mb-12" 
    />

    <!-- Step Content -->
    <div class="card">
      <!-- Step 1: Review Cart -->
      <div v-if="currentStep === 1">
        <h2 class="text-xl font-semibold text-white mb-6">Review Your Cart</h2>
        
        <div v-if="cartStore.isEmpty" class="text-center py-12">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-slate-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <p class="text-slate-400">Your cart is empty</p>
          <router-link to="/" class="btn-primary inline-block mt-4">
            Browse Merchandise
          </router-link>
        </div>

        <div v-else class="space-y-4">
          <CartItem 
            v-for="item in cartStore.items" 
            :key="item.id" 
            :item="item"
          />

          <!-- Summary -->
          <div class="border-t border-white/10 pt-6 mt-6">
            <div class="flex justify-between items-center text-lg mb-2">
              <span class="text-slate-400">Total</span>
              <span class="text-2xl font-bold text-white">
                ${{ cartStore.total.toFixed(2) }} USD
              </span>
            </div>
            <p class="text-xs text-slate-500 text-right">
              + network fee (shown in MetaMask)
            </p>
          </div>
        </div>
      </div>

      <!-- Step 2: Connect Wallet -->
      <div v-if="currentStep === 2">
        <h2 class="text-xl font-semibold text-white mb-6">Connect Your Wallet</h2>
        
        <div v-if="walletStore.isConnected" class="text-center py-8">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 
                      flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p class="text-lg text-white mb-2">Wallet Connected!</p>
          <p class="text-slate-400 font-mono text-sm">
            {{ walletStore.address?.slice(0, 6) }}...{{ walletStore.address?.slice(-4) }}
          </p>
          <p class="text-slate-500 text-sm mt-2">
            on {{ walletStore.chainName }}
          </p>
          
          <div v-if="checkoutStore.isLoading" class="mt-6">
            <div class="flex items-center justify-center gap-3 text-coinsub-400">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Preparing payment...</span>
            </div>
          </div>

          <!-- Error message -->
          <div v-if="checkoutStore.error" class="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
            <div class="flex items-start gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p class="text-red-400 font-medium text-sm">Error</p>
                <p class="text-red-300/80 text-sm mt-1">{{ checkoutStore.error }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-8">
          <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-coinsub-500/20 to-indigo-500/20 
                      flex items-center justify-center border border-white/10">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-coinsub-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          
          <p class="text-slate-400 mb-6">
            Connect your wallet to pay with cryptocurrency
          </p>

          <!-- Testnet USDC Faucet Info -->
          <div class="mb-6 p-4 rounded-xl bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border border-blue-500/20">
            <div class="flex items-start gap-3">
              <div class="flex-shrink-0 mt-0.5">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div class="flex-1">
                <p class="text-sm text-slate-300 mb-2">
                  Need testnet USDC? Get up to 1 USDC free from Circle's faucet every 2 hours.
                </p>
                <a 
                  href="https://faucet.circle.com/" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Get Testnet USDC
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>
          </div>

          <button @click="walletStore.connect" class="btn-primary">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Connect with WalletConnect
          </button>

          <div class="mt-6 flex flex-wrap justify-center gap-4 text-sm text-slate-500">
            <span>Supports:</span>
            <span class="text-slate-400">MetaMask</span>
            <span class="text-slate-400">Rainbow</span>
            <span class="text-slate-400">Coinbase Wallet</span>
            <span class="text-slate-400">Trust Wallet</span>
            <span class="text-slate-400">+ more</span>
          </div>
        </div>
      </div>

      <!-- Step 3: Confirm Payment -->
      <div v-if="currentStep === 3">
        <h2 class="text-xl font-semibold text-white mb-6">Confirm Payment</h2>

        <div class="space-y-6">
          <!-- Order Summary -->
          <div class="bg-slate-800/50 rounded-xl p-6">
            <h3 class="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
              Order Summary
            </h3>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-slate-400">Items</span>
                <span class="text-white">{{ cartStore.itemCount }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Subtotal</span>
                <span class="text-white">${{ cartStore.subtotal.toFixed(2) }}</span>
              </div>
              <div class="flex justify-between pt-2 border-t border-white/10">
                <div class="flex flex-col">
                  <span class="text-slate-400">Total</span>
                  <span class="text-xs text-slate-500 mt-1">+ network fee</span>
                </div>
                <div class="flex flex-col items-end">
                  <span class="text-xl font-bold text-white">
                    ${{ cartStore.total.toFixed(2) }} USD
                  </span>
                  <span class="text-xs text-slate-500 mt-1">(shown in MetaMask)</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Payment Details -->
          <div class="bg-slate-800/50 rounded-xl p-6">
            <h3 class="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
              Payment Details
            </h3>
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-slate-400">Wallet</span>
                <span class="text-white font-mono text-sm">
                  {{ walletStore.address?.slice(0, 10) }}...{{ walletStore.address?.slice(-8) }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Network</span>
                <span class="text-white">{{ walletStore.chainName }}</span>
              </div>
              <div v-if="checkoutStore.sessionId" class="flex justify-between">
                <span class="text-slate-400">Session ID</span>
                <span class="text-slate-500 font-mono text-xs">
                  {{ checkoutStore.sessionId }}
                </span>
              </div>
            </div>
          </div>

          <!-- Error Message -->
          <div v-if="checkoutStore.error" class="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
            <div class="flex items-start gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p class="text-red-400 font-medium">Payment Error</p>
                <p class="text-red-300/80 text-sm mt-1">{{ checkoutStore.error }}</p>
              </div>
            </div>
          </div>

          <!-- Sign Button -->
          <button 
            @click="handlePayment"
            :disabled="!checkoutStore.canPay || isSigning"
            class="w-full btn-primary py-4 text-lg flex items-center justify-center whitespace-nowrap"
          >
            <template v-if="isSigning">
              <svg class="animate-spin h-5 w-5 mr-2 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Confirming in wallet...</span>
            </template>
            <template v-else>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span>Sign & Pay ${{ cartStore.total.toFixed(2) }}</span>
            </template>
          </button>

          <p class="text-center text-sm text-slate-500">
            You'll be asked to sign a message in your wallet to authorize this payment.
            <span class="block mt-1 text-xs">Network fees will be displayed in MetaMask</span>
          </p>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex justify-end mt-8 pt-6 border-t border-white/10">
        <button 
          v-if="currentStep === 2 && walletStore.isConnected && !checkoutStore.isLoading"
          @click="initializeCheckout"
          :disabled="checkoutStore.isLoading"
          class="btn-primary whitespace-nowrap"
        >
          Continue
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 ml-2 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </button>
        <button 
          v-else-if="currentStep < 3 && currentStep !== 2"
          @click="nextStep"
          :disabled="!canProceed"
          class="btn-primary whitespace-nowrap"
        >
          Continue
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 ml-2 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
