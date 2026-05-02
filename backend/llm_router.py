"""LLM-based routing for Bridge Server."""
import json
import asyncio
from typing import Optional
import httpx


BRIDGE_ROUTE_PROMPT = """你是一个任务路由决策助手。根据以下信息选择最合适的目标 Agent。

## 任务信息
- 类型: {task_type}
- 描述: {description}
- 需要技能: {required_skills}
- 目标项目: {target_project}

## 候选 Agent 列表
{candidates_json}

## 选择标准
1. 技能匹配：Agent 必须有所需技能
2. 状态优先：IDLE > BUSY
3. 项目相关性：项目名与任务相关的优先
4. 负载均衡：同等条件选任务少的

## 输出格式
返回 JSON：
{"selected_agent_id": "xxx", "reason": "选择理由", "confidence": 0.8}
"""


class LLMRouter:
    """LLM-based routing decision."""

    def __init__(self):
        self.enabled = True  # Check config
        self.provider = "qwen"
        self.api_key = ""  # From config
        self.model = "qwen-max"
        self.timeout = 5.0

    async def route(
        self,
        task_type: str,
        description: str,
        required_skills: list[str],
        target_project: Optional[str],
        candidates: list[dict],
    ) -> Optional[dict]:
        """Make routing decision with LLM."""
        if not self.enabled or not self.api_key:
            return None

        if not candidates:
            return None

        prompt = BRIDGE_ROUTE_PROMPT.format(
            task_type=task_type,
            description=description,
            required_skills=", ".join(required_skills),
            target_project=target_project or "未指定",
            candidates_json=json.dumps(candidates, ensure_ascii=False, indent=2),
        )

        try:
            result = await self._call_llm(prompt)
            decision = json.loads(result)

            if decision.get("confidence", 0) < 0.5:
                return None

            agent_id = decision.get("selected_agent_id")
            for c in candidates:
                if c["agent_id"] == agent_id:
                    return {"agent": c, "reason": decision.get("reason")}

            return None

        except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
            return None

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        if self.provider == "qwen":
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": self.model,
                "input": {"prompt": prompt},
                "parameters": {"result_format": "text"},
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, headers=headers, json=body, timeout=self.timeout
                )
                data = resp.json()
                return data["output"]["text"]

        raise ValueError(f"Unknown LLM provider: {self.provider}")

    def fallback_route(self, candidates: list[dict]) -> dict:
        """Fallback routing without LLM."""
        idle = [a for a in candidates if a["status"] == "IDLE"]
        if idle:
            return {"agent": idle[0], "reason": "Fallback: IDLE agent"}

        sorted_agents = sorted(candidates, key=lambda a: a.get("current_tasks", 0))
        return {"agent": sorted_agents[0], "reason": "Fallback: least tasks"}


llm_router = LLMRouter()