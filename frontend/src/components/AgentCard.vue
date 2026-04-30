<template>
  <div class="agent-card">
    <div class="card-header">
      <StatusIndicator :status="agent.status" />
      <h3 class="agent-name">{{ agent.name }}</h3>
      <span class="agent-status-text">{{ agent.status }}</span>
    </div>
    <div class="card-body">
      <div class="info-row">
        <span class="label">Project</span>
        <span class="value">{{ agent.project || '—' }}</span>
      </div>
      <div class="info-row">
        <span class="label">IP</span>
        <span class="value">{{ agent.ip || '—' }}</span>
      </div>
      <div class="info-row">
        <span class="label">Task</span>
        <span class="value">{{ agent.current_task || 'None' }}</span>
      </div>
      <div class="info-row">
        <span class="label">Heartbeat</span>
        <span class="value">{{ formatRelativeTime(agent.last_heartbeat) }}</span>
      </div>
    </div>
    <div class="card-footer">
      <div class="badges" v-if="agent.capabilities">
        <CapabilityBadge
          v-for="s in agent.capabilities.mcp_servers"
          :key="'mcp-' + s"
          :label="s"
          kind="mcp"
        />
        <CapabilityBadge
          v-for="s in agent.capabilities.skills"
          :key="'skill-' + s"
          :label="s"
          kind="skill"
        />
      </div>
      <div class="card-id" :title="agent.id">{{ agent.id?.slice(0, 8) }}</div>
    </div>
  </div>
</template>

<script setup>
import StatusIndicator from './StatusIndicator.vue'
import CapabilityBadge from './CapabilityBadge.vue'
import { formatRelativeTime } from '../utils/format'

defineProps({ agent: { type: Object, required: true } })
</script>

<style scoped>
.agent-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: box-shadow .15s;
}
.agent-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); }
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.agent-name { font-size: 1rem; margin: 0; flex: 1; }
.agent-status-text {
  font-size: .7rem;
  text-transform: uppercase;
  color: #6b7280;
  font-weight: 600;
}
.card-body { display: flex; flex-direction: column; gap: 4px; }
.info-row { display: flex; justify-content: space-between; font-size: .8rem; }
.info-row .label { color: #9ca3af; }
.info-row .value { color: #374151; font-weight: 500; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.card-footer { display: flex; align-items: center; justify-content: space-between; margin-top: auto; }
.badges { display: flex; gap: 4px; flex-wrap: wrap; }
.card-id { font-size: .65rem; color: #d1d5db; font-family: monospace; }
</style>
