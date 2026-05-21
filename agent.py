import os
import sys
import json
import openai
import subprocess
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from huggingface_hub import HfApi

console = Console()
hf_api = HfApi()

# ==========================================
# 🛠️ AGENT TOOLSET DEFINITIONS
# ==========================================

def get_hf_repository_metadata(repo_id: str) -> str:
    """Fetches real-time metrics directly from Hugging Face."""
    try:
        model_info = hf_api.model_info(repo_id=repo_id)
        data = {
            "repo_id": repo_id,
            "likes": getattr(model_info, "likes", 0),
            "downloads": getattr(model_info, "downloads", 0),
            "pipeline_tag": getattr(model_info, "pipeline_tag", "Unknown"),
            "last_modified": str(getattr(model_info, "last_modified", "Unknown"))
        }
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to gather data from Hugging Face: {str(e)}"})

def check_system_resources() -> str:
    """Checks the developer's local machine environment: disk space, CPU architecture, and GPU presence."""
    try:
        total, used, free = shutil.disk_usage(".")
        gb = 1024 ** 3
        resources = {
            "available_disk_space_gb": round(free / gb, 2),
            "current_working_directory": os.getcwd(),
            "os_platform": sys.platform
        }
        return json.dumps(resources)
    except Exception as e:
        return json.dumps({"error": f"Failed to check local resources: {str(e)}"})

def execute_system_command(command: str) -> str:
    """Safely executes an approved terminal shell command within the project workspace."""
    # 🛑 HUMAN-IN-THE-LOOP SAFETY GATE
    console.print(f"\n[bold red]⚠️  CRITICAL SECURITY GATE:[/] The AI agent wants to execute this shell command:")
    console.print(Panel(f"[bold yellow]{command}[/]", border_style="red", title="Proposed Command"))
    
    confirm = console.input("[bold white]Do you approve running this command? (y/N): [/]").strip().lower()
    
    if confirm not in ['y', 'yes']:
        return json.dumps({"status": "rejected", "error": "The user blocked execution of this command for safety."})
    
    # Run the approved command safely
    try:
        # Limit execution time to 60 seconds so it doesn't hang indefinitely
        result = subprocess.run(
            command, 
            shell=True, 
            text=True, 
            capture_output=True, 
            timeout=60
        )
        return json.dumps({
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "failed", "error": "Command execution timed out after 60 seconds."})
    except Exception as e:
        return json.dumps({"status": "failed", "error": str(e)})


# Tools schema array for OpenAI SDK compatibility
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
            "description": "Execute a safe command inside the local terminal bash shell environment. Use this to check files, manage downloads, or inspect files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The terminal shell string command to execute."}
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
    xai_key = os.getenv("XAI_API_KEY")
    local_url = os.getenv("LOCAL_MODEL_URL")

    if xai_key:
        run_interactive_loop("grok", "https://api.x.ai/v1", xai_key, os.getenv("XAI_MODEL_NAME", "grok-4.3"), initial_message)
    elif local_url:
        run_interactive_loop("local", local_url, "dummy-key", os.getenv("LOCAL_MODEL_NAME", "llama3"), initial_message)
    else:
        console.print("[bold red]Error:[/] No active LLM provider found. Set XAI_API_KEY or LOCAL_MODEL_URL.", style="red")

# ==========================================
# 🔄 CORE EXECUTION AND STREAM INTERCEPTOR LOOP
# ==========================================
def run_interactive_loop(provider_name: str, base_url: str, api_key: str, model_name: str, first_input: str):
    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    conversation_history = []
    current_input = first_input
    
    console.print(f"[bold dim cyan]Session started via {provider_name} ({model_name}). Type 'exit' to close.[/]")

    while True:
        if not current_input:
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

        # Turn 1: Stream evaluate user request
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
                            if tc.id:
                                tool_calls_buffer[idx]["id"] = tc.id
                            if tc.function and tc.function.name:
                                tool_calls_buffer[idx]["name"] += tc.function.name
                            if tc.function and tc.function.arguments:
                                tool_calls_buffer[idx]["arguments"] += tc.function.arguments
                        
                        live.update(Panel(Markdown("⚙️ *Agent analyzing platform capabilities and resource dependencies...*"), border_style="yellow", padding=(1, 2)))
                        live.refresh()

                    elif hasattr(delta, "content") and delta.content:
                        text_buffer += delta.content
                        live.update(Panel(Markdown(text_buffer), border_style="cyan", padding=(1, 2)))
                        live.refresh()

            except Exception as e:
                console.print(f"[bold red]Stream Turn 1 Error:[/] {e}")
                continue

            # Process active tool branch execution paths
            if is_tool_call:
                assistant_tool_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": v["id"],
                            "type": "function",
                            "function": {"name": v["name"], "arguments": v["arguments"]}
                        } for v in tool_calls_buffer.values()
                    ]
                }
                conversation_history.append(assistant_tool_msg)

                # Process tool execution payloads
                first_call = list(tool_calls_buffer.values())[0]
                tool_name = first_call["name"]
                args = json.loads(first_call["arguments"]) if first_call["arguments"] else {}
                
                # Close the live context window cleanly if human confirmation input is coming up
                live.stop()

                # Dispatch context values to correct backend handler
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
                live.update(Panel(Markdown("⏳ *Synthesizing outputs and drafting status dashboard report...*"), border_style="yellow", padding=(1, 2)))
                live.refresh()

                tool_response_msg = {
                    "role": "tool",
                    "tool_call_id": first_call["id"],
                    "name": tool_name,
                    "content": tool_output
                }
                conversation_history.append(tool_response_msg)

                # Turn 2: Generate final streamed output block response
                try:
                    final_stream = client.chat.completions.create(
                        model=model_name,
                        messages=conversation_history,
                        stream=True
                    )
                    
                    final_text_buffer = ""
                    for chunk in final_stream:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            final_text_buffer += delta.content
                            live.update(Panel(Markdown(final_text_buffer), border_style="cyan", padding=(1, 2)))
                            live.refresh()
                    
                    conversation_history.append({"role": "assistant", "content": final_text_buffer})
                except Exception as e:
                    console.print(f"[bold red]Stream Turn 2 Error:[/] {e}")
            else:
                conversation_history.append({"role": "assistant", "content": text_buffer})