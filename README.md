# Python Template Scaffolder

Reusable Python project scaffolding tool with local templates.

## What it creates

Default template (`fullstack-app`) scaffolds:

- `backend/` Python API (FastAPI), tests, Dockerfile, `.env.example`
- `frontend/` Next.js app with Dockerfile and API URL wiring
- root `docker-compose.yml` orchestrating frontend + backend
- root `.env.example` plus Makefile commands to copy env files
- `.github/workflows/ci.yml` for backend lint + tests

## Usage

From this folder:

```bash
python3 scaffold.py list
python3 scaffold.py create --name "My Cool App" --author "Sathish" --email "sathish@example.com"
python3 scaffold.py status --project /path/to/my-cool-app
```

Output is created as `<output>/<project-slug>` (default output is current directory).

Example with custom output:

```bash
python3 scaffold.py create \
  --name "Customer Insights API" \
  --description "API for customer insights" \
  --output /Users/works/Desktop/@sathish/ai_projects
```

You can pass additional variables to templates:

```bash
python3 scaffold.py create --name "Demo" --var service_port=8000 --var team_name="Platform"
```

## Track Generated Vs Custom Files

Every generated project now includes a manifest at `.scaffold/manifest.json` with all scaffolded files.

Check status any time:

```bash
python3 scaffold.py status --project /absolute/path/to/project
```

It reports:

- generated files unchanged from template
- generated files modified by you
- generated files deleted by you
- custom files you added later

## Template options

```bash
python3 scaffold.py list
```

- `fullstack-app` (default): backend + frontend + docker-compose
- `python-app`: python-only package template

## Add your own template

1. Create a folder under `templates/`, for example `templates/data-pipeline`.
2. Add files ending in `.tmpl`.
3. Use placeholders in file content and paths like `{{ project_name }}`, `{{ package_name }}`.
4. Run `python3 scaffold.py create --template data-pipeline --name "My Pipeline"`.

## Built-in variables

- `project_name`
- `project_slug`
- `package_name`
- `description`
- `python_version`
- `license`
- `author`
- `email`
- `author_line`
- `year`
