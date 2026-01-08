import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

/**
 * Checkout Store
 * 
 * Manages the Coinsub purchase session flow:
 * 1. Create session with cart data
 * 2. Request purchase message for signing
 * 3. Submit signed message to complete payment
 */
export const useCheckoutStore = defineStore('checkout', () => {
  // State
  const sessionId = ref(null)
  const sessionData = ref(null)
  const messageData = ref(null)
  const status = ref('idle') // idle, creating, ready, signing, processing, completed, error
  const error = ref(null)
  const transactionHash = ref(null)
  const paymentId = ref(null)

  // Computed
  const isLoading = computed(() => 
    ['creating', 'signing', 'processing'].includes(status.value)
  )

  const canPay = computed(() => 
    status.value === 'ready' && messageData.value
  )

  const isComplete = computed(() => 
    status.value === 'completed'
  )

  // Actions
  
  /**
   * Step 1: Create a purchase session
   * Sends cart data to backend, which creates a session with Coinsub
   */
  async function createSession(cartData) {
    try {
      status.value = 'creating'
      error.value = null

      const response = await api.post('/create-session', cartData)
      
      sessionId.value = response.data.session_id
      sessionData.value = response.data
      status.value = 'created'

      return response.data
    } catch (e) {
      console.error('Failed to create session:', e)
      error.value = e.response?.data?.error || e.message || 'Failed to create session'
      status.value = 'error'
      throw e
    }
  }

  /**
   * Step 2: Request purchase message
   * Gets the EIP-712 typed data that the user needs to sign
   */
  async function requestMessage(walletAddress, chainId) {
    if (!sessionId.value) {
      throw new Error('No active session')
    }

    try {
      status.value = 'creating'
      error.value = null

      const response = await api.post(`/session/${sessionId.value}/message`, {
        wallet_address: walletAddress,
        chain_id: chainId
      })

      messageData.value = response.data
      status.value = 'ready'

      return response.data
    } catch (e) {
      console.error('Failed to request message:', e)
      error.value = e.response?.data?.error || e.message || 'Failed to request message'
      status.value = 'error'
      throw e
    }
  }

  /**
   * Step 3: Submit signed message
   * Sends the signature to backend to complete the payment
   */
  async function submitSignature(signature, walletAddress) {
    if (!sessionId.value) {
      throw new Error('No active session')
    }

    try {
      status.value = 'processing'
      error.value = null

      const response = await api.post(`/session/${sessionId.value}/sign`, {
        signature,
        wallet_address: walletAddress,
        message_id: messageData.value?.message_id
      })

      transactionHash.value = response.data.transaction_hash
      paymentId.value = response.data.payment_id
      status.value = 'completed'

      return response.data
    } catch (e) {
      console.error('Failed to submit signature:', e)
      error.value = e.response?.data?.error || e.message || 'Failed to complete payment'
      status.value = 'error'
      throw e
    }
  }

  /**
   * Poll for session status updates
   */
  async function checkStatus() {
    if (!sessionId.value) return null

    try {
      const response = await api.get(`/session/${sessionId.value}/status`)
      return response.data
    } catch (e) {
      console.error('Failed to check status:', e)
      return null
    }
  }

  /**
   * Cancel the current session
   */
  async function cancelSession() {
    if (!sessionId.value) return

    try {
      await api.post(`/session/${sessionId.value}/cancel`)
    } catch (e) {
      console.error('Failed to cancel session:', e)
    }

    reset()
  }

  /**
   * Reset checkout state
   */
  function reset() {
    sessionId.value = null
    sessionData.value = null
    messageData.value = null
    status.value = 'idle'
    error.value = null
    transactionHash.value = null
    paymentId.value = null
  }

  return {
    // State
    sessionId,
    sessionData,
    messageData,
    status,
    error,
    transactionHash,
    paymentId,

    // Computed
    isLoading,
    canPay,
    isComplete,

    // Actions
    createSession,
    requestMessage,
    submitSignature,
    checkStatus,
    cancelSession,
    reset
  }
})
