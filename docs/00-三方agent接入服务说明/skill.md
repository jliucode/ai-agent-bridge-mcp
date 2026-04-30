---
description: AI Agent Bridge — agent 注册、心跳、任务委派与接收
---

# AI Agent Bridge 工作流

你已接入 AI Agent Bridge，可以在多个 AI Agent 之间互派任务、共享结果。
桥接服务提供以下 MCP 工具：`agent_register`、`agent_heartbeat`、`agent_update_status`、`agent_list`、`task_delegate`、`task_update`、`task_list`。

## 一、启动流程

**当用户说"注册到桥"或首次对话时，自动执行以下注册流程：**

1. 调用 `agent_register` 注册当前 agent：
   - `name`: 你的名称，格式建议 `项目名-编号`，如 `claude-code-shop-01`
   - `project`: 当前项目的名称或描述
   - `capabilities`:
     - `mcp_servers`: 列出你所有可用的 MCP（调用 `/mcp` 查看），如 `["gitnexus", "zread", "web-search-prime"]`
     - `skills`: 列出你的 skill（调用 `/help` 查看），如 `["pptx", "commit", "pdf"]`
     - `description`: 一句话描述你的职责，如"负责电商前端代码生成与 Bug 修复"
2. 注册成功后告知用户："✅ 已注册到 Agent Bridge — Dashboard 可见"
3. 若注册失败，提示用户检查 MCP 连接（`/mcp` 面板中确认 agent-bridge 已连接）

## 二、定时心跳

**重要：超过 60 秒无心跳会被标记为 OFFLINE，其他 agent 将无法向你委派任务。**

- 每 30~60 秒自动调用 `agent_heartbeat`
- 在长任务执行期间也要保持心跳
- 用户说"心跳"时手动发送一次
- 心跳无需用户催促，完全后台自动进行

## 三、查看所有 Agent

当用户说以下关键词时触发：
- "查看 agent" / "有什么 agent" / "谁在线" / "agent 列表"

执行步骤：
1. 调用 `agent_list` 获取所有已注册 Agent
2. 以表格形式展示：

```
| 名称 | 项目 | 状态 | MCP | Skills | 当前任务 |
|------|------|------|-----|--------|---------|
| xxx  | xxx  | 🟢 ONLINE | ... | ... | ... |
```

3. 标注可接收任务的 Agent（状态为 ONLINE 或 IDLE），告知用户"以下 agent 可接收任务：..."
4. 标注自己的位置

## 四、委派任务给其他 Agent

当用户说以下关键词时触发：
- "委派给 xxx" / "让 xxx 做" / "派任务给" / "分配给"

执行步骤：
1. 先 `agent_list` 确认目标 agent 存在且状态为 ONLINE 或 IDLE
2. 若用户未指定目标，先展示 agent 列表让用户选择
3. 准备任务描述：
   - `title`: 一句话说清要做什么（如"修复订单接口超时"）
   - `description`: 完整的上下文和期望（含报错信息、相关文件路径、预期行为、约束条件等）
   - `to_agent`: 目标 agent 的 ID（从 agent_list 结果中获取）
4. 调用 `task_delegate` 委派任务
5. 告知用户："📤 任务已委派给 {agent_name}，等待处理中..."
6. **重要**：告知用户"当收到结果时我会及时通知你"

## 五、接收和处理任务

当收到 SSE 事件 `task.assigned` 时（系统自动推送，你无法主动查询）：

1. **立即告知用户**：
   ```
   📥 收到来自 {from_agent} 的任务委派：
   **{title}**
   描述：{description}
   是否接单处理？
   ```

2. **评估任务**：对照自己的 capabilities 判断能否处理

3. **若可处理**（用户确认后）：
   - 调用 `task_update(task_id="{id}", status="IN_PROGRESS")`
   - 告知用户："🔄 正在处理任务..."
   - 执行任务（读取文件、分析、修改、验证）
   - 完成后调用 `task_update(task_id="{id}", status="DONE", result="执行结果摘要")`
   - result 要写清楚：做了什么修改、涉及哪些文件、效果如何

4. **若超出能力范围**：
   - 调用 `task_update(task_id="{id}", status="FAILED", result="无法处理：{具体原因}")`
   - 建议用户可以 `task_delegate` 给更合适的 agent
   - 注意：虽然不能执行代码，但你可以分析问题、给出方案建议

5. **任务进度报告**：在长任务执行中，定期向用户报告进度

## 六、状态管理

根据当前情况主动更新状态：
- 空闲时 → `agent_update_status(status="IDLE")`
- 接到任务开始处理 → `agent_update_status(status="BUSY")`
- 任务完成后 → `agent_update_status(status="IDLE")`

## 七、查询任务

- 用户说"我的任务" → 调用 `task_list` 列出自己的任务
- 以表格展示任务状态（PENDING / IN_PROGRESS / DONE / FAILED）
