<script setup>
defineProps({
  steps: {
    type: Array,
    required: true
  },
  currentStep: {
    type: Number,
    required: true
  }
})
</script>

<template>
  <nav aria-label="Progress">
    <ol class="flex items-center justify-between">
      <li 
        v-for="(step, index) in steps" 
        :key="step.id"
        class="relative flex-1"
        :class="{ 'pr-8 sm:pr-20': index !== steps.length - 1 }"
      >
        <!-- Connector line -->
        <div 
          v-if="index !== steps.length - 1"
          class="absolute top-4 left-7 sm:left-8 right-0 h-0.5"
          :class="step.id < currentStep ? 'bg-coinsub-500' : 'bg-slate-700'"
        ></div>

        <div class="flex items-center gap-3 relative">
          <!-- Step circle -->
          <div 
            class="w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm
                   transition-all duration-300"
            :class="{
              'bg-coinsub-500 text-white': step.id === currentStep,
              'bg-coinsub-500/20 text-coinsub-400 border border-coinsub-500/30': step.id < currentStep,
              'bg-slate-800 text-slate-500 border border-slate-700': step.id > currentStep
            }"
          >
            <svg 
              v-if="step.id < currentStep"
              xmlns="http://www.w3.org/2000/svg" 
              class="h-4 w-4" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span v-else>{{ step.id }}</span>
          </div>

          <!-- Step text -->
          <div class="hidden sm:block">
            <div 
              class="font-medium transition-colors duration-300"
              :class="{
                'text-white': step.id <= currentStep,
                'text-slate-500': step.id > currentStep
              }"
            >
              {{ step.name }}
            </div>
            <div class="text-sm text-slate-500">
              {{ step.description }}
            </div>
          </div>
        </div>
      </li>
    </ol>
  </nav>
</template>
