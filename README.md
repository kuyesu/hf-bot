# 🤗 hf-kit

[![PyPI version](https://img.shields.io/pypi/v/hf-kit.svg)](https://pypi.org/project/hf-kit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A simple CLI utility suite to inspect Hugging Face repositories, evaluate local disk space safety, and check model trends.

---

## 🛑 About 

1. **`diskspace` (Preventing Storage Crashes):** Stops you from downloading a model that will crash your hard drive halfway through. It checks the remote model size against your remaining local storage before you download.
2. **`vibecheck` (Evaluating Project Activity):** Checks monthly downloads, community likes, and lifecycle metrics so you can immediately see if a model is vibrant and maintained or a dormant archive.
3. **`peek` (Inspecting Model Architecture):** Avoids downloading heavy model weights just to check basic parameters. It instantly snatches and parses the remote `config.json` to show context windows, attention heads, and model classes.



### Installation

```bash
pip install hf-kit

```

For local development mode:

```bash
git clone [https://github.com/yourusername/hf-kit.git](https://github.com/yourusername/hf-kit.git)
cd hf-kit
pip install -e .

```


### Usage & Commands

#### 1. `diskspace`

```bash
hf-kit diskspace EleutherAI/gpt-j-6b

```
![Storage Assessment](https://github.com/kuyesu/hf-tool/blob/main/screenshot/diskspace.png)


#### 2. `vibecheck`

```bash
hf-kit vibecheck EleutherAI/gpt-j-6b

```

![Vibe Check](screenshots/vibecheck.png)


#### 3. `peek`

```bash
hf-kit peek gpt2

```

![Structural Architecture Peek](https://github.com/kuyesu/hf-tool/blob/main/screenshot/diskspace.png)


### Private & Gated Repositories

If a repository requires authentication, `hf-kit` securely prompts for your Hugging Face token and saves it locally:

```text
🔒 Authentication Needed
Enter your Hugging Face Access Token (input will be hidden): ············
✓ Success! Token validated and saved locally.

```


### Uninstallation

```bash
pip uninstall hf-kit

```



### License

MIT

