# Operations

## Local Development

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run tests:

```bash
python3 -m pytest -q
```

Run the acceptance demo:

```bash
python3 run.py --synthetic --output demo.html
```

## Generated Files

The following files are ignored by git:

- `demo.html`
- `dashboard.html`
- Python bytecode/cache directories;
- `.pytest_cache/`;
- `.synthetic_returns.csv`.

If you want to preserve a dashboard output, rename it to a dated file outside the repo
or store it in a controlled reporting folder.

## Dependency Management

Dependencies are pinned in `requirements.txt`. If versions are updated:

1. Install the new versions.
2. Run `python3 -m pytest -q`.
3. Run `python3 run.py --synthetic --output demo.html`.
4. Open the dashboard and check charts render offline.
5. Commit the updated `requirements.txt`.

## Release Checklist

Before pushing a code change:

```bash
git status --short --branch
python3 -m pytest -q
python3 run.py --synthetic --output demo.html
git diff --stat
```

Confirm generated files are not staged:

```bash
git status --ignored --short
```

Commit:

```bash
git add <source files>
git commit -m "<message>"
git push origin main
```

## Troubleshooting

### Plotly Missing

If dashboard rendering fails with `No module named 'plotly'`:

```bash
python3 -m pip install -r requirements.txt
```

### Excel Input Fails

Excel input needs `openpyxl`. Install dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

### Model Has Too Many Flags

Common causes:

- too many factors for the available history;
- overlapping factor definitions;
- factor and parent index mismatch;
- stale or missing input data;
- benchmark not aligned with the fund universe.

Start by reviewing:

1. data-quality report;
2. factor construction audit;
3. correlation flags;
4. VIF flags;
5. residual review table.

## Current Implementation Boundaries

The current version does not include:

- holdings-based attribution;
- security-level Brinson attribution;
- database persistence;
- PDF export;
- multi-fund batch processing;
- formal web application server.

The output is one static HTML file per run.

