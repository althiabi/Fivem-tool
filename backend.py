import sys
import json
import traceback
import threading
import queue
from main import (
    FiveMDumper,
    FiveMDecryptor,
    normalize_cfx_link,
    get_ip_from_cfx,
    get_token,
    test_server_connection,
    settings,
    Logger
)

# Queue for handling prompt responses from Electron
prompt_queue = queue.Queue()

def emit_log(msg: str, msg_type: str = "system"):
    print(json.dumps({"topic": "log", "data": {"message": msg, "type": msg_type}}), flush=True)

def emit_progress(total: int, done: int, ok: int, failed: int, bytes_count: int):
    print(json.dumps({"topic": "progress", "data": {
        "total": total,
        "done": done,
        "ok": ok,
        "failed": failed,
        "bytes": bytes_count
    }}), flush=True)

# Patch Logger so main.py uses stdout json instead of rich console
class HeadlessLogger:
    @staticmethod
    def info(msg: str): emit_log(msg, "system")
    @staticmethod
    def warning(msg: str): emit_log(msg, "warn")
    @staticmethod
    def error(msg: str): emit_log(msg, "error")
    @staticmethod
    def success(msg: str): emit_log(msg, "system")
    @staticmethod
    def dump(msg: str): emit_log(msg, "dump")
    @staticmethod
    def display(msg: str): emit_log(msg, "system")

import main
main.Logger = HeadlessLogger
main.console.print = lambda *args, **kwargs: None

# We also need to patch ProgressTracker so it emits progress JSON
class HeadlessProgressTracker(main.ProgressTracker):
    def __init__(self):
        super().__init__()
        self.total = 0
        self.done = 0
        self.ok = 0
        self.failed = 0
        self.bytes = 0
    
    def start_main_progress(self, total_resources: int):
        self.total = total_resources
        emit_progress(self.total, self.done, self.ok, self.failed, self.bytes)
        return 1

    def update_main_progress(self, completed: int, description: str = None):
        self.done += completed
        self.ok += completed
        emit_progress(self.total, self.done, self.ok, self.failed, self.bytes)

main.ProgressTracker = HeadlessProgressTracker

def run_dump(payload):
    method = payload.get("method")
    target = payload.get("target")
    threadsCount = payload.get("threads", 50)
    autoCleanup = payload.get("autoCleanup", False)

    settings.set("max_workers", threadsCount)
    settings.set("auto_cleanup", autoCleanup)
    
    ip = target
    
    # Mock Prompt.ask and Confirm.ask to interact with GUI Modal
    original_display = main.ResourceManager.display_resources_by_category
    captured_categories = {}

    @staticmethod
    def intercepted_display(resources):
        nonlocal captured_categories
        try:
            categorized = original_display(resources)
            # categorized is a dict of { "Scripts": [(0, res_dict), ...], ... }
            new_captured = {}
            for cat_name, items in categorized.items():
                cat_list = []
                for idx, res in items:
                    f_count = len(res.get("files", {})) + len(res.get("streamFiles", {}))
                    # Estimate based on file count (roughly 500KB per file as per main.py estimate)
                    size_estimate = f_count * 500 * 1024
                    cat_list.append({
                        "idx": idx,
                        "name": res.get("name", "Unknown"),
                        "file_count": f_count,
                        "size": size_estimate
                    })
                new_captured[cat_name] = cat_list
            captured_categories = new_captured
            return categorized
        except Exception as e:
            emit_log(f"Backend Categorization Error: {str(e)}", "error")
            # Return empty categorization so it doesn't crash main.py completely
            return {}

    main.ResourceManager.display_resources_by_category = intercepted_display

    class MockPrompt:
        @staticmethod
        def ask(*args, **kwargs):
            # Emit prompt request with resources payload
            print(json.dumps({"topic": "show-prompt", "data": {"categories": captured_categories}}), flush=True)
            # Block until we receive the response from the queue
            return prompt_queue.get()

    class MockConfirm:
        @staticmethod
        def ask(*args, **kwargs):
            return True

    # THE CRITICAL FIX: Since main.py uses 'from rich.prompt import Prompt', 
    # we must patch it in its global namespace directly.
    main.__dict__['Prompt'] = MockPrompt
    main.__dict__['Confirm'] = MockConfirm

    if method == "cfx":
        normalized_link = normalize_cfx_link(target)
        try:
            emit_log("Parsing Server IP from CFX link...")
            ip = get_ip_from_cfx(normalized_link)
            emit_log(f"Found IP: {ip}")
        except Exception as e:
            emit_log(f"Error parsing IP: {e}", "error")
            print(json.dumps({"topic": "dump-complete"}), flush=True)
            return

    try:
        emit_log("Fetching token...")
        raw_token = get_token()
        token = raw_token.split('\n')[0].strip() if raw_token else ""
        if not token:
            emit_log("Error 67: Make sure FiveM is running and connected.", "error")
            print(json.dumps({"topic": "dump-complete"}), flush=True)
            return
        
        emit_log(f"Token acquired. Testing connection to {ip}...")
        working_url, is_connected = test_server_connection(ip, settings.get("connection_timeout"))
        
        if not is_connected:
            emit_log("Cannot connect to server. It might be offline or Cloudflare protected.", "error")
            print(json.dumps({"topic": "dump-complete"}), flush=True)
            return
            
        emit_log(f"Starting dump on {working_url} with {threadsCount} threads...")
        dumper = FiveMDumper(working_url, token)
        dumper.run()
        
        emit_log("Dump protocol completed successfully.", "system")
        print(json.dumps({"topic": "dump-complete"}), flush=True)

    except Exception as e:
        emit_log(f"Backend Exception: {str(e)}\n{traceback.format_exc()}", "error")
        print(json.dumps({"topic": "dump-complete"}), flush=True)

def main_loop():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            action = payload.get("action")
            if action == "dump":
                # Run the dump in a separate thread so the main loop can continue listening for 'prompt-response'
                threading.Thread(target=run_dump, args=(payload,), daemon=True).start()
            elif action == "prompt-response":
                prompt_queue.put(payload.get("data", "all"))
            elif action == "ping":
                emit_log("Pong from backend", "system")
        except Exception as e:
            emit_log(f"Error processing command: {e}", "error")

if __name__ == "__main__":
    main_loop()
