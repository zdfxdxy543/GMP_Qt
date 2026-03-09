import json
import re
from pathlib import Path
from typing import Any


class BlockLibraryManager:
    DECLARATION_BEGIN = "//BEGINDECLARATION"
    DECLARATION_END = "//ENDDECLARATION"
    DECLARATION_END_ALIASES = ("//ENDDECLARATION", "//ENDDECLEARATION")

    def __init__(self, library_dir: Path):
        self.library_dir = Path(library_dir)
        self.blocks = []
        self.block_map = {}
        self.reload()

    def reload(self):
        self.blocks = []
        self.block_map = {}

        if not self.library_dir.exists():
            return

        for file_path in sorted(self.library_dir.glob("*.json")):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            block_items = payload.get("blocks", []) if isinstance(payload, dict) else payload
            if not isinstance(block_items, list):
                continue

            for block in block_items:
                if not isinstance(block, dict):
                    continue
                block_id = str(block.get("id", "")).strip()
                if not block_id:
                    continue
                self.blocks.append(block)
                self.block_map[block_id] = block

    def library_names(self):
        names = {str(item.get("library", "未分类")).strip() or "未分类" for item in self.blocks}
        return ["全部程序块库", *sorted(names)]

    def get_block(self, block_id: str):
        return self.block_map.get(block_id)

    def filter_blocks(self, query: str, library_name: str, step_name: str | None = None):
        query_lower = (query or "").strip().lower()
        filtered = []

        for block in self.blocks:
            block_library = str(block.get("library", "未分类")).strip() or "未分类"
            if library_name and library_name != "全部程序块库" and block_library != library_name:
                continue

            if step_name:
                step_list = block.get("steps", [])
                if isinstance(step_list, list) and step_list and step_name not in step_list:
                    continue

            if query_lower:
                haystack = " ".join(
                    [
                        str(block.get("name", "")),
                        str(block.get("id", "")),
                        str(block.get("library", "")),
                        str(block.get("language", "")),
                    ]
                ).lower()
                if query_lower not in haystack:
                    continue

            filtered.append(block)

        return filtered

    def insert_block(self, block: dict[str, Any], target_folder: Path, preferred_file: Path | None = None):
        if not block:
            return {"ok": False, "message": "程序块数据无效"}

        target_folder = Path(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)

        insert_target = block.get("insert_target", {}) if isinstance(block.get("insert_target", {}), dict) else {}
        definition_target = block.get("definition_target", {}) if isinstance(block.get("definition_target", {}), dict) else {}

        insert_file = self._resolve_file(target_folder, insert_target.get("file"), preferred_file)
        insert_anchor = str(insert_target.get("anchor", "// <AUTO_BLOCKS>"))

        def_file = self._resolve_file(target_folder, definition_target.get("file"), insert_file)
        def_anchor = str(definition_target.get("anchor", "// <AUTO_DEFINITIONS>"))

        code_template = str(block.get("code_template", "")).rstrip()
        variables = block.get("variables", []) if isinstance(block.get("variables", []), list) else []

        ensure_result = self.ensure_variable_definitions(block, target_folder, preferred_file)
        written_files = [Path(item) for item in ensure_result.get("written_files", [])]

        if not code_template:
            return {
                "ok": True,
                "message": "仅补充了变量定义（程序块代码为空）",
                "written_files": [str(path) for path in written_files],
                "target_file": str(def_file),
            }

        updated_target_content, target_changed = self._insert_snippets(self._read_text(insert_file), [code_template], insert_anchor)
        if target_changed:
            self._write_text(insert_file, updated_target_content)
            written_files.append(insert_file)

        return {
            "ok": True,
            "message": "程序块插入完成",
            "written_files": [str(path) for path in written_files],
            "target_file": str(insert_file),
        }

    def ensure_variable_definitions(self, block: dict[str, Any], target_folder: Path, preferred_file: Path | None = None):
        return self.ensure_variable_definitions_for_language(block, target_folder, preferred_file, language_name="C")

    def ensure_variable_definitions_for_language(
        self,
        block: dict[str, Any],
        target_folder: Path,
        preferred_file: Path | None = None,
        language_name: str = "C",
    ):
        if not block:
            return {"ok": False, "message": "程序块数据无效", "written_files": []}

        target_folder = Path(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)

        target_file = self._resolve_declaration_file(block, target_folder, preferred_file)
        if target_file is None:
            return {
                "ok": False,
                "message": "当前 IDE 文件不可用，无法检查声明区",
                "written_files": [],
                "definition_file": "",
            }
        preview = self.preview_missing_definitions_for_language(block, target_folder, preferred_file, language_name)
        if not preview.get("ok"):
            return {
                "ok": False,
                "message": preview.get("message", "变量定义检查失败"),
                "written_files": [],
                "definition_file": str(target_file),
            }

        missing_definitions = list(preview.get("missing_definitions", []))
        written_files = []
        if missing_definitions:
            original_text = self._read_text(target_file)
            region = self._find_declaration_region(original_text)
            if region is None:
                return {
                    "ok": False,
                    "message": "当前 IDE 文件未找到声明区注释 //BEGINDECLARATION 或 //ENDDECLARATION(或 //ENDDECLEARATION)，已停止插入",
                    "written_files": [],
                    "definition_file": str(target_file),
                }

            updated_text = self._insert_declarations_into_region(original_text, region, missing_definitions)
            if updated_text != original_text:
                self._write_text(target_file, updated_text)
                written_files.append(target_file)

        return {
            "ok": True,
            "message": "变量定义已检查",
            "written_files": [str(path) for path in written_files],
            "definition_file": str(target_file),
        }

    def preview_missing_definitions(self, block: dict[str, Any], target_folder: Path, preferred_file: Path | None = None):
        return self.preview_missing_definitions_for_language(block, target_folder, preferred_file, language_name="C")

    def preview_missing_definitions_for_language(
        self,
        block: dict[str, Any],
        target_folder: Path,
        preferred_file: Path | None = None,
        language_name: str = "C",
    ):
        if not block:
            return {
                "ok": False,
                "message": "程序块数据无效",
                "missing_definitions": [],
                "definition_file": "",
                "insert_file": "",
            }

        target_folder = Path(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)

        target_file = self._resolve_declaration_file(block, target_folder, preferred_file)
        if target_file is None:
            return {
                "ok": False,
                "message": "当前 IDE 文件不可用，无法检查声明区",
                "missing_definitions": [],
                "definition_file": "",
                "insert_file": "",
            }
        file_text = self._read_text(target_file)
        region = self._find_declaration_region(file_text)
        if region is None:
            return {
                "ok": False,
                "message": "当前 IDE 文件未找到声明区注释 //BEGINDECLARATION 或 //ENDDECLARATION(或 //ENDDECLEARATION)，已停止插入",
                "missing_definitions": [],
                "definition_file": str(target_file),
                "insert_file": str(target_file),
            }

        begin_end = region
        declaration_region_text = file_text[begin_end[0]:begin_end[1]]

        missing_definitions = []
        normalized_language = self._normalize_language(language_name, target_file)
        variables = block.get("variables", []) if isinstance(block.get("variables", []), list) else []
        for var_item in variables:
            if not isinstance(var_item, dict):
                continue
            var_name = str(var_item.get("name", "")).strip()
            if not var_name:
                continue
            if self._is_name_defined(declaration_region_text, var_name):
                continue
            declaration_line = self._build_declaration_line(var_item, normalized_language)
            if declaration_line:
                missing_definitions.append(declaration_line)

        return {
            "ok": True,
            "message": "预检完成",
            "missing_definitions": missing_definitions,
            "definition_file": str(target_file),
            "insert_file": str(target_file),
        }

    def _resolve_declaration_file(self, block: dict[str, Any], target_folder: Path, preferred_file: Path | None):
        if preferred_file is None:
            return None
        return Path(preferred_file)

    def _normalize_language(self, language_name: str, file_path: Path | None = None):
        token = str(language_name or "").strip().lower()
        if token in {"python", "py"}:
            return "python"
        if token in {"c++", "cpp", "cxx", "cc"}:
            return "cpp"
        if token in {"c"}:
            return "c"

        if file_path is not None:
            suffix = file_path.suffix.lower()
            if suffix == ".py":
                return "python"
            if suffix in {".cpp", ".cxx", ".cc", ".hpp", ".hh", ".hxx"}:
                return "cpp"

        return "c"

    def _find_declaration_region(self, text: str):
        content = text or ""
        begin_index = content.find(self.DECLARATION_BEGIN)
        if begin_index < 0:
            return None

        begin_line_end = content.find("\n", begin_index)
        if begin_line_end < 0:
            begin_line_end = len(content)
        else:
            begin_line_end += 1

        end_index = -1
        for end_token in self.DECLARATION_END_ALIASES:
            current_index = content.find(end_token, begin_line_end)
            if current_index >= 0 and (end_index < 0 or current_index < end_index):
                end_index = current_index
        if end_index < 0:
            return None

        return begin_line_end, end_index

    def _insert_declarations_into_region(self, text: str, region: tuple[int, int], declarations: list[str]):
        if not declarations:
            return text

        start_pos, end_pos = region
        end_line_start = text.rfind("\n", 0, end_pos) + 1
        end_line_prefix = text[end_line_start:end_pos]
        indent_match = re.match(r"[ \t]*", end_line_prefix)
        indent = indent_match.group(0) if indent_match else ""

        formatted_lines = []
        for item in declarations:
            stmt = item.strip()
            if not stmt:
                continue
            formatted_lines.append(f"{indent}{stmt}\n")

        insert_text = "\n" + "".join(formatted_lines)
        if insert_text and not insert_text.endswith("\n"):
            insert_text += "\n"

        insert_pos = end_line_start

        return text[:insert_pos] + insert_text + text[insert_pos:]

    def _build_declaration_line(self, variable_item: dict[str, Any], normalized_language: str):
        custom_declaration = str(variable_item.get("declaration", "")).strip()
        if custom_declaration:
            return custom_declaration

        existing_definition = str(variable_item.get("definition", "")).strip()
        if existing_definition:
            if normalized_language == "python":
                return existing_definition.rstrip(";")
            return existing_definition if existing_definition.endswith(";") else f"{existing_definition};"

        name = str(variable_item.get("name", "")).strip()
        if not name:
            return ""

        default_value = str(variable_item.get("default", "")).strip()
        if normalized_language == "python":
            value = default_value or "None"
            return f"{name} = {value}"

        var_type = str(variable_item.get("type", "")).strip() or "float"
        value = default_value or "0"
        return f"{var_type} {name} = {value};"

    def _resolve_file(self, target_folder: Path, relative_path: str | None, fallback_path: Path | None):
        rel = str(relative_path or "").strip()
        if rel:
            return target_folder / rel
        if fallback_path is not None:
            return Path(fallback_path)
        return target_folder / "ctrl.c"

    def _read_text(self, file_path: Path):
        try:
            return file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        except UnicodeDecodeError:
            return file_path.read_text(encoding="gbk", errors="replace")
        except OSError:
            return ""

    def _write_text(self, file_path: Path, text: str):
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")

    def _is_name_defined(self, text: str, name: str):
        return bool(re.search(rf"\b{re.escape(name)}\b", text or ""))

    def _insert_snippets(self, text: str, snippets: list[str], anchor: str):
        content = text or ""
        changed = False

        new_snippets = [item.strip() for item in snippets if item and item.strip() and item.strip() not in content]
        if not new_snippets:
            return content, changed

        block_text = "\n\n".join(new_snippets)

        if anchor and anchor in content:
            content = content.replace(anchor, f"{block_text}\n\n{anchor}", 1)
            changed = True
            return content, changed

        if content and not content.endswith("\n"):
            content += "\n"

        if anchor:
            content += f"\n{anchor}\n"
        content += f"{block_text}\n"
        changed = True
        return content, changed
