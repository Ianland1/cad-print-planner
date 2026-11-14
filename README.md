# CAD & 3D Print Planner

A Drafter app for organizing CAD projects, tracking print status and estimated
hours, and checking whether parts fit a printer's build volume.

[Open the website](https://ianland1.github.io/cad-print-planner/).
Projects are session data; keep important information elsewhere.

## Run locally

Use Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
drafter main.py --port 8766 --no-open-browser
```

## Test

```sh
python -m pip install coverage
python -m coverage run --source=main -m unittest discover -v
python -m coverage report -m
```

## Deploy

Pushes to `main` run the tests and publish the site to GitHub Pages. Deployment
can also be started manually from **Actions → Deploy main branch as website**.
Failing tests stop deployment. The deployed site's `dashboard/` contains test
output, coverage, and the course diagnostics reports.
