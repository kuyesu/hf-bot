#!/usr/bin/env python3
import argparse
import os
import sys
import shutil
import requests
from datetime import datetime
from huggingface_hub import HfApi, get_token, login
from huggingface_hub.utils import RepositoryNotFoundError, GatedRepoError, LocalTokenNotFoundError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from agent import run_agent

console = Console()

def format_size(bytes_size: int) -> str:
    """Utility to convert bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"

def get_api(token=None) -> HfApi:
    """
    Programmatic helper that checks if the primary HF server is responsive.
    If it hits a connection reset/timeout, it seamlessly initializes the HfApi 
    instance pointed to the stable mirror endpoint.
    """
    if os.environ.get("HF_ENDPOINT"):
        return HfApi(token=token)
        
    try:
        # A quick, low-overhead ping to test primary endpoint connectivity
        requests.get("https://huggingface.co", timeout=2.0)
        return HfApi(token=token)
    except requests.RequestException:
        # Seamlessly fallback behind the scenes for this specific runtime layout
        return HfApi(endpoint="https://hf-mirror.com", token=token)

def ensure_authenticated() -> str:
    """
    Checks if a Hugging Face token is available.
    If no token is found in environment or local cache, prompts the user securely
    and saves it so subsequent runs don't ask again.
    """
    token = get_token()
    if token:
        return token

    console.print(Panel(
        "[yellow]🔒 Authentication Needed[/yellow]\n\n"
        "This tool needs to check repository structural specs.\n"
        "If you are trying to access a private or gated model (like Llama or Gemma),\n"
        "an active access token is required.",
        title="Hugging Face Hub Security",
        border_style="yellow",
        expand=False
    ))

    # Prompt securely using Rich's password-style masking input
    user_token = Prompt.ask(
        "Enter your Hugging Face Access Token (input will be hidden)", 
        password=True
    ).strip()

    if not user_token:
        console.print("[bold red]Authorization Aborted:[/bold red] Token cannot be empty. Exiting.", style="red")
        sys.exit(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Verifying and storing your token...", total=None)
        try:
            # Login validates the token and writes it securely to ~/.cache/huggingface/token
            login(token=user_token, add_to_git_credential=False)
            console.print("[bold green]✓ Success![/bold green] Token validated and saved locally.\n")
            return user_token
        except Exception as e:
            console.print(f"[bold red]Authentication Failed:[/bold red] The token provided is invalid. Details: {e}", style="red")
            sys.exit(1)

# ==========================================
# COMMAND 1: DISKSPACE
# ==========================================
def handle_diskspace(args):
    repo_id = args.repo_id
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description=f"Querying 🤗 Hub for {repo_id}...", total=None)
        try:
            api = get_api()
            model_info = api.model_info(repo_id=repo_id, files_metadata=True)
        except (GatedRepoError, LocalTokenNotFoundError, RepositoryNotFoundError) as e:
            if isinstance(e, RepositoryNotFoundError):
                console.print(f"[dim]Repo not found publicly. Checking if it is a private instance...[/dim]")
            
            active_token = ensure_authenticated()
            
            try:
                api = get_api(token=active_token)
                model_info = api.model_info(repo_id=repo_id, files_metadata=True)
            except Exception as retry_error:
                console.print(f"[bold red]Access Denied:[/bold red] Still unable to access '{repo_id}'.\n"
                              f"Make sure your token has access rights or that the repo name is correct.\n"
                              f"Details: {retry_error}", style="red")
                return
        except Exception as e:
            console.print(f"[bold red]Network Error:[/bold red] {e}")
            return

    # Sum up target files sizes
    total_bytes = sum(f.size for f in model_info.siblings if f.size is not None)
    
    # Get local storage metrics
    total_space, used_space, free_space = shutil.disk_usage(".")
    
    table = Table(title=f"💾 Storage Assessment: {repo_id}", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    
    table.add_row("Total Model Files Size", format_size(total_bytes))
    table.add_row("Your Available Disk Space", format_size(free_space))
    
    if free_space > total_bytes:
        margin = free_space - total_bytes
        status_text = f"[bold green]✓ Fit Confirmed![/bold green] You will have {format_size(margin)} remaining space."
        table.add_row("Safety Margin", f"[green]+{format_size(margin)}[/green]")
    else:
        deficit = total_bytes - free_space
        status_text = f"[bold red]✗ Out of Space![/bold red] You need an additional {format_size(deficit)} to safely fetch this model."
        table.add_row("Deficit", f"[red]-{format_size(deficit)}[/red]")
        
    console.print(table)
    console.print(Panel(status_text, expand=False))

# ==========================================
# COMMAND 2: VIBECHECK
# ==========================================
def handle_vibecheck(args):
    repo_id = args.repo_id
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description=f"Auditing trends for {repo_id}...", total=None)
        try:
            api = get_api()
            model_info = api.model_info(repo_id=repo_id)
        except (GatedRepoError, LocalTokenNotFoundError, RepositoryNotFoundError):
            active_token = ensure_authenticated()
            try:
                api = get_api(token=active_token)
                model_info = api.model_info(repo_id=repo_id)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] Could not fetch data ({e})")
                return
        except Exception as e:
            console.print(f"[bold red]Network Error:[/bold red] Could not connect to Hub endpoints ({e})")
            return

    downloads = getattr(model_info, "downloads", 0)
    likes = getattr(model_info, "likes", 0)
    last_modified_str = getattr(model_info, "lastModified", None)
    
    if last_modified_str:
        try:
            clean_date = last_modified_str.split("T")[0]
            dt = datetime.strptime(clean_date, "%Y-%m-%d")
            days_ago = (datetime.now() - dt).days
            time_status = f"{clean_date} ({days_ago} days ago)"
        except Exception:
            time_status = str(last_modified_str)
            days_ago = 0
    else:
        time_status = "Unknown"
        days_ago = 999

    if downloads > 50000 and days_ago < 30:
        verdict = "[bold green]🚀 Vibrant & Trending[/bold green]"
    elif downloads > 1000 or days_ago < 90:
        verdict = "[bold blue]👍 Stable Workhorse[/bold blue]"
    else:
        verdict = "[bold yellow]⚠️ Dormant Archive[/bold yellow]"

    panel_content = (
        f"[bold]Total Downloads (Month):[/bold] {downloads:,}\n"
        f"[bold]Community Likes:[/bold] {likes:,}\n"
        f"[bold]Last Updated:[/bold] {time_status}\n\n"
        f"[bold underline]Verdict:[/bold underline]\n{verdict}"
    )
    
    console.print(Panel(panel_content, title=f"📊 Vibe Check: {repo_id}", border_style="cyan", expand=False))

# ==========================================
# COMMAND 3: PEEK
# ==========================================
def handle_peek(args):
    repo_id = args.repo_id
    base_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    config_url = f"{base_endpoint}/{repo_id}/resolve/main/config.json"
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task(description="Snatching config metadata...", total=None)
        
        try:
            response = requests.get(config_url, headers=headers, timeout=10)
        except requests.RequestException:
            # If the base endpoint times out or drops, auto-rewrite the URL destination
            if "huggingface.co" in config_url:
                config_url = config_url.replace("huggingface.co", "hf-mirror.com")
                response = requests.get(config_url, headers=headers, timeout=10)
            else:
                raise
        
        if response.status_code in [401, 403]:
            progress.stop()
            active_token = ensure_authenticated()
            headers = {"Authorization": f"Bearer {active_token}"}
            
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as retry_progress:
                retry_progress.add_task(description="Retrying secure handshake...", total=None)
                try:
                    response = requests.get(config_url, headers=headers, timeout=10)
                except requests.RequestException:
                    if "huggingface.co" in config_url:
                        config_url = config_url.replace("huggingface.co", "hf-mirror.com")
                        response = requests.get(config_url, headers=headers, timeout=10)
                    else:
                        raise

        if response.status_code == 404:
            console.print(f"[bold yellow]Notice:[/bold yellow] No architecture 'config.json' found for {repo_id}.", style="yellow")
            return
            
        try:
            response.raise_for_status()
            config_data = response.json()
        except Exception as e:
            console.print(f"[bold red]Error parsing config mapping:[/bold red] {e}")
            return

    table = Table(title=f"🔎 Structural Architecture Peek: {repo_id}", show_header=True, header_style="bold green")
    table.add_column("Parameter key", style="cyan")
    table.add_column("Config Value", justify="left")
    
    targets = [
        ("architectures", "Model Class"),
        ("model_type", "Model Type Base"),
        ("max_position_embeddings", "Context Length Window"),
        ("vocab_size", "Vocabulary Matrix Size"),
        ("hidden_size", "Hidden Size Dimension"),
        ("num_attention_heads", "Attention Heads Count"),
        ("torch_dtype", "Default Precision Datatype")
    ]
    
    found_any = False
    for key, label in targets:
        if key in config_data:
            val = config_data[key]
            if isinstance(val, list):
                val = ", ".join(map(str, val))
            table.add_row(label, str(val))
            found_any = True
            
    if not found_any:
        for k, v in list(config_data.items())[:8]:
            table.add_row(str(k), str(v))

    console.print(table)

# ==========================================
# CORE ENTRY ROUTER
# ==========================================
def main():
    # Capture everything after 'hf-bot' command invocation
    args = sys.argv[1:]
    
    # CASE 1: No arguments provided (e.g., 'hf-bot')
    if not args:
        initial_prompt = ""
        
    # CASE 2: Explicit command keyword provided (e.g., 'hf-bot start')
    elif args[0].strip().lower() == "start":
        # If they wrote 'hf-bot start "some string"', use the trailing arguments,
        # otherwise default to a clean slate initialization parameter
        initial_prompt = " ".join(args[1:]) if len(args) > 1 else ""
        
    # CASE 3: Inline prompt provided directly (e.g., hf-bot "check popularity...")
    else:
        initial_prompt = " ".join(args)

    # Boot up the interactive agent session
    run_agent(initial_prompt)
    parser = argparse.ArgumentParser(
        description="hf-bot: An extended utility suite for structural validation and hub metrics."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")
    
    ds_parser = subparsers.add_parser("diskspace", help="Evaluate local disk availability against model weights size")
    ds_parser.add_argument("repo_id", type=str, help="Hugging Face Repository identifier")
    ds_parser.set_defaults(func=handle_diskspace)
    
    vc_parser = subparsers.add_parser("vibecheck", help="Assess model momentum, downloads, and lifecycle status")
    vc_parser.add_argument("repo_id", type=str, help="Hugging Face Repository identifier")
    vc_parser.set_defaults(func=handle_vibecheck)
    
    pk_parser = subparsers.add_parser("peek", help="Download tiny header maps to analyze structural parameters")
    pk_parser.add_argument("repo_id", type=str, help="Hugging Face Repository identifier")
    pk_parser.set_defaults(func=handle_peek)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()