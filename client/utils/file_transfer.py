"""File transfer utilities for remote skill calls."""
import base64
import tempfile
from pathlib import Path


class FileTransfer:
    """Handle file transfer for remote skill calls."""

    @staticmethod
    def read_files(file_paths: list[str]) -> list[dict]:
        """Read files and encode for transfer."""
        files = []
        for path in file_paths:
            p = Path(path)
            if not p.exists():
                continue

            with open(p, "rb") as f:
                content = base64.b64encode(f.read()).decode()

            files.append({
                "original_path": path,
                "filename": p.name,
                "content": content,
                "size": p.stat().st_size,
            })
        return files

    @staticmethod
    def save_files(files: list[dict], task_id: str) -> list[str]:
        """Save transferred files to temp directory."""
        transfer_dir = Path(tempfile.gettempdir()) / "transfer" / task_id
        transfer_dir.mkdir(parents=True, exist_ok=True)

        local_paths = []
        for file in files:
            local_path = transfer_dir / file["filename"]
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(file["content"]))
            local_paths.append(str(local_path))

        return local_paths

    @staticmethod
    def cleanup(task_id: str):
        """Clean up transferred files."""
        transfer_dir = Path(tempfile.gettempdir()) / "transfer" / task_id
        if transfer_dir.exists():
            for f in transfer_dir.iterdir():
                f.unlink()
            transfer_dir.rmdir()