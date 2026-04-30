import { defineStore } from 'pinia'
import { fetchAgents } from '../api'
import { onWsMessage } from '../api'

export const useAgentStore = defineStore('agents', {
  state: () => ({
    agents: [],
    loading: false,
  }),
  actions: {
    async load() {
      this.loading = true
      try {
        const data = await fetchAgents()
        this.agents = data.agents || []
      } finally {
        this.loading = false
      }
    },
    _upsert(agent) {
      const idx = this.agents.findIndex((a) => a.id === agent.id)
      if (idx >= 0) this.agents[idx] = agent
      else this.agents.push(agent)
    },
    _remove(id) {
      this.agents = this.agents.filter((a) => a.id !== id)
    },
    startListening() {
      onWsMessage((msg) => {
        switch (msg.type) {
          case 'agent.online':
          case 'agent.updated':
            this._upsert(msg.data)
            break
          case 'agent.offline':
            this._upsert(msg.data)
            break
        }
      })
    },
  },
})
