"""CLI table logger for MCP Proxy."""
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live


class ProxyLogger:
    """Rich-based table logger for MCP Proxy."""

    def __init__(self, machine_ip: str = "unknown"):
        self.console = Console()
        self.machine_ip = machine_ip
        self.events: list[dict] = []
        self.stats = {
            "agents_online": 0,
            "tasks_pending": 0,
            "last_hb": None,
        }

    def print_header(self, version: str = "0.1.0"):
        """Print header panel."""
        panel = Panel(
            f"[bold]MCP Proxy v{version}[/bold] — Machine: [cyan]{self.machine_ip}[/cyan]",
            style="blue"
        )
        self.console.print(panel)

    def log_event(
        self,
        event: str,
        target: str,
        status: str,
        details: str,
        status_icon: str = "✅"
    ):
        """Log an event to the table."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.events.append({
            "time": timestamp,
            "event": event,
            "target": target,
            "status": f"{status_icon} {status}",
            "details": details,
        })
        self._render_table()

    def _render_table(self):
        """Render the events table."""
        table = Table(title="MCP Proxy Events")
        table.add_column("Time", style="cyan")
        table.add_column("Event", style="green")
        table.add_column("Target", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="white")

        # Show last 10 events
        for event in self.events[-10:]:
            table.add_row(
                event["time"],
                event["event"],
                event["target"],
                event["status"],
                event["details"],
            )

        self.console.clear()
        self.print_header()
        self.console.print(table)
        self._print_stats()

    def _print_stats(self):
        """Print stats bar."""
        stats_line = (
            f"Agents Online: [cyan]{self.stats['agents_online']}[/cyan] │ "
            f"Tasks Pending: [yellow]{self.stats['tasks_pending']}[/yellow] │ "
            f"Last HB: [green]{self.stats['last_hb'] or 'N/A'}[/green]"
        )
        self.console.print(stats_line)

    def update_stats(self, agents: int = None, tasks: int = None, last_hb: str = None):
        """Update stats."""
        if agents is not None:
            self.stats["agents_online"] = agents
        if tasks is not None:
            self.stats["tasks_pending"] = tasks
        if last_hb is not None:
            self.stats["last_hb"] = last_hb
        self._render_table()

    def log_connected(self, bridge_url: str):
        """Log Bridge connection."""
        self.log_event("CONNECTED", "Bridge", "Online", bridge_url, "✅")

    def log_registered(self, agent_id: str, project: str, skills: list[str]):
        """Log Agent registration."""
        skills_str = ", ".join(skills[:3])
        if len(skills) > 3:
            skills_str += "..."
        short_id = agent_id.split("-")[0]
        self.log_event("REGISTERED", f"{project}-{short_id}", "IDLE", skills_str, "✅")
        self.stats["agents_online"] += 1

    def log_task(self, task_id: str, status: str, details: str, icon: str = "🔄"):
        """Log task event."""
        self.log_event("TASK", f"#{task_id}", status, details, icon)

    def log_heartbeat(self, agent_count: int):
        """Log heartbeat."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_event("HEARTBEAT", f"All ({agent_count})", "OK", "30s interval", "✅")
        self.update_stats(last_hb=timestamp)

    def log_error(self, message: str):
        """Log error."""
        self.log_event("ERROR", "System", "Failed", message, "❌")


logger = ProxyLogger()