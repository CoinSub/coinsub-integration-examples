<script setup>
import { RouterView } from 'vue-router'
import NavBar from './components/NavBar.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <NavBar />
    <main class="flex-1">
      <RouterView />
    </main>
    <footer class="py-6 text-center text-slate-500 text-sm">
      <p>
        Powered by 
        <a href="https://coinsub.io" target="_blank" rel="noopener" 
           class="text-coinsub-400 hover:text-coinsub-300 transition-colors">
          Coinsub
        </a>
        · Integration Example
      </p>
    </footer>
  </div>
</template>
