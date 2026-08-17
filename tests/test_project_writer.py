from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from atlas.project_writer import (
    ProjectValidationError,
    apply_repair,
    collect_project_context,
    parse_project_spec,
    parse_repair_spec,
    write_project,
)


def payload(files: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "project_name": "my neat project",
            "summary": "A small test project.",
            "run_instructions": "python main.py",
            "files": files,
        }
    )


def repair_payload(changes: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "summary": "Fixed the broken greeting.",
            "diagnosis": "The name was not defined.",
            "run_instructions": "python main.py",
            "changes": changes,
        }
    )


class ProjectWriterTests(unittest.TestCase):
    def test_parses_fenced_structured_response(self) -> None:
        spec = parse_project_spec(
            "```json\n" + payload([{"path": "src/main.py", "content": "print('ok')"}]) + "\n```", "fallback"
        )
        self.assertEqual(spec.name, "my-neat-project")
        self.assertEqual(spec.files[0].path.as_posix(), "src/main.py")

    def test_rejects_unsafe_paths(self) -> None:
        for unsafe_path in ("../outside.py", "/etc/passwd", "C:/Windows/file.txt", "NUL.txt", "folder/file. ", ""):
            with self.subTest(unsafe_path=unsafe_path), self.assertRaises(ProjectValidationError):
                parse_project_spec(payload([{"path": unsafe_path, "content": "nope"}]), "fallback")

    def test_deduplicates_repeated_generated_files(self) -> None:
        spec = parse_project_spec(
            payload([
                {"path": "main.py", "content": "print('first')"},
                {"path": "main.py", "content": "print('second')"},
                {"path": "README.md", "content": "hello"},
            ]),
            "fallback",
        )
        self.assertEqual(len(spec.files), 2)
        self.assertEqual(spec.files[0].path.as_posix(), "main.py")
        self.assertEqual(spec.files[0].content, "print('second')")

    def test_creates_new_folder_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            spec = parse_project_spec(payload([{"path": "hello.txt", "content": "hello"}]), "fallback")
            first = write_project(spec, Path(directory))
            second = write_project(spec, Path(directory))
            self.assertEqual(first.root.name, "my-neat-project")
            self.assertEqual(second.root.name, "my-neat-project-2")
            self.assertEqual((first.root / "hello.txt").read_text(), "hello")

    def test_collects_code_and_applies_repair_with_a_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            (root / "main.py").write_text("print(name)\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
            context, count, _bytes, truncated = collect_project_context(root)
            self.assertIn("FILE: main.py", context)
            self.assertNotIn("ignored.js", context)
            self.assertEqual(count, 1)
            self.assertFalse(truncated)

            repair = parse_repair_spec(repair_payload([{"path": "main.py", "content": "name = 'Atlas'\nprint(name)\n"}]))
            written = apply_repair(repair, root)
            self.assertIn("name = 'Atlas'", (root / "main.py").read_text())
            self.assertEqual((written.backup_root / "main.py").read_text(), "print(name)\n")
