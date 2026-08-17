"""Validation and safe on-disk creation for Gemini-generated projects."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4


class ProjectValidationError(ValueError):
    """Raised when a model response is not safe project data."""


@dataclass(frozen=True)
class ProjectFile:
    path: PurePosixPath
    content: str


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    summary: str
    run_instructions: str
    files: tuple[ProjectFile, ...]


@dataclass(frozen=True)
class WrittenProject:
    root: Path
    file_count: int
    summary: str
    run_instructions: str


@dataclass(frozen=True)
class RepairSpec:
    """Complete contents for only the files Gemini decided must change."""

    summary: str
    diagnosis: str
    run_instructions: str
    changes: tuple[ProjectFile, ...]


@dataclass(frozen=True)
class WrittenRepair:
    project_root: Path
    backup_root: Path
    changed_paths: tuple[PurePosixPath, ...]
    summary: str
    diagnosis: str
    run_instructions: str


MAX_FILES = 250
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_FILES = 250
MAX_CONTEXT_BYTES = 2 * 1024 * 1024
MAX_SINGLE_CONTEXT_FILE_BYTES = 256 * 1024
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")
_TEXT_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".html", ".htm", ".css", ".scss", ".sql", ".sh", ".ps1", ".bat", ".cmd", ".go",
    ".rs", ".java", ".kt", ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".swift", ".vue", ".svelte",
    ".xml", ".gradle", ".properties", ".env", ".dockerfile",
}
_TEXT_FILENAMES = {"dockerfile", "makefile", "readme", "license", ".gitignore", ".editorconfig", "requirements"}
_IGNORED_DIRECTORIES = {
    ".git", ".svn", ".hg", ".atlas-backups", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", "dist", "build", ".next", "coverage",
}
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def safe_project_name(value: str) -> str:
    name = _SAFE_NAME.sub("-", value.strip()).strip(".-")[:60].lower()
    return name or "gemini-project"


def _extract_json(text: str) -> str:
    """Accept JSON with an accidental Markdown fence, but nothing more ambiguous."""
    text = text.strip()
    if text.startswith("```"):
        newline = text.find("\n")
        if newline < 0 or not text.endswith("```"):
            raise ProjectValidationError("Gemini returned an incomplete JSON code block.")
        text = text[newline + 1 : -3].strip()
    return text


def _safe_relative_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise ProjectValidationError("Every generated file needs a non-empty path.")
    normalised = value.replace("\\", "/").strip()
    path = PurePosixPath(normalised)
    if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] in {"", "."}:
        raise ProjectValidationError(f"Unsafe project file path rejected: {value!r}")
    if any(part.endswith(":") for part in path.parts):
        raise ProjectValidationError(f"Unsafe project file path rejected: {value!r}")
    for part in path.parts:
        stem = part.split(".", 1)[0].rstrip(". ").upper()
        if part.endswith((".", " ")) or any(character in part for character in '<>:"|?*') or stem in _WINDOWS_RESERVED_NAMES:
            raise ProjectValidationError(f"Unsafe project file path rejected: {value!r}")
    return path


def parse_project_spec(response_text: str, requested_name: str) -> ProjectSpec:
    """Parse a structured-output response and enforce bounded, relative files."""
    try:
        data: Any = json.loads(_extract_json(response_text))
    except json.JSONDecodeError as error:
        raise ProjectValidationError("Gemini did not return valid project JSON. Try again.") from error

    if not isinstance(data, dict):
        raise ProjectValidationError("The project response must be a JSON object.")
    raw_files = data.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ProjectValidationError("The project response did not include any files.")
    if len(raw_files) > MAX_FILES:
        raise ProjectValidationError(f"The response has more than {MAX_FILES} files.")

    paths: set[PurePosixPath] = set()
    parsed_files_by_path: dict[PurePosixPath, ProjectFile] = {}
    total_bytes = 0
    for item in raw_files:
        if not isinstance(item, dict):
            raise ProjectValidationError("Each generated file must be a JSON object.")
        path = _safe_relative_path(item.get("path"))
        if not _is_text_candidate(Path(path.name)):
            raise ProjectValidationError(f"Repair change {path} is not a supported text/source file.")
        content = item.get("content")
        if not isinstance(content, str):
            raise ProjectValidationError(f"Generated file {path} has no text content.")
        if path in parsed_files_by_path:
            total_bytes -= len(parsed_files_by_path[path].content.encode("utf-8"))
        parsed_files_by_path[path] = ProjectFile(path=path, content=content)
        paths.add(path)
        total_bytes += len(content.encode("utf-8"))
        if total_bytes > MAX_TOTAL_BYTES:
            raise ProjectValidationError("Generated project exceeds the 8 MB safety limit.")

    parsed_files = list(parsed_files_by_path.values())
    return ProjectSpec(
        name=safe_project_name(str(data.get("project_name") or requested_name)),
        summary=str(data.get("summary") or "Gemini-generated project."),
        run_instructions=str(data.get("run_instructions") or "Review the generated README.md."),
        files=tuple(parsed_files),
    )


def parse_repair_spec(response_text: str) -> RepairSpec:
    """Parse repair JSON and apply the same strict path and size checks as generation."""
    try:
        data: Any = json.loads(_extract_json(response_text))
    except json.JSONDecodeError as error:
        raise ProjectValidationError("Gemini did not return valid repair JSON. Try the repair again.") from error
    if not isinstance(data, dict):
        raise ProjectValidationError("The repair response must be a JSON object.")
    raw_changes = data.get("changes")
    if not isinstance(raw_changes, list) or not raw_changes:
        raise ProjectValidationError("Gemini found no writable repair changes. Give it more error detail and try again.")
    if len(raw_changes) > MAX_FILES:
        raise ProjectValidationError(f"The repair response has more than {MAX_FILES} changed files.")

    paths: set[PurePosixPath] = set()
    changes_by_path: dict[PurePosixPath, ProjectFile] = {}
    total_bytes = 0
    for item in raw_changes:
        if not isinstance(item, dict):
            raise ProjectValidationError("Each repair change must be a JSON object.")
        path = _safe_relative_path(item.get("path"))
        content = item.get("content")
        if not isinstance(content, str):
            raise ProjectValidationError(f"Repair change {path} has no complete text content.")
        if path in changes_by_path:
            total_bytes -= len(changes_by_path[path].content.encode("utf-8"))
        changes_by_path[path] = ProjectFile(path=path, content=content)
        paths.add(path)
        total_bytes += len(content.encode("utf-8"))
        if total_bytes > MAX_TOTAL_BYTES:
            raise ProjectValidationError("Repair exceeds the 8 MB safety limit.")

    changes = list(changes_by_path.values())
    return RepairSpec(
        summary=str(data.get("summary") or "Gemini applied a project repair."),
        diagnosis=str(data.get("diagnosis") or "No diagnosis was returned."),
        run_instructions=str(data.get("run_instructions") or "Run the project again and check the error output."),
        changes=tuple(changes),
    )


def _is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_SUFFIXES or path.name.lower() in _TEXT_FILENAMES


def collect_project_context(project_directory: Path) -> tuple[str, int, int, bool]:
    """Read source/configuration text for repair without sending generated artifacts or huge files.

    Returns a marked-up bundle, included file count, byte count, and a flag that
    tells the UI whether a size bound excluded any text files.
    """
    root = project_directory.expanduser().resolve()
    if not root.is_dir():
        raise ProjectValidationError("Choose an existing project folder to repair.")
    blocks: list[str] = []
    included_files = 0
    included_bytes = 0
    truncated = False
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part.lower() in _IGNORED_DIRECTORIES for part in relative.parts[:-1]) or not _is_text_candidate(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_SINGLE_CONTEXT_FILE_BYTES or included_files >= MAX_CONTEXT_FILES or included_bytes + size > MAX_CONTEXT_BYTES:
            truncated = True
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="utf-8-sig")
            except (UnicodeDecodeError, OSError):
                truncated = True
                continue
        except OSError:
            continue
        blocks.append(f"\n===== FILE: {relative.as_posix()} =====\n{content}\n===== END FILE =====\n")
        included_files += 1
        included_bytes += len(content.encode("utf-8"))
    if not blocks:
        raise ProjectValidationError("No readable source or configuration files were found in that folder.")
    return "".join(blocks), included_files, included_bytes, truncated


def _unique_destination(parent: Path, name: str) -> Path:
    candidate = parent / name
    index = 2
    while candidate.exists():
        candidate = parent / f"{name}-{index}"
        index += 1
    return candidate


def write_project(spec: ProjectSpec, parent_directory: Path) -> WrittenProject:
    """Create a new project directory without touching existing projects."""
    parent = parent_directory.expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    root = _unique_destination(parent, spec.name)
    root.mkdir()
    root_resolved = root.resolve()

    try:
        for file in spec.files:
            destination = (root / Path(*file.path.parts)).resolve()
            if root_resolved not in destination.parents:
                raise ProjectValidationError(f"Unsafe destination rejected: {file.path}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(file.content, encoding="utf-8", newline="\n")
    except Exception:
        # The directory is intentionally retained so an I/O failure is inspectable/recoverable.
        raise

    return WrittenProject(
        root=root,
        file_count=len(spec.files),
        summary=spec.summary,
        run_instructions=spec.run_instructions,
    )


def apply_repair(spec: RepairSpec, project_directory: Path) -> WrittenRepair:
    """Apply a fully validated repair with backups and best-effort rollback."""
    root = project_directory.expanduser().resolve()
    if not root.is_dir():
        raise ProjectValidationError("Choose an existing project folder to repair.")
    root_resolved = root.resolve()
    targets: list[tuple[ProjectFile, Path]] = []
    # Validate the entire repair before mutating the project. This prevents a
    # later bad path from leaving earlier files changed.
    for change in spec.changes:
        destination = (root / Path(*change.path.parts)).resolve()
        if root_resolved not in destination.parents:
            raise ProjectValidationError(f"Unsafe repair destination rejected: {change.path}")
        if destination.exists() and destination.is_dir():
            raise ProjectValidationError(f"Repair destination is a directory: {change.path}")
        targets.append((change, destination))

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_root = root / ".atlas-backups" / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)
    existing_paths: set[Path] = set()
    temporaries: list[tuple[ProjectFile, Path, Path]] = []
    replaced: list[tuple[ProjectFile, Path]] = []
    try:
        for change, destination in targets:
            if destination.exists():
                existing_paths.add(destination)
                backup = backup_root / Path(*change.path.parts)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.atlas-tmp")
            temporary.write_text(change.content, encoding="utf-8", newline="\n")
            temporaries.append((change, destination, temporary))
        for change, destination, temporary in temporaries:
            temporary.replace(destination)
            replaced.append((change, destination))
    except Exception:
        # Restore files already replaced, and remove files that the repair had
        # newly introduced. The original backup remains for manual recovery too.
        for change, destination in reversed(replaced):
            backup = backup_root / Path(*change.path.parts)
            try:
                if destination in existing_paths and backup.is_file():
                    shutil.copy2(backup, destination)
                elif destination.exists():
                    destination.unlink()
            except OSError:
                pass
        for _change, _destination, temporary in temporaries:
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
        raise

    return WrittenRepair(
        project_root=root,
        backup_root=backup_root,
        changed_paths=tuple(change.path for change in spec.changes),
        summary=spec.summary,
        diagnosis=spec.diagnosis,
        run_instructions=spec.run_instructions,
    )
