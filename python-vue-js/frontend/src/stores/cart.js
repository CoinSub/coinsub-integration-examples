import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCartStore = defineStore('cart', () => {
  // State
  const items = ref([])
  const currency = ref('USD')
  const customerEmail = ref('')

  // Computed
  const itemCount = computed(() => 
    items.value.reduce((sum, item) => sum + item.quantity, 0)
  )

  const subtotal = computed(() => 
    items.value.reduce((sum, item) => sum + (item.price * item.quantity), 0)
  )

  const total = computed(() => subtotal.value)

  const isEmpty = computed(() => items.value.length === 0)

  // Actions
  function addItem(product) {
    const existingItem = items.value.find(item => item.id === product.id)
    
    if (existingItem) {
      existingItem.quantity++
    } else {
      items.value.push({
        ...product,
        quantity: 1
      })
    }
  }

  function removeItem(productId) {
    const index = items.value.findIndex(item => item.id === productId)
    if (index !== -1) {
      items.value.splice(index, 1)
    }
  }

  function updateQuantity(productId, quantity) {
    const item = items.value.find(item => item.id === productId)
    if (item) {
      if (quantity <= 0) {
        removeItem(productId)
      } else {
        item.quantity = quantity
      }
    }
  }

  function clearCart() {
    items.value = []
    customerEmail.value = ''
  }

  function setCustomerEmail(email) {
    customerEmail.value = email
  }

  function getCartData() {
    return {
      items: items.value.map(item => ({
        id: item.id,
        name: item.name,
        price: item.price,
        quantity: item.quantity,
        description: item.description
      })),
      currency: currency.value,
      customer_email: customerEmail.value,
      metadata: {
        source: 'coinsub-demo',
        timestamp: new Date().toISOString()
      }
    }
  }

  return {
    // State
    items,
    currency,
    customerEmail,

    // Computed
    itemCount,
    subtotal,
    total,
    isEmpty,

    // Actions
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    setCustomerEmail,
    getCartData
  }
})
