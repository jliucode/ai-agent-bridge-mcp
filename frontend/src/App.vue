<template>
  <div class="app">
    <header class="app-header">
      <h1>AI Agent Bridge</h1>
      <span class="ws-status" :class="{ connected: ws.connected }">
        {{ ws.connected ? 'Live' : 'Disconnected' }}
      </span>
    </header>
    <main class="app-main">
      <StatsBar :stats="stats" />
      <div class="columns">
        <AgentDashboard />
        <TaskPanel />
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { useAgentStore } from './stores/agent'
import { useTaskStore } from './stores/task'
import { useWebSocketStore } from './stores/websocket'
import { fetchStats } from './api'
import { onWsMessage } from './api'
import StatsBar from './components/StatsBar.vue'
import AgentDashboard from './components/AgentDashboard.vue'
import TaskPanel from './components/TaskPanel.vue'

const agentStore = useAgentStore()
const taskStore = useTaskStore()
const ws = useWebSocketStore()

const stats = reactive({
  total_agents: 0, online_agents: 0, busy_agents: 0,
  total_tasks: 0, pending_tasks: 0, in_progress_tasks: 0,
  completed_tasks: 0, failed_tasks: 0, offline_agents: 0,
})

async function loadStats() {
  try { Object.assign(stats, await fetchStats()) } catch { /* ignore */ }
}

onMounted(() => {
  ws.connect()
  agentStore.startListening()
  taskStore.startListening()
  loadStats()
  // Refresh stats on every WS event
  onWsMessage(() => loadStats())
  // Periodic stats refresh
  setInterval(loadStats, 10000)
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f4f6; color: #1f2937; }
</style>

<style scoped>
.app { min-height: 100vh; }
.app-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 14px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.app-header h1 { font-size: 1.2rem; font-weight: 700; }
.ws-status { font-size: .7rem; padding: 4px 10px; border-radius: 999px; background: #f3f4f6; color: #9ca3af; }
.ws-status.connected { background: #dcfce7; color: #15803d; }
.app-main { max-width: 1200px; margin: 0 auto; padding: 20px; display: flex; flex-direction: column; gap: 20px; }
.columns { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; }
@media (max-width: 768px) {
  .columns { grid-template-columns: 1fr; }
}
</style>
