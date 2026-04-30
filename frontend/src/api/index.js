const API_BASE = '/api'

async function request(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function fetchAgents() {
  return request('/agents')
}

export function fetchAgent(id) {
  return request(`/agents/${encodeURIComponent(id)}`)
}

export function fetchTasks(params = {}) {
  const qs = new URLSearchParams(params).toString()
  return request(`/tasks${qs ? '?' + qs : ''}`)
}

export function fetchTask(id) {
  return request(`/tasks/${encodeURIComponent(id)}`)
}

export function fetchStats() {
  return request('/stats')
}

export function fetchHealth() {
  return request('/health')
}

// ── WebSocket client ──────────────────────────────────────────────────────────

let ws = null
let listeners = []

export function connectWebSocket() {
  if (ws && ws.readyState === WebSocket.OPEN) return

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${location.host}/ws`)

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      listeners.forEach((fn) => fn(msg))
    } catch { /* ignore malformed */ }
  }

  ws.onclose = () => {
    // reconnect after 3 seconds
    setTimeout(connectWebSocket, 3000)
  }
}

export function onWsMessage(fn) {
  listeners.push(fn)
  return () => {
    listeners = listeners.filter((f) => f !== fn)
  }
}
