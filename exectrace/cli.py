from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from exectrace.core.replayer import Replayer
from exectrace.recorder.session import RecorderSession
from exectrace.storage.factory import get_storage
from exectrace.storage.json_storage import JsonStorage
from exectrace.storage.xml_storage import XmlStorage
from exectrace.utils.interactive import (
    prompt_confirmation,
    prompt_file_format,
    prompt_storage_location,
)
from exectrace.utils.logger import get_logger

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="exectrace",
        description="Record and replay developer workflows.",
    )
    sub = parser.add_subparsers(dest="command")

    # Record command
    record_parser = sub.add_parser("record", help="Start recording a workflow")
    record_parser.add_argument("name", help="Workflow name")
    record_parser.add_argument(
        "--root",
        default=".",
        help="Root directory to track for file system changes (default: current dir)",
    )
    record_parser.add_argument(
        "--format",
        choices=["json", "xml"],
        help="Storage format (json or xml). If not specified, will prompt.",
    )
    record_parser.add_argument(
        "--path",
        help="Custom storage path. If not specified, will prompt.",
    )

    # Stop command
    sub.add_parser("stop", help="Stop current recording and save workflow")
    # Replay command
    replay_parser = sub.add_parser("replay", help="Replay a workflow")
    replay_parser.add_argument("name", help="Workflow name")
    replay_parser.add_argument("--dry-run", action="store_true", help="Simulate steps without executing")
    replay_parser.add_argument("--explain", action="store_true", help="Describe each step before running")
    replay_parser.add_argument("--smart", action="store_true", help="Skip actions previously completed")

    # List command
    list_parser = sub.add_parser("list", help="List saved workflows")
    list_parser.add_argument("--json", action="store_true", help="Print list as JSON")

    # Edit command
    edit_parser = sub.add_parser("edit", help="Edit a saved workflow")
    edit_parser.add_argument("name", help="Workflow name to edit")
    # Delete command
    delete_parser = sub.add_parser("delete", help="Delete a saved workflow")
    delete_parser.add_argument("name", help="Workflow name to delete")
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Delete without confirmation",
    )

    return parser


def cmd_record(args: argparse.Namespace) -> int:
    """Handle the 'record' command with interactive prompts."""
    # Prompt for storage path if not provided
    storage_path = args.path if args.path else prompt_storage_location()
    
    # Prompt for file format if not provided
    file_format = args.format if args.format else prompt_file_format()
    
    # Create RecorderSession with chosen format and path
    recorder = RecorderSession(storage_format=file_format, storage_path=storage_path)
    state = recorder.start(name=args.name, root_dir=args.root)
    
    print(f"Recording started for workflow '{args.name}'.")
    print(f"Root directory: {state['root_dir']}")
    print(f"Storage format: {file_format.upper()}")
    print(f"Storage path: {storage_path}")
    print("Run your commands, then execute: exectrace stop")
    return 0


