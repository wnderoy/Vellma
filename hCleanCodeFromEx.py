#!/usr/bin/env python3
"""
DafnyBench Code Stripper
--------------------------------------------------------------------------------
Processes Dafny (.dfy) files in-place across a directory tree:
1. Strips executable method bodies (replacing them with `{ }`), leaving signatures
   and formal specifications (requires, ensures, modifies, reads, decreases) intact.
2. Preserves checking functions, predicates, lemmas, datatypes, and ghost functions
   completely untouched.
3. Performs in-place file modifications with contract preservation assertions.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
import re
import sys
from typing import List, Tuple

# Initialize standard logger
logging.basicConfig(level=logging.INFO, format="%(name)-10s: %(levelname)-7s %(message)s")
log = logging.getLogger("stripper")


@dataclass
class TokenSpan:
    """Represents a range in the source text."""
    start: int
    end: int
    text: str


class DafnyCodeStripper:
    """
    Parses Dafny source files to locate method declarations and empty their bodies
    while keeping specs (requires, ensures, modifies, reads, decreases) untouched.
    Leaves helper/checking functions, predicates, and lemmas unaltered.
    """

    # Matches methods to strip:
    # Captures:
    #   1: prefix/attributes (e.g. {:test})
    #   2: 'method' keyword
    #   3: method name
    #   4: parameters
    #   5: returns clause (optional)
    METHOD_HEADER_RE = re.compile(
        r"(?P<prefix>(?:\{:[^}]*\}\s*)*)"
        r"\b(?P<kind>method)\s+"
        r"(?P<name>[A-Za-z0-9_]+)\s*"
        r"(?P<type_params><[^>]*>)?\s*"
        r"\((?P<params>[^)]*)\)\s*"
        r"(?:returns\s*\((?P<returns>[^)]*)\))?",
        re.MULTILINE
    )

    @staticmethod
    def _find_matching_brace(text: str, open_idx: int) -> int:
        """Finds the index of the matching closing brace '}' for the brace at open_idx."""
        depth = 0
        in_line_comment = False
        in_block_comment = False
        in_string = False
        in_char = False
        n = len(text)
        i = open_idx

        while i < n:
            ch = text[i]

            # Comment and literal handling
            if not in_line_comment and not in_block_comment and not in_string and not in_char:
                if ch == '/' and i + 1 < n and text[i + 1] == '/':
                    in_line_comment = True
                    i += 2
                    continue
                elif ch == '/' and i + 1 < n and text[i + 1] == '*':
                    in_block_comment = True
                    i += 2
                    continue
                elif ch == '"':
                    in_string = True
                    i += 1
                    continue
                elif ch == "'":
                    in_char = True
                    i += 1
                    continue
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return i
            elif in_line_comment:
                if ch == '\n':
                    in_line_comment = False
            elif in_block_comment:
                if ch == '*' and i + 1 < n and text[i + 1] == '/':
                    in_block_comment = False
                    i += 2
                    continue
            elif in_string:
                if ch == '\\' and i + 1 < n:
                    i += 2
                    continue
                elif ch == '"':
                    in_string = False
            elif in_char:
                if ch == '\\' and i + 1 < n:
                    i += 2
                    continue
                elif ch == "'":
                    in_char = False

            i += 1

        return -1

    def strip_methods_in_content(self, content: str) -> Tuple[str, int]:
        """
        Replaces bodies of executable 'method' declarations with '{ }'.
        Skips 'function', 'predicate', 'lemma', 'twostate lemma', and 'ghost method'.
        """
        replacements = []  # List of (start_idx, end_idx, replacement_text)
        total_stripped = 0

        for match in self.METHOD_HEADER_RE.finditer(content):
            start_pos = match.start()
            name = match.group("name")

            # Check previous tokens to avoid matching 'ghost method'
            preceding_window = content[max(0, start_pos - 40):start_pos].strip()
            if preceding_window.endswith("ghost"):
                # Preserved for checking/ghost logic
                log.debug("Skipping ghost method '%s'", name)
                continue

            # Locate the opening brace '{' for the method body
            # Must skip specification clauses (requires, ensures, etc.)
            search_idx = match.end()
            body_open_idx = -1
            n = len(content)

            in_line_cmt = False
            in_blk_cmt = False
            in_str = False

            while search_idx < n:
                c = content[search_idx]
                if not in_line_cmt and not in_blk_cmt and not in_str:
                    if c == '/' and search_idx + 1 < n and content[search_idx + 1] == '/':
                        in_line_cmt = True
                        search_idx += 2
                        continue
                    elif c == '/' and search_idx + 1 < n and content[search_idx + 1] == '*':
                        in_blk_cmt = True
                        search_idx += 2
                        continue
                    elif c == '"':
                        in_str = True
                        search_idx += 1
                        continue
                    elif c == '{':
                        body_open_idx = search_idx
                        break
                    elif c == ';':
                        # Method without a body (abstract / declaration only)
                        break
                elif in_line_cmt and c == '\n':
                    in_line_cmt = False
                elif in_blk_cmt and c == '*' and search_idx + 1 < n and content[search_idx + 1] == '/':
                    in_blk_cmt = False
                    search_idx += 2
                    continue
                elif in_str and c == '"':
                    in_str = False

                search_idx += 1

            if body_open_idx != -1:
                body_close_idx = self._find_matching_brace(content, body_open_idx)
                if body_close_idx != -1:
                    body_content = content[body_open_idx + 1:body_close_idx].strip()
                    # Only replace if the body is not already empty
                    if body_content:
                        replacements.append((body_open_idx, body_close_idx + 1, "{\n}"))
                        total_stripped += 1
                        log.info("Stripped implementation body for method '%s'", name)

        # Apply replacements in reverse order to preserve string offsets
        new_content = content
        for start_idx, end_idx, repl in reversed(replacements):
            new_content = new_content[:start_idx] + repl + new_content[end_idx:]

        return new_content, total_stripped

    def process_file(self, file_path: Path) -> bool:
        """Processes a single .dfy file in-place and checks spec invariance."""
        assert file_path.exists(), f"File does not exist: {file_path}"
        raw_text = file_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            log.warning("Skipping empty file: %s", file_path)
            return False

        # Extract all contracts to verify invariance after stripping
        requires_clauses = re.findall(r"\brequires\b\s+([^;{\n]+)", raw_text)
        ensures_clauses = re.findall(r"\bensures\b\s+([^;{\n]+)", raw_text)

        stripped_text, count = self.strip_methods_in_content(raw_text)

        if count > 0:
            # Assertion: Guarantee specifications were never removed or modified
            for req in requires_clauses:
                req_norm = " ".join(req.strip().split())
                if req_norm:
                    assert req_norm in " ".join(stripped_text.split()), (
                        f"Assertion Error: Precondition dropped in {file_path.name}: {req_norm}"
                    )
            for ens in ensures_clauses:
                ens_norm = " ".join(ens.strip().split())
                if ens_norm:
                    assert ens_norm in " ".join(stripped_text.split()), (
                        f"Assertion Error: Postcondition dropped in {file_path.name}: {ens_norm}"
                    )

            # In-place write
            file_path.write_text(stripped_text, encoding="utf-8")
            log.info("Updated %s (stripped %d methods)", file_path, count)
            return True
        else:
            log.debug("No methods to strip in %s", file_path)
            return False

    def process_directory(self, folder_path: Path) -> None:
        """Recursively scans and processes all .dfy files in folder_path in-place."""
        assert folder_path.exists() and folder_path.is_dir(), f"Invalid folder: {folder_path}"
        dfy_files = list(folder_path.rglob("*.dfy"))
        log.info("Found %d Dafny (.dfy) files in %s", len(dfy_files), folder_path)

        modified_count = 0
        for f in dfy_files:
            try:
                if self.process_file(f):
                    modified_count += 1
            except Exception as e:
                log.error("Failed processing %s: %s", f, e)

        log.info("Done. Modified %d / %d files in-place.", modified_count, len(dfy_files))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 strip_dafnybench.py <path_to_folder_or_file>")
        sys.exit(1)

    target_path = Path(sys.argv[1])
    stripper = DafnyCodeStripper()

    if target_path.is_file():
        stripper.process_file(target_path)
    elif target_path.is_dir():
        stripper.process_directory(target_path)
    else:
        log.error("Target path does not exist: %s", target_path)
        sys.exit(1)


if __name__ == "__main__":
    main()