import { defineStore } from 'pinia'
import { connectWebSocket } from '../api'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    connected: false,
  }),
  actions: {
    connect() {
      connectWebSocket()
      this.connected = true
    },
  },
})
