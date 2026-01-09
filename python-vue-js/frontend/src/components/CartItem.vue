<script setup>
import { useCartStore } from '../stores/cart'

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
})

const cartStore = useCartStore()

function updateQuantity(delta) {
  cartStore.updateQuantity(props.item.id, props.item.quantity + delta)
}

function removeItem() {
  cartStore.removeItem(props.item.id)
}
</script>

<template>
  <div class="flex items-center gap-4 p-4 bg-slate-800/30 rounded-xl group">
    <!-- Image -->
    <div class="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
      <img 
        :src="item.image" 
        :alt="item.name"
        class="w-full h-full object-cover"
      />
    </div>

    <!-- Details -->
    <div class="flex-1 min-w-0">
      <h3 class="text-white font-medium truncate">{{ item.name }}</h3>
      <p class="text-slate-400 text-sm truncate">{{ item.description }}</p>
    </div>

    <!-- Quantity Controls -->
    <div class="flex items-center gap-2">
      <button 
        @click="updateQuantity(-1)"
        class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 
               text-slate-400 hover:text-white transition-colors
               flex items-center justify-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
        </svg>
      </button>
      
      <span class="w-8 text-center text-white font-medium">
        {{ item.quantity }}
      </span>
      
      <button 
        @click="updateQuantity(1)"
        class="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 
               text-slate-400 hover:text-white transition-colors
               flex items-center justify-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
      </button>
    </div>

    <!-- Price -->
    <div class="text-right min-w-[80px]">
      <div class="text-white font-semibold">
        ${{ (item.price * item.quantity).toFixed(2) }}
      </div>
      <div class="text-slate-500 text-sm">
        ${{ item.price.toFixed(2) }} each
      </div>
    </div>

    <!-- Remove Button -->
    <button 
      @click="removeItem"
      class="p-2 text-slate-500 hover:text-red-400 transition-colors 
             opacity-0 group-hover:opacity-100"
      title="Remove item"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
      </svg>
    </button>
  </div>
</template>
