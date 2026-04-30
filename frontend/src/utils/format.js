export function formatTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  return d.toLocaleString()
}

export function formatRelativeTime(isoString) {
  if (!isoString) return '—'
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diff = Math.floor((now - then) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function statusColor(status) {
  switch (status) {
    case 'ONLINE': return '#22c55e'
    case 'BUSY': return '#f59e0b'
    case 'IDLE': return '#3b82f6'
    case 'OFFLINE': return '#6b7280'
    default: return '#9ca3af'
  }
}

export function taskStatusColor(status) {
  switch (status) {
    case 'PENDING': return '#6b7280'
    case 'IN_PROGRESS': return '#3b82f6'
    case 'DONE': return '#22c55e'
    case 'FAILED': return '#ef4444'
    default: return '#9ca3af'
  }
}
