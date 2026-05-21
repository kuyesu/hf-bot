import os
import sys
import json
import openai
import subprocess
import shutil
import uuid
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.prompt import Prompt
from huggingface_hub import HfApi

console = Console()
hf_api = HfApi()

# Config layout directory files (~/.config/hf-bot/)
CONFIG_DIR = Path.home() / ".config" / "hf-bot"
CONFIG_FILE = CONFIG_DIR / "keys.json"
UUID_FILE = CONFIG_DIR / "device_id.json"

# CHANGE THIS to your deployed proxy domain endpoint address (e.g., https://hf-bot-proxy.render.com/v1)
PROXY_SERVER_URL = "https://hf-bot-proxy.vercel.app/v1" 

# ==========================================
# 🔐 CONFIGURATION MANAGEMENT LAYER
# ==========================================
def get_device_uuid() -> str:
    """Generates an anonymous tracking string to identify users consistently across restarts."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if UUID_FILE.exists():
        with open(UUID_FILE, "r") as f:
            return json.load(f).get("uuid", str(uuid.uuid4()))
    uid = str(uuid.uuid4())
    with open(UUID_FILE, "w") as f:
        json.dump({"uuid": uid}, f)
    return uid

def load_resolved_provider_context() -> tuple[openai.OpenAI, str, bool]:
    """Dynamically switches providers based on local configuration states."""
    env_xai_key = os.getenv("XAI_API_KEY")
    local_url = os.getenv("LOCAL_MODEL_URL")
    
    # 1. Option B Overrides: Explicit system environment variable configurations
    if env_xai_key:
        return openai.OpenAI(base_url="https://api.x.ai/v1", api_key=env_xai_key), os.getenv("XAI_MODEL_NAME", "grok-4.3"), False
    if local_url:
        return openai.OpenAI(base_url=local_url, api_key="dummy-key"), os.getenv("LOCAL_MODEL_NAME", "llama3"), False

    # 2. Option B Overrides: Stored keys inside local configuration profile files
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_key = json.load(f).get("XAI_API_KEY")
                if saved_key:
                    return openai.OpenAI(base_url="https://api.x.ai/v1", api_key=saved_key), os.getenv("XAI_MODEL_NAME", "grok-4.3"), False
        except Exception:
            pass

    # 3. Option A Base Case Fallback: Routing securely through your remote project proxy
    device_id = get_device_uuid()
    proxy_client = openai.OpenAI(
        base_url=PROXY_SERVER_URL,
        api_key="proxy-unneeded",
        default_headers={"X-Client-UUID": device_id}
    )
    return proxy_client, "grok-4.3", True


def run_interactive_config_setup():
    """Interactive command pipeline for setting local API tokens (Option B)."""
    console.print("\n🔐 [bold purple]hf-bot Workspace Token Configuration (Option B)[/]")
    console.print("Set your own key to remove shared limits. Saved at `~/.config/hf-bot/keys.json`.\n")
    user_key = Prompt.ask("[bold white]Enter your personal xAI (Grok) API Key[/]", password=True).strip()
    
    if not user_key:
        console.print("[red]Operation aborted.[/]")
        return
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"XAI_API_KEY": user_key}, f, indent=4)
        console.print("\n[bold green]✓ Success![/] Custom account key registered cleanly. Relaunching your tool now...\n")
    except Exception as e:
        console.print(f"[bold red]Failed to save token properties:[/] {e}")

# ==========================================
# 🛠️ AGENT TOOLSET DEFINITIONS
# ==========================================
def get_hf_repository_metadata(repo_id: str) -> str:
    try:
        model_info = hf_api.model_info(repo_id=repo_id)
        return json.dumps({
            "repo_id": repo_id, "likes": getattr(model_info, "likes", 0),
            "downloads": getattr(model_info, "downloads", 0),
            "pipeline_tag": getattr(model_info, "pipeline_tag", "Unknown")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def check_system_resources() -> str:
    total, used, free = shutil.disk_usage(".")
    return json.dumps({"available_disk_space_gb": round(free / (1024**3), 2), "os_platform": sys.platform})

def execute_system_command(command: str) -> str:
    console.print(f"\n[bold red]⚠️  CRITICAL SECURITY GATE:[/] The AI agent wants to execute this shell command:")
    console.print(Panel(f"[bold yellow]{command}[/]", border_style="red"))
    confirm = console.input("[bold white]Do you approve running this command? (y/N): [/]").strip().lower()
    if confirm not in ['y', 'yes']:
        return json.dumps({"status": "rejected", "error": "Blocked for safety."})
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=60)
        return json.dumps({"status": "success", "stdout": result.stdout, "stderr": result.stderr})
    except Exception as e:
        return json.dumps({"status": "failed", "error": str(e)})

OPENAI_FORMAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_hf_repository_metadata",
            "description": "Fetch real-time popularity trends, download counters, and likes from any Hugging Face model repository path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string", "description": "The Hugging Face repository identifier (e.g., 'mistralai/Mistral-7B-v0.1')"}
                },
                "required": ["repo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_system_resources",
            "description": "Check the local system's environment properties such as remaining free disk space (GB) and current directory.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_system_command",
            "description": "Execute an approved command inside the local terminal bash shell environment. Use this to safely write/write files, run scripts, or handle diagnostics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact terminal shell command sequence string to execute."}
                },
                "required": ["command"]
            }
        }
    }
]

# ==========================================
# 🧠 MULTI-PROVIDER AGENT ENGINE
# ==========================================
def run_agent(initial_message: str):
    if initial_message.strip().lower() == "config setup":
        run_interactive_config_setup()
        return
    run_interactive_loop(initial_message)

# ==========================================
# 🔄 CORE EXECUTION AND STREAM INTERCEPTOR LOOP
# ==========================================
def run_interactive_loop(first_input: str):
    conversation_history = []
    current_input = first_input

    while True:
        # Load active dynamic connection configurations on every chat turn loop
        client, model_name, is_using_proxy = load_resolved_provider_context()

        if not current_input or not current_input.strip():
            try:
                current_input = console.input("\n[bold green]hf-bot[/] ❯ ")
            except (KeyboardInterrupt, EOFError):
                break

        if current_input.strip().lower() in ["exit", "quit"]:
            break
        if not current_input.strip():
            continue

        conversation_history.append({"role": "user", "content": current_input})
        current_input = None  
        print()

        tool_calls_buffer = {}
        text_buffer = ""
        is_tool_call = False

        with Live(Panel(Markdown("Thinking..."), border_style="cyan", padding=(1, 2)), auto_refresh=False) as live:
            try:
                first_stream = client.chat.completions.create(
                    model=model_name,
                    messages=conversation_history,
                    tools=OPENAI_FORMAT_TOOLS,
                    stream=True
                )

                for chunk in first_stream:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        is_tool_call = True
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {"id": tc.id, "name": "", "arguments": ""}
                            if tc.id: tool_calls_buffer[idx]["id"] = tc.id
                            if tc.function and tc.function.name: tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments: tool_calls_buffer[idx]["arguments"] += tc.function.arguments
                        live.update(Panel(Markdown("⚙️ *Agent analyzing platform capabilities...*"), border_style="yellow"))
                        live.refresh()

                    elif hasattr(delta, "content") and delta.content:
                        text_buffer += delta.content
                        live.update(Panel(Markdown(text_buffer), border_style="cyan"))
                        live.refresh()

            except Exception as e:
                live.stop()
                # 🚨 SEAMLESS RATE LIMIT SWITCHING CORNER
                if "429" in str(e) and is_using_proxy:
                    console.print(Panel(
                        "🛑 [bold red]Shared Sandbox Limit Reached (50/50 Chats Used Today).[/]\n\n"
                        "To continue running requests seamlessly, let's step up to your own private access config (Option B).",
                        border_style="red", title="Quota Exceeded"
                    ))
                    run_interactive_config_setup()
                    # Wipe bad request out of current stack loop histories
                    conversation_history.pop()
                    continue
                else:
                    console.print(f"[bold red]Execution Stream Error:[/] {e}")
                    continue

            if is_tool_call:
                assistant_tool_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": v["id"], "type": "function",
                            "function": {"name": v["name"], "arguments": v["arguments"]}
                        } for v in tool_calls_buffer.values()
                    ]
                }
                conversation_history.append(assistant_tool_msg)
                first_call = list(tool_calls_buffer.values())[0]
                tool_name = first_call["name"]
                args = json.loads(first_call["arguments"]) if first_call["arguments"] else {}
                
                # Close the live context window cleanly if human confirmation input is coming up
                live.stop()
                if tool_name == "get_hf_repository_metadata":
                    tool_output = get_hf_repository_metadata(args.get("repo_id"))
                elif tool_name == "check_system_resources":
                    tool_output = check_system_resources()
                elif tool_name == "execute_system_command":
                    tool_output = execute_system_command(args.get("command"))
                else:
                    tool_output = json.dumps({"error": f"Unknown tool: {tool_name}"})

                # Restart visual layout frame after human confirmation loop finishes
                live.start()

                conversation_history.append({"role": "tool", "tool_call_id": first_call["id"], "name": tool_name, "content": tool_output})

                try:
                    final_stream = client.chat.completions.create(model=model_name, messages=conversation_history, stream=True)
                    final_text_buffer = ""
                    for chunk in final_stream:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            final_text_buffer += delta.content
                            live.update(Panel(Markdown(final_text_buffer), border_style="cyan"))
                            live.refresh()
                    conversation_history.append({"role": "assistant", "content": final_text_buffer})
                except Exception as e:
                    console.print(f"[bold red]Response Generation Error:[/] {e}")
            else:
                conversation_history.append({"role": "assistant", "content": text_buffer})