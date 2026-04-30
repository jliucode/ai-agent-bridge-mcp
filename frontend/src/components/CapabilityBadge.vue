<template>
  <span class="capability-badge" :class="kind">{{ label }}</span>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  kind: { type: String, default: 'skill' }, // 'skill' | 'mcp'
})
</script>

<style scoped>
.capability-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 500;
}
.capability-badge.skill {
  background: #dbeafe;
  color: #1d4ed8;
}
.capability-badge.mcp {
  background: #dcfce7;
  color: #15803d;
}
</style>
