import { defineStore } from 'pinia'
import { fetchTasks } from '../api'
import { onWsMessage } from '../api'

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
    loading: false,
  }),
  actions: {
    async load() {
      this.loading = true
      try {
        const data = await fetchTasks()
        this.tasks = data.tasks || []
      } finally {
        this.loading = false
      }
    },
    _upsert(task) {
      const idx = this.tasks.findIndex((t) => t.id === task.id)
      if (idx >= 0) this.tasks[idx] = task
      else this.tasks.unshift(task)
    },
    startListening() {
      onWsMessage((msg) => {
        if (msg.type === 'task.created' || msg.type === 'task.updated') {
          this._upsert(msg.data)
        }
      })
    },
  },
})
