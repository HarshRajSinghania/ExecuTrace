<div align="center">

```
  ███████╗██╗  ██╗███████╗ ██████╗██╗   ██╗████████╗██████╗  █████╗  ██████╗███████╗
  ██╔════╝╚██╗██╔╝██╔════╝██╔════╝██║   ██║╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝
  █████╗   ╚███╔╝ █████╗  ██║     ██║   ██║   ██║   ██████╔╝███████║██║     █████╗  
  ██╔══╝   ██╔██╗ ██╔══╝  ██║     ██║   ██║   ██║   ██╔══██╗██╔══██║██║     ██╔══╝  
  ███████╗██╔╝ ██╗███████╗╚██████╗╚██████╔╝   ██║   ██║  ██║██║  ██║╚██████╗███████╗
  ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝
```

# ExecuTrace

**Record, edit, and replay developer workflows**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/exectrace-workflow.svg)](https://pypi.org/project/exectrace-workflow/#description)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-purple.svg)](#)
[![Self-Hosted Git](https://img.shields.io/badge/Self--Hosted-Gitea-green?style=flat-square\&logo=gitea\&logoColor=white)](https://git.w4nn4d13.tech/0x5t4l1n/ExecuTrace)


</div>

---

## About

ExecuTrace is a Python library and CLI tool that captures developer workflows and replays them reliably.

**What it does:**
- Records terminal commands from shell history
- Tracks file system changes (create, modify, delete)
- Saves workflows in JSON or XML format
- Replays workflows with multiple execution modes

**Why use it:**
- Automate repetitive development tasks
- Share procedures with team members
- Create reproducible environment setups
- Document complex workflows reliably
- Ensure consistent deployments

## Documentation Website

The full open source docs website (retro 70s style) lives in `website/` and can be deployed with GitHub Pages.

- Source: `website/index.html`
- Hall of Fame data: `website/data/contributors.json`
- Security Hall of Fame data: `website/data/security_hof.json`

---

## Installation

### From PyPI (Global Library)
```bash
# Install globally from PyPI
pip install exectrace-workflow

# Verify installation
exectrace --help
```

### From Source (Development)
```bash
git clone https://github.com/th30d4y/ExecuTrace.git
cd ExecuTrace
pip install -e .
```

---

## Quick Usage

```bash
# Record
exectrace record my-workflow
# ... run your commands ...
exectrace stop

# Replay
exectrace replay my-workflow --explain
```

### Smart replay and previews

Use `exectrace replay my-workflow --smart` to skip actions completed by an earlier
smart replay. Progress is saved after each successful action, so a later failure
leaves the earlier actions checkpointed for the next attempt.

Add `--dry-run` to preview the remaining actions without executing them or changing
the saved replay state:

```bash
exectrace replay my-workflow --smart --dry-run
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

## Security

- Policy: [SECURITY.md](SECURITY.md)
- Advisory process: [SECURITY_ADVISORY.md](SECURITY_ADVISORY.md)

