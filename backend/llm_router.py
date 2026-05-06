"""LLM-based routing for Bridge Server."""
import json
import asyncio
from typing import Optional
import httpx

from config import DASHSCOPE_API_KEY, DASHSCOPE_MODEL_NAME


BRIDGE_ROUTE_PROMPT = """You are a task routing decision assistant. Select the most suitable target Agent based on the following information.

## Task Information
- Type: {task_type}
- Description: {description}
- Required Skills: {required_skills}
- Target Project: {target_project}

## Candidate Agent List
{candidates_json}

## Selection Criteria
1. Skill Match: Agent must have required skills
2. Status Priority: IDLE > BUSY
3. Project Relevance: Project name matching task preferred
4. Load Balancing: Select agent with fewer tasks when equal

## Output Format
Return JSON:
{"selected_agent_id": "xxx", "reason": "selection reason", "confidence": 0.8}
"""


class LLMRouter:
    """LLM-based routing decision."""

    def __init__(self):
        self.enabled = bool(DASHSCOPE_API_KEY)  # Enabled when API key is set
        self.provider = "qwen"
        self.api_key = DASHSCOPE_API_KEY
        self.model = DASHSCOPE_MODEL_NAME
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
            target_project=target_project or "Not specified",
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