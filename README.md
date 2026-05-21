# 🤗 hf-bot

[![PyPI version](https://img.shields.io/pypi/v/hf-bot.svg)](https://pypi.org/project/hf-bot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple CLI utility suite to inspect Hugging Face repositories, evaluate local disk space safety, and check model trends.

---

## 🛑 About 

1. **`diskspace` (Preventing Storage Crashes):** Stops you from downloading a model that will crash your hard drive halfway through. It checks the remote model size against your remaining local storage before you download.
2. **`vibecheck` (Evaluating Project Activity):** Checks monthly downloads, community likes, and lifecycle metrics so you can immediately see if a model is vibrant and maintained or a dormant archive.
3. **`peek` (Inspecting Model Architecture):** Avoids downloading heavy model weights just to check basic parameters. It instantly snatches and parses the remote `config.json` to show context windows, attention heads, and model classes.



### Installation

```bash
pip install hf-bot

```

For local development mode and contributions:

```bash
git clone [https://github.com/kuyesu/hf-tool.git](https://github.com/kuyesu/hf-tool.git)
cd hf-bot
pip install -e .

```


### Usage & Commands

#### 1. `diskspace`
Pass a Huggingface repository path (<repo_id>) to check its total weight footprint against your available local storage space:

```bash
hf-bot diskspace EleutherAI/gpt-j-6b

```
![Storage Assessment](https://github.com/kuyesu/hf-tool/blob/main/screenshot/diskspace.png)


#### 2. `vibecheck`

Pass a Huggingface repository ID (repo_id) to evaluate monthly usage trends, community traction, and lifecycle milestones:

```bash
hf-bot vibecheck EleutherAI/gpt-j-6b

```

![Vibe Check](https://github.com/kuyesu/hf-tool/blob/main/screenshot/vibecheck.png)


#### 3. `peek`
Pass a Huggingface model identifier (<model_id>) to fetch and parse its metadata parameters instantly:

```bash
hf-bot peek gpt2

```

![Structural Architecture Peek](https://github.com/kuyesu/hf-tool/blob/main/screenshot/peek.png)


### Private & Gated Repositories

If a repository requires authentication, `hf-bot` securely prompts for your Hugging Face token and saves it locally:

```text
🔒 Authentication Needed
Enter your Hugging Face Access Token (input will be hidden): ············
✓ Success! Token validated and saved locally.

```


### Uninstallation

```bash
pip uninstall hf-bot

```



### License

MIT

