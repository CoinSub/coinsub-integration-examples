<script setup>
const props = defineProps({
  steps: {
    type: Array,
    required: true
  },
  currentStep: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['step-click'])

function handleStepClick(stepId) {
  // Only allow clicking on completed steps or the current step
  if (stepId <= props.currentStep) {
    emit('step-click', stepId)
  }
}
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
        <div class="flex items-center gap-3 relative z-10">
          <!-- Step circle -->
          <button
            v-if="step.id <= currentStep"
            @click="handleStepClick(step.id)"
            class="w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm
                   transition-all duration-300 flex-shrink-0 cursor-pointer
                   hover:scale-110 active:scale-95"
            :class="{
              'bg-coinsub-500 text-white': step.id === currentStep,
              'bg-coinsub-500/20 text-coinsub-400 border border-coinsub-500/30 hover:bg-coinsub-500/30': step.id < currentStep,
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
          </button>
          <div
            v-else
            class="w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm
                   transition-all duration-300 flex-shrink-0
                   bg-slate-800 text-slate-500 border border-slate-700"
          >
            <span>{{ step.id }}</span>
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
