"""Regression tests for smart-replay checkpoints."""

import base64
import tempfile
import unittest
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from exectrace.core.models import Action, Workflow
from exectrace.core.replayer import Replayer
from exectrace.storage.json_storage import JsonStorage
from exectrace.storage.xml_storage import XmlStorage


class ReplayStateTests(unittest.TestCase):
    def make_workflow(self, root: Path) -> Workflow:
        workflow = Workflow(name="checkpoint-test")
        for name in ("first.txt", "second.txt"):
            workflow.add_action(
                "file_create",
                {
                    "path": str(root / name),
                    "content_b64": base64.b64encode(name.encode("utf-8")).decode(
                        "ascii"
                    ),
                },
            )
        return workflow

    def test_dry_run_does_not_create_completion_state(self) -> None:
        for backend in (JsonStorage, XmlStorage):
            with (
                self.subTest(backend=backend.__name__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                storage = backend(tmp)
                workflow = self.make_workflow(root)
                replayer = Replayer(storage)

                replayer.replay(workflow, dry_run=True, smart=True)

                self.assertFalse(storage.replay_state_path(workflow.name).exists())
                self.assertFalse((root / "first.txt").exists())
                replayer.replay(workflow, smart=True)
                self.assertEqual((root / "first.txt").read_text(), "first.txt")
                self.assertEqual((root / "second.txt").read_text(), "second.txt")

    def test_dry_run_preserves_existing_checkpoint(self) -> None:
        for backend in (JsonStorage, XmlStorage):
            with (
                self.subTest(backend=backend.__name__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                storage = backend(tmp)
                workflow = self.make_workflow(Path(tmp))
                replayer = Replayer(storage)
                storage.save_replay_state(
                    workflow.name, {replayer._signature(workflow.actions[0])}
                )
                before = storage.replay_state_path(workflow.name).read_bytes()

                with patch.object(
                    storage, "save_replay_state", wraps=storage.save_replay_state
                ) as save:
                    replayer.replay(workflow, dry_run=True, smart=True)
                    save.assert_not_called()

                self.assertEqual(
                    storage.replay_state_path(workflow.name).read_bytes(), before
                )

    def test_failure_keeps_only_successful_actions_checkpointed(self) -> None:
        for backend in (JsonStorage, XmlStorage):
            with (
                self.subTest(backend=backend.__name__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                storage = backend(tmp)
                workflow = self.make_workflow(root)
                replayer = Replayer(storage)
                execute = replayer._execute_action

                def fail_second(
                    idx: int,
                    action: Action,
                    execute: Callable[[int, Action], None] = execute,
                ) -> None:
                    if idx == 2:
                        raise RuntimeError("simulated action failure")
                    execute(idx, action)

                with (
                    patch.object(replayer, "_execute_action", side_effect=fail_second),
                    self.assertRaisesRegex(RuntimeError, "simulated action failure"),
                ):
                    replayer.replay(workflow, smart=True)

                self.assertTrue((root / "first.txt").is_file())
                self.assertFalse((root / "second.txt").exists())
                self.assertEqual(
                    storage.load_replay_state(workflow.name),
                    {replayer._signature(workflow.actions[0])},
                )
                with patch.object(
                    replayer, "_execute_action", wraps=execute
                ) as resumed:
                    replayer.replay(workflow, smart=True)
                    resumed.assert_called_once_with(2, workflow.actions[1])

                self.assertEqual((root / "second.txt").read_text(), "second.txt")
                self.assertEqual(len(storage.load_replay_state(workflow.name)), 2)

    def test_non_smart_replay_does_not_write_checkpoints(self) -> None:
        for backend in (JsonStorage, XmlStorage):
            with (
                self.subTest(backend=backend.__name__),
                tempfile.TemporaryDirectory() as tmp,
            ):
                storage = backend(tmp)
                workflow = self.make_workflow(Path(tmp))
                Replayer(storage).replay(workflow)
                self.assertFalse(storage.replay_state_path(workflow.name).exists())


if __name__ == "__main__":
    unittest.main()
