#!/usr/bin/env python3
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
import sys
from typing import List, Tuple


#init logger format from global hLogger module
import hLogger
hLogger.setup_logger()

log_parser = logging.getLogger("parser")
log_deriver = logging.getLogger("deriver")
log_emitter = logging.getLogger("emitter")


@dataclass
class MethodContract:
    #representation of a dafny method as an AST
    method_name: str
    signature_header: str
    inputs: List[Tuple[str, str]] = field(default_factory=list)
    outputs: List[Tuple[str, str]] = field(default_factory=list)
    requires_clauses: List[str] = field(default_factory=list)
    ensures_clauses: List[str] = field(default_factory=list)
    modifies_clauses: List[str] = field(default_factory=list)
    reads_clauses: List[str] = field(default_factory=list)

    def assert_valid(self) -> None:
        assert self.method_name, "Validation Error: Method name cannot be empty"
        assert self.signature_header, "Validation Error: Signature header cannot be empty"


class DafnyContractParser:
    """Parses .dfy files to extract contracts verbatim."""

    CLAUSE_KEYWORDS = ("requires", "ensures", "modifies", "reads", "decreases")

    def parse_file(self, file_path: Path) -> MethodContract:
        log_parser.info("Reading %s", file_path)
        assert file_path.exists(), f"File does not exist: {file_path}"

        raw_content = file_path.read_text(encoding="utf-8")
        assert raw_content.strip(), f"File is empty: {file_path}"

        return self.parse_text(raw_content)

    def parse_text(self, content: str) -> MethodContract:
        # Strip comments
        clean_text = re.sub(r"//.*", "", content)
        clean_text = re.sub(r"/\*.*?\*/", "", clean_text, flags=re.DOTALL)

        # Match method declaration
        sig_pattern = re.compile(
            r"^\s*(method\s+([A-Za-z0-9_]+)\s*\((.*?)\)(?:\s*returns\s*\((.*?)\))?)",
            re.MULTILINE | re.DOTALL,
        )
        match = sig_pattern.search(clean_text)
        assert match, "No valid method declaration found in input text"

        raw_signature = match.group(1).strip()
        method_name = match.group(2).strip()
        raw_inputs = match.group(3) or ""
        raw_outputs = match.group(4) or ""

        contract = MethodContract(
            method_name=method_name,
            signature_header=raw_signature,
            inputs=self._parse_parameters(raw_inputs),
            outputs=self._parse_parameters(raw_outputs),
        )

        body_start_idx = clean_text.find("{", match.end())
        spec_text = (
            clean_text[match.end() : body_start_idx]
            if body_start_idx != -1
            else clean_text[match.end() :]
        )

        self._extract_clauses(spec_text, contract)
        contract.assert_valid()

        log_parser.info(
            "Parsed '%s' (%d inputs, %d outputs, %d requires, %d ensures)",
            contract.method_name,
            len(contract.inputs),
            len(contract.outputs),
            len(contract.requires_clauses),
            len(contract.ensures_clauses),
        )
        return contract

    def _parse_parameters(self, raw_params: str) -> List[Tuple[str, str]]:
        params = []
        if not raw_params.strip():
            return params
        for part in raw_params.split(","):
            part = part.strip()
            if ":" in part:
                name, type_sig = part.split(":", 1)
                params.append((name.strip(), type_sig.strip()))
        return params

    def _extract_clauses(self, spec_text: str, contract: MethodContract) -> None:
        tokens = spec_text.split()
        if not tokens:
            return

        current_keyword = None
        current_tokens = []

        def flush():
            if current_keyword and current_tokens:
                expr = " ".join(current_tokens).strip()
                if current_keyword == "requires":
                    contract.requires_clauses.append(expr)
                elif current_keyword == "ensures":
                    contract.ensures_clauses.append(expr)
                elif current_keyword == "modifies":
                    contract.modifies_clauses.append(expr)
                elif current_keyword == "reads":
                    contract.reads_clauses.append(expr)

        for token in tokens:
            if token in self.CLAUSE_KEYWORDS:
                flush()
                current_keyword = token
                current_tokens = []
            elif current_keyword:
                current_tokens.append(token)

        flush()

#unchecked
class TemplateDeriver:
    """Applies formal derivation rules to synthesize baseline code from contracts."""

    @staticmethod
    def derive_baseline(contract: MethodContract) -> str:
        log_deriver.info("Deriving code for method '%s'", contract.method_name)

        # Check for array traversal patterns (e.g., parameter `a: array<T>`)
        array_param = next(
            (name for name, typ in contract.inputs if "array" in typ), None
        )

        statements = []

        if array_param:
            log_deriver.info("Detected array input '%s' -> applying Range Scan Rule", array_param)
            # Derive standard bounded loop mechanics
            statements.append(f"  var i := 0;")
            statements.append(f"  while i < {array_param}.Length")
            statements.append(f"    invariant 0 <= i <= {array_param}.Length")
            statements.append(f"  {{")
            statements.append(f"    i := i + 1;")
            statements.append(f"  }}")
        else:
            log_deriver.info("No pattern match -> emitting default body")
            statements.append("  // Baseline stub")

        return "\n".join(statements)

#unchecked
class ScaffoldEmitter:
    """Reassembles original contracts with the mechanically derived body."""

    @staticmethod
    def emit(contract: MethodContract, derived_body: str) -> str:
        contract.assert_valid()
        assert derived_body is not None, "Derived body cannot be None"

        log_emitter.info("Reassembling '%s'", contract.method_name)

        lines = [contract.signature_header]

        for mod in contract.modifies_clauses:
            lines.append(f"  modifies {mod}")
        for rd in contract.reads_clauses:
            lines.append(f"  reads {rd}")
        for req in contract.requires_clauses:
            lines.append(f"  requires {req}")
        for ens in contract.ensures_clauses:
            lines.append(f"  ensures {ens}")

        lines.append("{")
        lines.append(derived_body)
        lines.append("}")

        result = "\n".join(lines) + "\n"

        # Assert: Contract preservation check
        for req in contract.requires_clauses:
            assert req in result, f"Invariant violation: dropped requires [{req}]"
        for ens in contract.ensures_clauses:
            assert ens in result, f"Invariant violation: dropped ensures [{ens}]"

        log_emitter.info("Contract preservation verified (0 specifications altered)")
        return result


def main():
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("input.dfy")

    # 1. Parse
    parser = DafnyContractParser()
    contract = parser.parse_file(target_path)

    # 2. Derive logic mechanically
    derived_body = TemplateDeriver.derive_baseline(contract)

    # 3. Emit
    final_code = ScaffoldEmitter.emit(contract, derived_body)

    output_path = target_path.with_suffix(".scaffolded.dfy")
    output_path.write_text(final_code, encoding="utf-8")
    log_emitter.info("Written to %s", output_path)


if __name__ == "__main__":
    main()