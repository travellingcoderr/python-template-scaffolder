#!/usr/bin/env python3
"""Scaffold reusable Python projects from local templates."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

TOKEN_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "python-project"


def to_package_name(value: str) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    if not candidate:
        return "python_project"
    if candidate[0].isdigit():
        candidate = f"pkg_{candidate}"
    return candidate


def render_text(text: str, context: dict[str, str]) -> str:
    def replacement(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise KeyError(f"Missing template variable: {key}")
        return context[key]

    return TOKEN_RE.sub(replacement, text)


def parse_vars(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid --var '{item}'. Use key=value format.")
        key, val = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --var '{item}'. Empty key is not allowed.")
        parsed[key] = val
    return parsed


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(destination: Path, template_name: str, files: dict[str, str]) -> None:
    scaffold_dir = destination / ".scaffold"
    scaffold_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = scaffold_dir / "manifest.json"
    manifest = {
        "manifest_version": 1,
        "template": template_name,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scaffold_project(
    templates_dir: Path,
    template_name: str,
    destination: Path,
    context: dict[str, str],
    overwrite: bool = False,
) -> dict[str, str]:
    template_root = templates_dir / template_name
    if not template_root.exists() or not template_root.is_dir():
        available = sorted(p.name for p in templates_dir.iterdir() if p.is_dir())
        raise FileNotFoundError(
            f"Template '{template_name}' not found. Available templates: {', '.join(available)}"
        )

    destination.mkdir(parents=True, exist_ok=True)
    generated_files: dict[str, str] = {}

    for source in template_root.rglob("*"):
        if source.name == ".DS_Store":
            continue

        relative = source.relative_to(template_root)
        rendered_relative = Path(render_text(relative.as_posix(), context))
        target = destination / rendered_relative

        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        if target.suffix == ".tmpl":
            target = target.with_suffix("")

        if target.exists() and not overwrite:
            raise FileExistsError(f"File exists: {target}. Use --overwrite to replace.")

        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        rendered = render_text(text, context)
        target.write_text(rendered, encoding="utf-8")
        rel = target.relative_to(destination).as_posix()
        generated_files[rel] = file_sha256(target)

    return generated_files


def run_status(project_path: Path) -> None:
    manifest_path = project_path / ".scaffold" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files: dict[str, str] = manifest.get("files", {})

    generated: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []

    for rel, expected_hash in sorted(files.items()):
        path = project_path / rel
        if not path.exists():
            deleted.append(rel)
            continue
        if file_sha256(path) == expected_hash:
            generated.append(rel)
        else:
            modified.append(rel)

    ignored = {".scaffold/manifest.json"}
    generated_set = set(files.keys())
    custom: list[str] = []
    for path in sorted(p for p in project_path.rglob("*") if p.is_file()):
        rel = path.relative_to(project_path).as_posix()
        if rel in ignored or rel in generated_set:
            continue
        custom.append(rel)

    print(f"Template: {manifest.get('template', 'unknown')}")
    print(f"Generated (unchanged): {len(generated)}")
    print(f"Modified generated: {len(modified)}")
    print(f"Deleted generated: {len(deleted)}")
    print(f"Custom files: {len(custom)}")

    def print_section(title: str, items: list[str]) -> None:
        if not items:
            return
        print(f"\n{title}:")
        for item in items:
            print(f"- {item}")

    print_section("Modified generated files", modified)
    print_section("Deleted generated files", deleted)
    print_section("Custom files", custom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create Python projects from templates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Generate a project from a template.")
    create.add_argument("--name", required=True, help="Project name.")
    create.add_argument("--template", default="fullstack-app", help="Template folder name.")
    create.add_argument(
        "--output",
        default=".",
        help="Directory where the new project folder should be created.",
    )
    create.add_argument("--author", default="", help="Author full name.")
    create.add_argument("--email", default="", help="Author email.")
    create.add_argument(
        "--description",
        default="Full-stack app with Python backend and Next.js frontend.",
        help="Project description.",
    )
    create.add_argument("--python", default=">=3.11", help="Python version constraint.")
    create.add_argument("--license", default="MIT", help="License identifier.")
    create.add_argument(
        "--var",
        action="append",
        default=[],
        help="Additional template variable in key=value format. Can be repeated.",
    )
    create.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")

    list_cmd = subparsers.add_parser("list", help="List available templates.")
    list_cmd.add_argument("--templates-dir", default="templates", help="Templates directory path.")

    status = subparsers.add_parser("status", help="Show generated/custom file status using manifest.")
    status.add_argument(
        "--project",
        default=".",
        help="Path to a scaffolded project directory (contains .scaffold/manifest.json).",
    )

    return parser


def run_create(args: argparse.Namespace) -> None:
    root = Path(__file__).resolve().parent
    templates_dir = root / "templates"

    project_slug = slugify(args.name)
    destination = Path(args.output).resolve() / project_slug

    author = args.author.strip()
    email = args.email.strip()
    if author and email:
        author_line = f"{author} <{email}>"
    elif author:
        author_line = author
    else:
        author_line = ""

    context = {
        "project_name": args.name.strip(),
        "project_slug": project_slug,
        "package_name": to_package_name(args.name),
        "description": args.description.strip(),
        "python_version": args.python.strip(),
        "license": args.license.strip(),
        "author": author,
        "email": email,
        "author_line": author_line,
        "year": str(dt.datetime.now().year),
    }

    context.update(parse_vars(args.var))
    generated_files = scaffold_project(
        templates_dir=templates_dir,
        template_name=args.template,
        destination=destination,
        context=context,
        overwrite=args.overwrite,
    )
    write_manifest(destination=destination, template_name=args.template, files=generated_files)
    print(f"Project created at: {destination}")
    print(f"Manifest written to: {destination / '.scaffold' / 'manifest.json'}")


def run_list(args: argparse.Namespace) -> None:
    root = Path(__file__).resolve().parent
    templates_dir = (root / args.templates_dir).resolve()
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    templates = sorted(p.name for p in templates_dir.iterdir() if p.is_dir())
    if not templates:
        print("No templates found.")
        return

    print("Available templates:")
    for template in templates:
        print(f"- {template}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        run_create(args)
    elif args.command == "list":
        run_list(args)
    elif args.command == "status":
        run_status(Path(args.project).resolve())


if __name__ == "__main__":
    main()
