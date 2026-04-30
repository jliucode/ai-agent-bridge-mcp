<template>
  <div class="stats-bar">
    <div class="stat">
      <span class="stat-value">{{ stats.total_agents }}</span>
      <span class="stat-label">Total</span>
    </div>
    <div class="stat online">
      <span class="stat-value">{{ stats.online_agents }}</span>
      <span class="stat-label">Online</span>
    </div>
    <div class="stat busy">
      <span class="stat-value">{{ stats.busy_agents }}</span>
      <span class="stat-label">Busy</span>
    </div>
    <div class="stat">
      <span class="stat-value">{{ stats.total_tasks }}</span>
      <span class="stat-label">Tasks</span>
    </div>
    <div class="stat done">
      <span class="stat-value">{{ stats.completed_tasks }}</span>
      <span class="stat-label">Done</span>
    </div>
    <div class="stat failed">
      <span class="stat-value">{{ stats.failed_tasks }}</span>
      <span class="stat-label">Failed</span>
    </div>
  </div>
</template>

<script setup>
defineProps({ stats: { type: Object, required: true } })
</script>

<style scoped>
.stats-bar {
  display: flex;
  gap: 24px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  flex-wrap: wrap;
}
.stat { text-align: center; }
.stat-value { font-size: 1.5rem; font-weight: 700; display: block; line-height: 1.2; }
.stat-label { font-size: .7rem; color: #9ca3af; text-transform: uppercase; }
.stat.online .stat-value { color: #22c55e; }
.stat.busy .stat-value { color: #f59e0b; }
.stat.done .stat-value { color: #22c55e; }
.stat.failed .stat-value { color: #ef4444; }
</style>
