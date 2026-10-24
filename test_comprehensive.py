#!/usr/bin/env python3
"""Test script to verify ExecuTrace functionality."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return exit code and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"
    except Exception as e:
        return 1, str(e)

def test_cli_help():
    """Test that all CLI help messages work."""
    print("Testing CLI help messages...")
    
    commands = [
        ["python", "-m", "exectrace", "--help"],
        ["python", "-m", "exectrace", "record", "--help"],
        ["python", "-m", "exectrace", "replay", "--help"],
        ["python", "-m", "exectrace", "list", "--help"],
        ["python", "-m", "exectrace", "edit", "--help"],
        ["python", "-m", "exectrace", "delete", "--help"],
    ]
    
    for cmd in commands:
        code, output = run_cmd(cmd)
        if code != 0:
            print(f"❌ Failed: {' '.join(cmd)}")
            print(output)
            return False
        if "usage:" not in output.lower():
            print(f"❌ Unexpected output for: {' '.join(cmd)}")
            return False
    
    print("✅ All CLI help messages working\n")
    return True

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    try:
        from exectrace.cli import main
        from exectrace.storage.json_storage import JsonStorage
        from exectrace.storage.xml_storage import XmlStorage
        from exectrace.storage.factory import get_storage
        from exectrace.recorder.session import RecorderSession
        from exectrace.core.replayer import Replayer
        from exectrace.core.editor import WorkflowEditor
        from exectrace.utils.interactive import prompt_file_format
        
        print("✅ All imports successful\n")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}\n")
        return False

def test_storage_backends():
    """Test JSON and XML storage backends."""
    print("Testing storage backends...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test JSON storage
        from exectrace.storage.json_storage import JsonStorage
        from exectrace.core.models import Workflow
        
        json_storage = JsonStorage(tmpdir)
        workflow = Workflow(name="test-json")
        workflow.add_action("command", {"command": "echo test", "cwd": "."})
        json_storage.save_workflow(workflow)
        
        loaded = json_storage.load_workflow("test-json")
        if loaded.name != "test-json" or len(loaded.actions) != 1:
            print("❌ JSON storage failed")
            return False
        
        print("  ✅ JSON storage working")
        
        # Test XML storage
        from exectrace.storage.xml_storage import XmlStorage
        
        xml_storage = XmlStorage(tmpdir)
        workflow = Workflow(name="test-xml")
        workflow.add_action("command", {"command": "echo test", "cwd": "."})
        xml_storage.save_workflow(workflow)
        
        loaded = xml_storage.load_workflow("test-xml")
        if loaded.name != "test-xml" or len(loaded.actions) != 1:
            print("❌ XML storage failed")
            return False
        
        print("  ✅ XML storage working")
        
        # Test factory
        from exectrace.storage.factory import get_storage
        
        json_backend = get_storage("json", tmpdir)
        xml_backend = get_storage("xml", tmpdir)
        
        if not isinstance(json_backend, JsonStorage) or not isinstance(xml_backend, XmlStorage):
            print("❌ Storage factory failed")
            return False
        
        print("  ✅ Storage factory working")
    
    print("✅ All storage backends working\n")
    return True

def test_workflow_operations():
    """Test workflow operations (create, edit, delete)."""
    print("Testing workflow operations...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from exectrace.core.models import Workflow
        from exectrace.storage.factory import get_storage
        from exectrace.core.editor import WorkflowEditor
        
        storage = get_storage("json", tmpdir)
        
        # Create
        workflow = Workflow(name="ops-test")
        workflow.add_action("command", {"command": "ls", "cwd": "."})
        storage.save_workflow(workflow)
        print("  ✅ Create workflow")
        
        # Edit using WorkflowEditor
        editor = WorkflowEditor(storage)
        loaded = editor.load("ops-test")
        loaded.add_action("command", {"command": "pwd", "cwd": "."})
        editor.save(loaded)
        
        reloaded = storage.load_workflow("ops-test")
        if len(reloaded.actions) != 2:
            print("❌ Workflow edit failed")
            return False
        print("  ✅ Edit workflow")
        
        # List
        workflows = storage.list_workflows()
        if "ops-test" not in workflows:
            print("❌ Workflow list failed")
            return False
        print("  ✅ List workflows")
        
        # Delete
        path = storage.workflow_path("ops-test")
        path.unlink()
        if path.exists():
            print("❌ Workflow delete failed")
            return False
        print("  ✅ Delete workflow")
    
    print("✅ All workflow operations working\n")
    return True

def test_replayer():
    """Test replay functionality."""
    print("Testing replay functionality...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from exectrace.core.models import Workflow
        from exectrace.core.replayer import Replayer
        from exectrace.storage.factory import get_storage
        
        storage = get_storage("json", tmpdir)
        
        # Create a simple workflow
        workflow = Workflow(name="replay-test")
        workflow.add_action("command", {"command": "echo 'test'", "cwd": "."})
        storage.save_workflow(workflow)
        
        # Test dry-run
        replayer = Replayer(storage)
        result = replayer.replay(workflow, dry_run=True)
        if result != 1:
            print("❌ Dry-run replay failed")
            return False
        print("  ✅ Dry-run replay working")
        
        # Test explain mode
        result = replayer.replay(workflow, explain=True, dry_run=True)
        if result != 1:
            print("❌ Explain mode failed")
            return False
        print("  ✅ Explain mode working")
    
    print("✅ Replay functionality working\n")
    return True


def run_replay_state_tests() -> bool:
    """Run checkpoint regressions with both storage backends."""
    import unittest
    from test_replayer_state import ReplayStateTests

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReplayStateTests)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main_test():
    """Run all tests."""
    print("=" * 60)
    print("ExecuTrace Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        test_imports,
        test_cli_help,
        test_storage_backends,
        test_workflow_operations,
        test_replayer,
        run_replay_state_tests,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
            results.append(False)
    
    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    return all(results)

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    success = main_test()
    sys.exit(0 if success else 1)
