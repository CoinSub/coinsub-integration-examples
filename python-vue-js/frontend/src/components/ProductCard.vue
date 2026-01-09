<script setup>
import { ref } from 'vue'

const props = defineProps({
  product: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['add-to-cart'])

const isAdding = ref(false)

async function handleAddToCart() {
  isAdding.value = true
  emit('add-to-cart', props.product)
  
  // Brief animation feedback
  await new Promise(resolve => setTimeout(resolve, 300))
  isAdding.value = false
}
</script>

<template>
  <div class="card-hover group overflow-hidden">
    <!-- Image -->
    <div class="relative h-48 -mx-6 -mt-6 mb-4 overflow-hidden">
      <img 
        :src="product.image" 
        :alt="product.name"
        class="w-full h-full object-cover transition-transform duration-500 
               group-hover:scale-110"
      />
      <div class="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
      
      <!-- Category badge -->
      <div class="absolute top-4 left-4">
        <span class="badge-info text-xs uppercase tracking-wider">
          {{ product.category }}
        </span>
      </div>
    </div>

    <!-- Content -->
    <div class="space-y-3">
      <h3 class="text-xl font-semibold text-white group-hover:text-coinsub-400 
                 transition-colors">
        {{ product.name }}
      </h3>
      
      <p class="text-slate-400 text-sm line-clamp-2">
        {{ product.description }}
      </p>

      <div class="flex items-center justify-between pt-4">
        <div class="flex items-baseline gap-1">
          <span class="text-2xl font-bold text-white">
            ${{ product.price.toFixed(2) }}
          </span>
          <span class="text-sm text-slate-500">USD</span>
        </div>

        <button 
          @click="handleAddToCart"
          :disabled="isAdding"
          class="btn-primary text-sm py-2 px-4"
        >
          <Transition
            mode="out-in"
            enter-active-class="transition-all duration-200"
            enter-from-class="opacity-0 scale-50"
            enter-to-class="opacity-100 scale-100"
            leave-active-class="transition-all duration-200"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-50"
          >
            <span v-if="isAdding" class="flex items-center gap-2">
              <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Added
            </span>
            <span v-else class="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Add to Cart
            </span>
          </Transition>
        </button>
      </div>
    </div>
  </div>
</template>
