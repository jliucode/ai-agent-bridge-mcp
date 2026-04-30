<template>
  <div class="dashboard">
    <h2>Agents ({{ agents.length }})</h2>
    <div class="agents-grid">
      <AgentCard v-for="agent in agents" :key="agent.id" :agent="agent" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgentStore } from '../stores/agent'
import AgentCard from './AgentCard.vue'

const store = useAgentStore()
const agents = computed(() => store.agents)

onMounted(() => store.load())
</script>

<style scoped>
.dashboard h2 { font-size: 1rem; margin: 0 0 12px; color: #374151; }
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
</style>
