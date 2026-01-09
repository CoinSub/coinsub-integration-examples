import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createWeb3Modal, defaultWagmiConfig } from '@web3modal/wagmi'
import { 
  mainnet, 
  polygon, 
  base,
  sepolia,
  polygonAmoy,
  baseSepolia
} from 'viem/chains'
import { getAccount, disconnect, signTypedData, watchAccount, reconnect } from '@wagmi/core'

// WalletConnect Project ID - Get yours at https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'YOUR_PROJECT_ID'

// Determine environment (defaults to 'test' for safety)
const isTestMode = import.meta.env.VITE_COINSUB_ENV !== 'production'

// Configure chains based on environment
// Test mode: testnets for development
// Production: mainnets for live transactions
const chains = isTestMode 
  ? [
      sepolia,           // Ethereum Sepolia Testnet
      polygonAmoy,       // Polygon Amoy Testnet
      baseSepolia        // Base Sepolia Testnet
    ]
  : [
      mainnet,           // Ethereum Mainnet
      polygon,           // Polygon Mainnet
      base               // Base Mainnet
    ]

// Wagmi configuration
const metadata = {
  name: 'Coinsub Demo',
  description: 'Pay with cryptocurrency using Coinsub',
  url: window.location.origin,
  icons: [`${window.location.origin}/coinsub.svg`]
}

const wagmiConfig = defaultWagmiConfig({
  chains,
  projectId,
  metadata,
  enableWalletConnect: true,
  enableInjected: true,
  enableEIP6963: true,
  enableCoinbase: true
})

// Create Web3Modal
let web3Modal = null
if (typeof window !== 'undefined') {
  web3Modal = createWeb3Modal({
    wagmiConfig,
    projectId,
    chains,
    themeMode: 'dark',
    themeVariables: {
      '--w3m-accent': '#0ea5e9',
      '--w3m-border-radius-master': '12px'
    },
    // Feature MetaMask as a top choice
    featuredWalletIds: ['io.metamask'],
    // Include other popular wallets
    includeWalletIds: [
      'io.metamask',
      'com.coinbase.wallet',
      'me.rainbow',
      'com.trustwallet.app',
      'io.zerion.wallet'
    ]
  })
}

export const useWalletStore = defineStore('wallet', () => {
  // State
  const address = ref(null)
  const chainId = ref(null)
  const isConnecting = ref(false)
  const error = ref(null)

  // Computed
  const isConnected = computed(() => !!address.value)

  const chainName = computed(() => {
    const chain = chains.find(c => c.id === chainId.value)
    return chain?.name || 'Unknown'
  })

  const supportedChains = computed(() => chains.map(c => ({
    id: c.id,
    name: c.name,
    nativeCurrency: c.nativeCurrency
  })))

  // Initialize - check for existing connection
  async function init() {
    try {
      await reconnect(wagmiConfig)
      const account = getAccount(wagmiConfig)
      if (account.isConnected) {
        address.value = account.address
        chainId.value = account.chainId
      }
    } catch (e) {
      console.warn('Failed to reconnect:', e)
    }

    // Watch for account changes
    watchAccount(wagmiConfig, {
      onChange: (account) => {
        if (account.isConnected) {
          address.value = account.address
          chainId.value = account.chainId
        } else {
          address.value = null
          chainId.value = null
        }
      }
    })
  }

  // Actions
  async function connect() {
    try {
      isConnecting.value = true
      error.value = null
      
      if (web3Modal) {
        await web3Modal.open()
      }
    } catch (e) {
      console.error('Failed to connect wallet:', e)
      error.value = e.message
    } finally {
      isConnecting.value = false
    }
  }

  async function disconnectWallet() {
    try {
      await disconnect(wagmiConfig)
      address.value = null
      chainId.value = null
    } catch (e) {
      console.error('Failed to disconnect:', e)
    }
  }

  /**
   * Sign an EIP-712 typed data message
   * This is used for signing purchase messages from Coinsub
   */
  async function signMessage(typedData) {
    if (!address.value) {
      throw new Error('Wallet not connected')
    }

    try {
      const signature = await signTypedData(wagmiConfig, {
        domain: typedData.domain,
        types: typedData.types,
        primaryType: typedData.primaryType,
        message: typedData.message
      })
      
      return signature
    } catch (e) {
      console.error('Failed to sign message:', e)
      throw new Error(e.shortMessage || e.message || 'Failed to sign message')
    }
  }

  // Initialize on store creation
  init()

  return {
    // State
    address,
    chainId,
    isConnecting,
    error,
    
    // Computed
    isConnected,
    chainName,
    supportedChains,
    
    // Actions
    connect,
    disconnect: disconnectWallet,
    signMessage
  }
})