def cmd_stop(_: argparse.Namespace) -> int:
    """Handle the 'stop' command."""
    recorder = RecorderSession()
    workflow = recorder.stop()
    print(f"Recording stopped. Saved workflow '{workflow.name}' with {len(workflow.actions)} actions.")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Handle the 'replay' command."""
    # Try both storage backends to find the workflow
    storage = None
    workflow = None
    
    # Try JSON first
    try:
        storage = JsonStorage()
        workflow = storage.load_workflow(args.name)
    except FileNotFoundError:
        # Try XML
        try:
            storage = XmlStorage()
            workflow = storage.load_workflow(args.name)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Workflow '{args.name}' not found in JSON or XML format") from exc
    
    replayer = Replayer(storage=storage)
    total = replayer.replay(workflow, dry_run=args.dry_run, explain=args.explain, smart=args.smart)
    print(f"Replay complete. Processed {total} action(s).")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Handle the 'list' command."""
    # Collect workflows from both storage formats
    json_storage = JsonStorage()
    xml_storage = XmlStorage()
    
    json_workflows = json_storage.list_workflows()
    xml_workflows = xml_storage.list_workflows()
    
    # Combine and deduplicate
    all_workflows = sorted(set(json_workflows + xml_workflows))
    
    if args.json:
        print(json.dumps(all_workflows, indent=2))
    else:
        if not all_workflows:
            print("No workflows found.")
            return 0
        print("Available workflows:")
        for workflow_name in all_workflows:
            # Check which formats are available
            is_json = workflow_name in json_workflows
            is_xml = workflow_name in xml_workflows
            formats = []
            if is_json:
                formats.append("json")
            if is_xml:
                formats.append("xml")
            format_str = f" [{', '.join(formats)}]" if formats else ""
            print(f"  - {workflow_name}{format_str}")
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    """Handle the 'edit' command."""
    # Try to find the workflow in either format
    storage = None
    workflow = None
    
    try:
        storage = JsonStorage()
        workflow = storage.load_workflow(args.name)
        current_format = "json"
    except FileNotFoundError:
        try:
            storage = XmlStorage()
            workflow = storage.load_workflow(args.name)
            current_format = "xml"
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Workflow '{args.name}' not found") from exc
    
    # Display workflow info
    print(f"\nWorkflow: {workflow.name}")
    print(f"Format: {current_format}")
    print(f"Created: {workflow.created_at}")
    print(f"Actions: {len(workflow.actions)}")
    print("\nActions:")
    for idx, action in enumerate(workflow.actions, 1):
        print(f"  {idx}. {action.action_type} @ {action.timestamp}")
    
    # Interactive editing menu
    while True:
        print("\nEdit options:")
        print("  1) Add action")
        print("  2) Remove action")
        print("  3) View action details")
        print("  4) Save and exit")
        print("  5) Exit without saving")
        
        choice = input("Choose option (1-5): ").strip()
        
        if choice == "1":
            action_type = input("Enter action type (command, file_create, file_modify, file_delete): ").strip()
            if action_type not in ("command", "file_create", "file_modify", "file_delete"):
                print("Invalid action type.")
                continue
            
            payload_input = input("Enter payload as JSON: ").strip()
            try:
                payload = json.loads(payload_input)
            except json.JSONDecodeError:
                print("Invalid JSON format.")
                continue
            
            workflow.add_action(action_type, payload)
            print(f"Action added. Total actions: {len(workflow.actions)}")
        
        elif choice == "2":
            try:
                idx = int(input("Enter action number to remove: ").strip())
                if 1 <= idx <= len(workflow.actions):
                    removed = workflow.actions.pop(idx - 1)
                    print(f"Removed: {removed.action_type}")
                else:
                    print("Invalid action number.")
            except ValueError:
                print("Please enter a valid number.")
        
        elif choice == "3":
            try:
                idx = int(input("Enter action number to view: ").strip())
                if 1 <= idx <= len(workflow.actions):
                    action = workflow.actions[idx - 1]
                    print(f"\nAction {idx}:")
                    print(f"  Type: {action.action_type}")
                    print(f"  Timestamp: {action.timestamp}")
                    print(f"  Payload: {json.dumps(action.payload, indent=2)}")
                else:
                    print("Invalid action number.")
            except ValueError:
                print("Please enter a valid number.")
        
        elif choice == "4":
            storage.save_workflow(workflow)
            print(f"Workflow saved as '{workflow.name}' in {current_format} format.")
            return 0
        
        elif choice == "5":
            print("Exiting without saving.")
            return 0
        
        else:
            print("Invalid choice.")


def cmd_delete(args: argparse.Namespace) -> int:
    """Handle the 'delete' command."""
    # Try to find the workflow in either format
    found_formats = []
    paths_to_delete = []
    
    try:
        storage = JsonStorage()
        path = storage.workflow_path(args.name)
        if path.exists():
            found_formats.append("json")
            paths_to_delete.append(path)
    except PermissionError:
        # Do not swallow permission errors on the storage directory
        raise
    except Exception:
        # Other errors (e.g. transient I/O) are ignored so we can try the other format
        pass
    
    try:
        storage = XmlStorage()
        path = storage.workflow_path(args.name)
        if path.exists():
            found_formats.append("xml")
            paths_to_delete.append(path)
    except PermissionError:
        raise
    except Exception:
        pass
    
    if not found_formats:
        print(f"Workflow '{args.name}' not found in any format.")
        return 1
    
    # Confirm deletion unless --force is used
    if not args.force:
        format_str = ", ".join(found_formats)
        if not prompt_confirmation(f"Delete workflow '{args.name}' ({format_str})?"):
            print("Deletion cancelled.")
            return 0
    
    # Delete the files
    for path in paths_to_delete:
        try:
            path.unlink()
            print(f"Deleted: {path}")
        except Exception as exc:
            print(f"Error deleting {path}: {exc}", file=sys.stderr)
            return 2
    
    print(f"Workflow '{args.name}' deleted successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "record":
            return cmd_record(args)
        if args.command == "stop":
            return cmd_stop(args)
        if args.command == "replay":
            return cmd_replay(args)
        if args.command == "list":
            return cmd_list(args)
        if args.command == "edit":
            return cmd_edit(args)
        if args.command == "delete":
            return cmd_delete(args)

        parser.print_help()
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"Execution error: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:  # Basic fallback handling for starter project robustness.
        print(f"Unexpected error: {exc}", file=sys.stderr)
        logger.exception("Unexpected error")
        return 99


if __name__ == "__main__":
    raise SystemExit(main())
