<template>
  <span class="status-indicator" :style="{ backgroundColor: color }" :title="status"></span>
</template>

<script setup>
import { computed } from 'vue'
import { statusColor } from '../utils/format'

const props = defineProps({ status: { type: String, default: 'OFFLINE' } })
const color = computed(() => statusColor(props.status))
</script>

<style scoped>
.status-indicator {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
</style>
