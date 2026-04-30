<template>
  <div class="task-panel">
    <div class="panel-header">
      <h2>Tasks</h2>
      <button class="btn-refresh" @click="load">Refresh</button>
    </div>
    <div class="task-list" v-if="tasks.length">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-item"
        :class="task.status"
      >
        <div class="task-top">
          <span class="task-title">{{ task.title }}</span>
          <span class="task-status" :style="{ color: taskStatusColor(task.status) }">
            {{ task.status }}
          </span>
        </div>
        <div class="task-meta">
          <span :title="task.from_agent">{{ task.from_agent?.slice(0, 8) }}</span>
          <span class="arrow">→</span>
          <span :title="task.to_agent">{{ task.to_agent?.slice(0, 8) }}</span>
          <span class="task-time">{{ formatRelativeTime(task.created_at) }}</span>
        </div>
        <div class="task-result" v-if="task.result">{{ task.result }}</div>
      </div>
    </div>
    <div class="empty" v-else>No tasks yet</div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useTaskStore } from '../stores/task'
import { formatRelativeTime, taskStatusColor } from '../utils/format'

const store = useTaskStore()
const tasks = computed(() => store.tasks)

function load() { store.load() }
onMounted(() => load())
</script>

<style scoped>
.task-panel {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  padding: 16px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.panel-header h2 { margin: 0; font-size: 1rem; }
.btn-refresh {
  border: 1px solid #e5e7eb;
  background: #fff;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: .75rem;
}
.btn-refresh:hover { background: #f3f4f6; }
.task-list { display: flex; flex-direction: column; gap: 8px; }
.task-item {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f9fafb;
  border-left: 3px solid #d1d5db;
}
.task-item.IN_PROGRESS { border-left-color: #3b82f6; }
.task-item.DONE { border-left-color: #22c55e; }
.task-item.FAILED { border-left-color: #ef4444; }
.task-top { display: flex; justify-content: space-between; align-items: center; }
.task-title { font-weight: 600; font-size: .85rem; }
.task-status { font-size: .7rem; font-weight: 600; text-transform: uppercase; }
.task-meta { font-size: .7rem; color: #9ca3af; margin-top: 4px; display: flex; gap: 6px; align-items: center; }
.task-meta span { font-family: monospace; }
.arrow { color: #d1d5db; }
.task-time { margin-left: auto; }
.task-result { font-size: .75rem; color: #374151; margin-top: 6px; padding: 4px 8px; background: #f3f4f6; border-radius: 4px; }
.empty { color: #9ca3af; font-size: .85rem; text-align: center; padding: 20px; }
</style>
