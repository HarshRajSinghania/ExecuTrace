from __future__ import annotations

import base64
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from exectrace.core.models import Action, Workflow
from exectrace.storage.json_storage import JsonStorage
from exectrace.utils.logger import get_logger

logger = get_logger(__name__)


class Replayer:
    def __init__(self, storage: JsonStorage | None = None) -> None:
        self.storage = storage or JsonStorage()

    def _signature(self, action: Action) -> str:
        serialized = f"{action.action_type}|{action.payload}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def replay(
        self,
        workflow: Workflow,
        dry_run: bool = False,
        explain: bool = False,
        smart: bool = False,
    ) -> int:
        completed = self.storage.load_replay_state(workflow.name) if smart else set()
        newly_completed = set(completed)

        for idx, action in enumerate(workflow.actions, start=1):
            signature = self._signature(action)
            if smart and signature in completed:
                print(f"[{idx}] SKIP (smart): {action.action_type}")
                continue

            if explain:
                print(self._explain_action(idx, action))

            if dry_run:
                print(f"[{idx}] DRY-RUN: {action.action_type}")
                continue

            self._execute_action(idx, action)
            newly_completed.add(signature)
            if smart:
                self.storage.save_replay_state(workflow.name, newly_completed)

        return len(workflow.actions)

    def _explain_action(self, idx: int, action: Action) -> str:
        if action.action_type == "command":
            cmd = action.payload.get("command", "")
            cwd = action.payload.get("cwd", ".")
            return f"[{idx}] Execute command in {cwd}: {cmd}"

        path = action.payload.get("path", "")
        if action.action_type == "file_create":
            return f"[{idx}] Create file: {path}"
        if action.action_type == "file_modify":
            return f"[{idx}] Modify file: {path}"
        if action.action_type == "file_delete":
            return f"[{idx}] Delete file: {path}"
        return f"[{idx}] Unknown action: {action.action_type}"

    def _execute_action(self, idx: int, action: Action) -> None:
        if action.action_type == "command":
            cmd = str(action.payload.get("command", "")).strip()
            cwd = str(action.payload.get("cwd", "."))
            if not cmd:
                logger.warning("[%d] Empty command skipped", idx)
                return
            print(f"[{idx}] RUN: {cmd}")
            result = subprocess.run(cmd, cwd=cwd, shell=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"Command failed with code {result.returncode}: {cmd}")
            return

        if action.action_type in {"file_create", "file_modify"}:
            path = Path(str(action.payload["path"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            content_b64 = str(action.payload.get("content_b64", ""))
            raw = base64.b64decode(content_b64.encode("ascii"))
            path.write_bytes(raw)
            print(f"[{idx}] WRITE: {path}")
            return

        if action.action_type == "file_delete":
            path = Path(str(action.payload["path"]))
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                os.remove(path)
            print(f"[{idx}] DELETE: {path}")
            return

        logger.warning("[%d] Unknown action type: %s", idx, action.action_type)
