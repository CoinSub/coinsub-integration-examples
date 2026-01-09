<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <div class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex justify-between items-center">
          <h1 class="text-2xl font-bold text-gray-900">Payment History</h1>
          <button
            @click="handleLogout"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Logout
          </button>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="bg-white rounded-lg shadow p-4 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label for="status" class="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              id="status"
              v-model="filters.status"
              @change="fetchPayments"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="">All</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div class="md:col-span-2 flex items-end">
            <button
              @click="fetchPayments"
              :disabled="loading"
              class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ loading ? 'Loading...' : 'Refresh' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading && payments.length === 0" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <p class="mt-2 text-gray-600">Loading payments...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p class="text-red-800">{{ error }}</p>
      </div>

      <!-- Payments List -->
      <div v-else-if="payments.length > 0" class="bg-white shadow rounded-lg overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Payment ID
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Transaction
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="payment in payments" :key="payment.id">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                  {{ payment.id }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <span v-if="payment.display_amount !== undefined">
                    {{ formatAmount(payment.display_amount) }} {{ payment.token_symbol || 'USDC' }}
                  </span>
                  <span v-else>
                    {{ payment.amount }} {{ payment.currency || 'USDC' }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span
                    :class="{
                      'bg-green-100 text-green-800': payment.status === 'completed' || payment.status === 'confirmed',
                      'bg-yellow-100 text-yellow-800': payment.status === 'pending',
                      'bg-red-100 text-red-800': payment.status === 'failed'
                    }"
                    class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                  >
                    {{ payment.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ formatDate(payment.transaction_date || payment.payment_date || payment.created_at) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <a
                    v-if="payment.confirmation_url || payment.block_explorer_url"
                    :href="payment.confirmation_url || payment.block_explorer_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-indigo-600 hover:text-indigo-900 font-mono text-xs"
                  >
                    {{ truncateHash(payment.txhash || payment.transaction_hash) }}
                  </a>
                  <span v-else class="text-gray-400">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="bg-white rounded-lg shadow p-12 text-center">
        <p class="text-gray-500">No payments found.</p>
      </div>

      <!-- Count -->
      <div v-if="payments.length > 0" class="mt-4 text-sm text-gray-600 text-center">
        Showing {{ payments.length }} payment{{ payments.length !== 1 ? 's' : '' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const payments = ref([])
const loading = ref(false)
const error = ref('')
const filters = ref({
  status: '',
  agreement: null
})

const getAuthToken = () => {
  return sessionStorage.getItem('admin_token')
}

const fetchPayments = async () => {
  const token = getAuthToken()
  if (!token) {
    router.push('/admin/login')
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await axios.post(
      '/api/admin/payments',
      {
        agreement: filters.value.agreement,
        status: filters.value.status
      },
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (response.data.success) {
      payments.value = response.data.payments || []
    } else {
      error.value = response.data.error || 'Failed to fetch payments'
    }
  } catch (err) {
    if (err.response?.status === 401) {
      sessionStorage.removeItem('admin_token')
      router.push('/admin/login')
    } else {
      error.value = err.response?.data?.error || 'Failed to fetch payments. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

const handleLogout = () => {
  sessionStorage.removeItem('admin_token')
  router.push('/admin/login')
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateString
  }
}

const formatAmount = (amount) => {
  if (amount === undefined || amount === null) return '-'
  // Format to show up to 6 decimal places, removing trailing zeros
  return parseFloat(amount.toFixed(6)).toString()
}

const truncateHash = (hash) => {
  if (!hash) return ''
  return `${hash.substring(0, 6)}...${hash.substring(hash.length - 4)}`
}

onMounted(() => {
  const token = getAuthToken()
  if (!token) {
    router.push('/admin/login')
  } else {
    fetchPayments()
  }
})
</script>
