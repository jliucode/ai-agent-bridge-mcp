"""Remote agents cache with skill indexing."""
from typing import Optional


class RemoteAgentsCache:
    """Cache and index remote agents by skills."""

    def __init__(self):
        self.agents: dict[str, dict] = {}  # agent_id → info
        self.skills_index: dict[str, list[str]] = {}  # skill → agent_ids
        self.projects_index: dict[str, list[str]] = {}  # project → agent_ids

    def update(self, agents_list: list[dict]):
        """Update cache from Bridge sync."""
        self.agents = {a["agent_id"]: a for a in agents_list}

        # Rebuild indexes
        self.skills_index = {}
        self.projects_index = {}

        for agent in agents_list:
            for skill in agent.get("skills", []):
                self.skills_index.setdefault(skill, []).append(agent["agent_id"])

            project = agent.get("project")
            if project:
                self.projects_index.setdefault(project, []).append(agent["agent_id"])

    def find_by_skill(self, skill: str, project: Optional[str] = None) -> list[dict]:
        """Find agents with given skill."""
        candidates = self.skills_index.get(skill, [])
        if project:
            candidates = [c for c in candidates if self.agents[c]["project"] == project]
        return [self.agents[c] for c in candidates]

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def is_local(self, agent_id: str, local_agent_ids: list[str]) -> bool:
        """Check if agent is local."""
        return agent_id in local_agent_ids

    def select_agent(self, candidates: list[dict]) -> Optional[dict]:
        """Select best agent (load balance)."""
        if not candidates:
            return None

        # Priority: IDLE > least tasks
        idle = [a for a in candidates if a["status"] == "IDLE"]
        if idle:
            return idle[0]

        return min(candidates, key=lambda a: a.get("current_tasks", 0))