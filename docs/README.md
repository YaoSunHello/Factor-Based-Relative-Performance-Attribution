# Documentation Index

This folder contains the full handover documentation for the factor-based relative
performance attribution project.

## Documents

| Document | Purpose |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | How to install, run, configure, and interpret the dashboard. |
| [DATA_AND_CONFIG_SPEC.md](DATA_AND_CONFIG_SPEC.md) | Required input data format and every `config.yaml` field. |
| [METHODOLOGY.md](METHODOLOGY.md) | Model equations, staged regression, attribution linking, and risk decomposition. |
| [MODULE_REFERENCE.md](MODULE_REFERENCE.md) | File-by-file package reference for developers. |
| [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) | What each dashboard section means and how to review outputs. |
| [OPERATIONS.md](OPERATIONS.md) | Testing, generated files, dependency management, and release checklist. |

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 run.py --synthetic --output demo.html
```

Open `demo.html` in a browser. The file is self-contained and works offline.

