"""Versioned, read-only metadata catalog for external agent skills.

The catalog stores provenance and trust metadata only. It never downloads,
imports, evaluates, or executes skill content.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
LIFECYCLE_STATES = frozenset({
    "discovered", "pinned", "metadata_validated", "scanned", "evaluated",
    "approved", "available", "active", "quarantined", "revoked",
})
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class SkillCatalogError(ValueError):
    """Raised when catalog metadata is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class SkillSource:
    """Immutable provenance for one externally maintained skill."""

    source_id: str
    skill_id: str
    repository_url: str
    skill_path: str
    commit_sha: str
    license_spdx: Optional[str] = None
    upstream_identity: Optional[str] = None
    maintainer: Optional[str] = None


@dataclass(frozen=True)
class SkillApproval:
    """Human approval evidence bound to one exact content digest."""

    approver: str
    digest: str
    reference: str


@dataclass(frozen=True)
class SkillTrustRecord:
    """Pinned content digest and review lifecycle state for a skill."""

    skill_id: str
    source_id: str
    sha256: str
    state: str
    approval: Optional[SkillApproval] = None


class SkillCatalog:
    """Read-only index joining source provenance to trust-lock records."""

    def __init__(self, sources: Dict[str, SkillSource], records: Dict[str, SkillTrustRecord]):
        self._sources = dict(sources)
        self._records = dict(records)

    @classmethod
    def load(cls, directory: str | Path) -> "SkillCatalog":
        root = Path(directory)
        source_doc = _read_document(root / "skill-sources.json", "sources")
        lock_doc = _read_document(root / "skills.lock.json", "skills")

        sources: Dict[str, SkillSource] = {}
        source_ids = set()
        skill_ids = set()
        identities = set()
        for index, item in enumerate(source_doc["sources"]):
            where = f"skill-sources.json sources[{index}]"
            if not isinstance(item, dict):
                raise SkillCatalogError(f"{where} must be an object")
            source = _parse_source(item, where)
            if source.source_id in source_ids:
                raise SkillCatalogError(f"duplicate source_id: {source.source_id}")
            if source.skill_id in skill_ids:
                raise SkillCatalogError(f"duplicate skill_id: {source.skill_id}")
            identity = (source.repository_url.casefold(), source.skill_path, source.commit_sha.casefold())
            if identity in identities:
                raise SkillCatalogError(f"duplicate source identity for skill: {source.skill_id}")
            source_ids.add(source.source_id)
            skill_ids.add(source.skill_id)
            identities.add(identity)
            sources[source.source_id] = source

        records: Dict[str, SkillTrustRecord] = {}
        record_sources = set()
        for index, item in enumerate(lock_doc["skills"]):
            where = f"skills.lock.json skills[{index}]"
            if not isinstance(item, dict):
                raise SkillCatalogError(f"{where} must be an object")
            record = _parse_trust_record(item, where)
            if record.skill_id in records:
                raise SkillCatalogError(f"duplicate skill_id in lock: {record.skill_id}")
            if record.source_id in record_sources:
                raise SkillCatalogError(f"duplicate source_id in lock: {record.source_id}")
            source = sources.get(record.source_id)
            if source is None:
                raise SkillCatalogError(f"unknown source_id in lock: {record.source_id}")
            if source.skill_id != record.skill_id:
                raise SkillCatalogError(
                    f"skill_id mismatch for source_id {record.source_id}: "
                    f"{record.skill_id} != {source.skill_id}"
                )
            records[record.skill_id] = record
            record_sources.add(record.source_id)

        missing_locks = sorted(source.skill_id for source in sources.values() if source.skill_id not in records)
        if missing_locks:
            raise SkillCatalogError("missing lock record for skill_id: " + ", ".join(missing_locks))
        return cls(sources, records)

    def validate(self) -> list[str]:
        """Return consistency issues without mutating catalog records."""
        problems = []
        seen_identities = set()
        seen_skills = set()
        for source_id, source in self._sources.items():
            if source_id != source.source_id:
                problems.append(f"source map key mismatch: {source_id}")
            if source.skill_id in seen_skills:
                problems.append(f"duplicate skill_id: {source.skill_id}")
            seen_skills.add(source.skill_id)
            identity = (source.repository_url.casefold(), source.skill_path, source.commit_sha.casefold())
            if identity in seen_identities:
                problems.append(f"duplicate source identity for skill: {source.skill_id}")
            seen_identities.add(identity)
        seen_record_sources = set()
        for skill_id, record in self._records.items():
            if skill_id != record.skill_id:
                problems.append(f"lock map key mismatch: {skill_id}")
            source = self._sources.get(record.source_id)
            if source is None:
                problems.append(f"unknown source_id in lock: {record.source_id}")
            elif source.skill_id != skill_id:
                problems.append(f"skill_id mismatch for source_id: {record.source_id}")
            if record.source_id in seen_record_sources:
                problems.append(f"duplicate source_id in lock: {record.source_id}")
            seen_record_sources.add(record.source_id)
            if not _SHA256_RE.fullmatch(record.sha256):
                problems.append(f"invalid sha256 for skill_id: {skill_id}")
            if record.state not in LIFECYCLE_STATES:
                problems.append(f"unsupported state for skill_id: {skill_id}")
            if record.state in {"approved", "available", "active"} and record.approval is None:
                problems.append(f"missing human approval for skill_id: {skill_id}")
            elif record.approval is not None and record.approval.digest != record.sha256:
                problems.append(f"approval digest mismatch for skill_id: {skill_id}")
        for source in self._sources.values():
            if source.skill_id not in self._records:
                problems.append(f"missing lock record for skill_id: {source.skill_id}")
        return problems

    def get(self, skill_id: str) -> Optional[Tuple[SkillSource, SkillTrustRecord]]:
        """Return the source and lock record, or None for an unknown or legacy ID."""
        record = self._records.get(skill_id)
        if record is None:
            return None
        return self._sources[record.source_id], record

    def items(self) -> Tuple[Tuple[SkillSource, SkillTrustRecord], ...]:
        """Return catalog entries in stable skill-ID order."""
        return tuple(
            (self._sources[record.source_id], record)
            for skill_id, record in sorted(self._records.items())
        )

    def __len__(self) -> int:
        return len(self._records)


def _read_document(path: Path, collection: str) -> dict:
    if not path.is_file():
        raise SkillCatalogError(f"missing catalog file: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SkillCatalogError(f"invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise SkillCatalogError(f"{path.name} root must be an object")
    version = value.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise SkillCatalogError(f"unsupported schema_version in {path.name}: {version!r}")
    entries = value.get(collection)
    if not isinstance(entries, list):
        raise SkillCatalogError(f"{path.name} field {collection!r} must be an array")
    return value


def _required_text(item: dict, key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SkillCatalogError(f"{where} requires non-empty {key}")
    return value.strip()


def _optional_text(item: dict, key: str, where: str) -> Optional[str]:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SkillCatalogError(f"{where} {key} must be non-empty text or null")
    return value.strip()


def _parse_source(item: dict, where: str) -> SkillSource:
    source_id = _required_text(item, "source_id", where)
    skill_id = _required_text(item, "skill_id", where)
    repository_url = _required_text(item, "repository_url", where)
    parts = urlsplit(repository_url)
    segments = [part for part in parts.path.split("/") if part]
    if (parts.scheme != "https" or parts.netloc != "github.com" or parts.username
            or parts.password or parts.query or parts.fragment or len(segments) != 2
            or repository_url.endswith("/") or segments[1].endswith(".git")):
        raise SkillCatalogError(f"{where} repository_url must be a canonical https://github.com/owner/repo URL")

    skill_path = _required_text(item, "skill_path", where)
    path = PurePosixPath(skill_path)
    if (path.is_absolute() or "\\" in skill_path or path.as_posix() != skill_path
            or any(part in ("", ".", "..") for part in skill_path.split("/"))):
        raise SkillCatalogError(f"{where} skill_path must be a normalized relative POSIX path")

    commit_sha = _required_text(item, "commit_sha", where)
    if not _COMMIT_RE.fullmatch(commit_sha):
        raise SkillCatalogError(f"{where} commit_sha must be a full 40-character Git commit SHA")
    license_spdx = _optional_text(item, "license_spdx", where)
    return SkillSource(
        source_id=source_id,
        skill_id=skill_id,
        repository_url=repository_url,
        skill_path=skill_path,
        commit_sha=commit_sha.lower(),
        license_spdx=license_spdx,
        upstream_identity=_optional_text(item, "upstream_identity", where),
        maintainer=_optional_text(item, "maintainer", where),
    )


def _parse_trust_record(item: dict, where: str) -> SkillTrustRecord:
    skill_id = _required_text(item, "skill_id", where)
    source_id = _required_text(item, "source_id", where)
    digest = _required_text(item, "sha256", where)
    if not _SHA256_RE.fullmatch(digest):
        raise SkillCatalogError(f"{where} sha256 must be a 64-character hexadecimal digest")
    state = _required_text(item, "state", where)
    if state not in LIFECYCLE_STATES:
        raise SkillCatalogError(f"{where} has unsupported state: {state}")
    raw_approval = item.get("approval")
    approval = None
    if raw_approval is not None:
        if not isinstance(raw_approval, dict):
            raise SkillCatalogError(f"{where} approval must be an object or null")
        approver = _required_text(raw_approval, "approver", f"{where} approval")
        approval_digest = _required_text(raw_approval, "digest", f"{where} approval")
        reference = _required_text(raw_approval, "reference", f"{where} approval")
        if not _SHA256_RE.fullmatch(approval_digest) or approval_digest.lower() != digest.lower():
            raise SkillCatalogError(f"{where} approval digest must match the lock sha256")
        approval = SkillApproval(approver=approver, digest=approval_digest.lower(), reference=reference)
    if state in {"approved", "available", "active"} and approval is None:
        raise SkillCatalogError(f"{where} state {state} requires a human approval record")
    return SkillTrustRecord(
        skill_id=skill_id, source_id=source_id, sha256=digest.lower(), state=state,
        approval=approval,
    )


@dataclass(frozen=True)
class SkillIngestionResult:
    """Normalized text snapshot returned by safe, offline skill ingestion."""

    source: SkillSource
    files: Tuple[str, ...]
    sha256: str
    _contents: Tuple[Tuple[str, str], ...]
    _metadata: Tuple[Tuple[str, str], ...]
    findings: Tuple[str, ...] = ()

    @property
    def contents(self) -> Dict[str, str]:
        """Return a defensive copy of normalized file contents."""
        return dict(self._contents)

    @property
    def metadata(self) -> Dict[str, str]:
        """Return parsed SKILL.md frontmatter as a fresh dictionary."""
        return dict(self._metadata)


MAX_SKILL_FILES = 128
MAX_SKILL_BYTES = 1024 * 1024


def ingest_skill(
    source: SkillSource,
    files: Dict[str, str | bytes],
    *,
    policy: Optional["SkillPolicy"] = None,
) -> SkillIngestionResult:
    """Validate and hash caller-supplied text files without executing or fetching them.

    Paths are normalized as relative POSIX paths. Parent traversal, absolute paths,
    Windows separators, duplicate normalized paths, invalid UTF-8 and oversized
    snapshots are rejected before a deterministic SHA-256 digest is produced.
    """
    if not isinstance(source, SkillSource):
        raise SkillCatalogError("source must be a SkillSource")
    source = _parse_source({
        "source_id": source.source_id, "skill_id": source.skill_id,
        "repository_url": source.repository_url, "skill_path": source.skill_path,
        "commit_sha": source.commit_sha, "license_spdx": source.license_spdx,
        "upstream_identity": source.upstream_identity, "maintainer": source.maintainer,
    }, "source")
    if policy is not None and not isinstance(policy, SkillPolicy):
        raise SkillCatalogError("policy must be a SkillPolicy")
    max_files = policy.max_files if policy else MAX_SKILL_FILES
    max_bytes = policy.max_bytes if policy else MAX_SKILL_BYTES
    if not isinstance(files, dict) or not files:
        raise SkillCatalogError("files must be a non-empty mapping of relative paths to text")
    if len(files) > max_files:
        raise SkillCatalogError(f"skill contains too many files (max {max_files})")

    normalized: Dict[str, str] = {}
    total_bytes = 0
    for raw_path, payload in files.items():
        if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
            raise SkillCatalogError("skill file path must be non-empty text without NUL bytes")
        if raw_path.startswith("/") or "\\" in raw_path:
            raise SkillCatalogError(f"invalid absolute or non-POSIX skill path: {raw_path!r}")
        segments = raw_path.split("/")
        if any(part == ".." for part in segments):
            raise SkillCatalogError(f"path traversal is not allowed: {raw_path!r}")
        clean_segments = [part for part in segments if part not in ("", ".")]
        if not clean_segments:
            raise SkillCatalogError(f"invalid empty skill path: {raw_path!r}")
        path = PurePosixPath(*clean_segments).as_posix()
        if path in normalized:
            raise SkillCatalogError(f"duplicate normalized skill file path: {path}")
        if isinstance(payload, bytes):
            try:
                file_content = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SkillCatalogError(f"skill file is not valid UTF-8: {path}") from exc
        elif isinstance(payload, str):
            file_content = payload
        else:
            raise SkillCatalogError(f"skill file payload must be str or UTF-8 bytes: {path}")
        if "\x00" in file_content:
            raise SkillCatalogError(f"skill file contains NUL bytes and is not accepted as text: {path}")
        total_bytes += len(file_content.encode("utf-8"))
        if total_bytes > max_bytes:
            raise SkillCatalogError(f"skill snapshot exceeds {max_bytes} bytes")
        normalized[path] = file_content

    if "SKILL.md" not in normalized:
        raise SkillCatalogError("skill snapshot must contain SKILL.md at its root")

    ordered = tuple(sorted(normalized.items()))
    canonical = json.dumps(ordered, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    metadata = _parse_skill_frontmatter(normalized["SKILL.md"])
    return SkillIngestionResult(
        source=source,
        files=tuple(path for path, _ in ordered),
        sha256=digest,
        _contents=ordered,
        _metadata=tuple(sorted(metadata.items())),
    )


def _parse_skill_frontmatter(content: str) -> Dict[str, str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillCatalogError("SKILL.md must start with YAML frontmatter")
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise SkillCatalogError("SKILL.md frontmatter is missing its closing --- delimiter") from exc

    fields: Dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise SkillCatalogError(f"unsupported SKILL.md frontmatter syntax at line {line_number}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", key):
            raise SkillCatalogError(f"invalid SKILL.md frontmatter key at line {line_number}")
        if key in fields:
            raise SkillCatalogError(f"duplicate SKILL.md frontmatter key: {key}")
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1].replace("''", "'")
        if not value:
            raise SkillCatalogError(f"SKILL.md frontmatter value is empty: {key}")
        fields[key] = value

    for required in ("name", "description"):
        if required not in fields:
            raise SkillCatalogError(f"SKILL.md frontmatter requires {required}")
    return fields


@dataclass(frozen=True)
class SkillPolicy:
    """Conservative policy limits for untrusted skill metadata and static scans."""

    allowed_licenses: Tuple[str, ...] = ("MIT", "Apache-2.0")
    blocking_severities: Tuple[str, ...] = ("critical",)
    max_files: int = MAX_SKILL_FILES
    max_bytes: int = MAX_SKILL_BYTES

    def __post_init__(self) -> None:
        if not self.allowed_licenses or any(not isinstance(item, str) or not item.strip() for item in self.allowed_licenses):
            raise SkillCatalogError("allowed_licenses must contain non-empty SPDX identifiers")
        allowed_severities = {"low", "medium", "high", "critical"}
        if not self.blocking_severities or any(item not in allowed_severities for item in self.blocking_severities):
            raise SkillCatalogError("blocking_severities contains an unsupported severity")
        if type(self.max_files) is not int or self.max_files < 1:
            raise SkillCatalogError("max_files must be a positive integer")
        if type(self.max_bytes) is not int or self.max_bytes < 1:
            raise SkillCatalogError("max_bytes must be a positive integer")


@dataclass(frozen=True)
class SkillScanFinding:
    """One transparent static-pattern match; not a malware verdict."""

    rule_id: str
    severity: str
    path: str
    line_number: int
    evidence: str


@dataclass(frozen=True)
class SkillScanReport:
    """Static scan output tied to the exact ingested content digest."""

    sha256: str
    rules_scanned: Tuple[str, ...]
    findings: Tuple[SkillScanFinding, ...]
    blocking_severities: Tuple[str, ...] = ("critical",)

    @property
    def blocking(self) -> bool:
        return any(item.severity in self.blocking_severities for item in self.findings)


_STATIC_RULES = (
    ("destructive-command", "critical", re.compile(r"\b(?:rm\s+-[^\n]*\brf\b|shred\b|mkfs(?:\.\w+)?\b|dd\s+if=)", re.IGNORECASE)),
    ("shell-execution", "medium", re.compile(r"\b(?:os\.system\s*\(|subprocess\.(?:run|Popen|call)\s*\(|(?:bash|sh)\s+-c\b)", re.IGNORECASE)),
    ("network-upload", "high", re.compile(r"\b(?:curl\b[^\n]*(?:--data(?:-binary)?|-d\b|--upload-file)|wget\b[^\n]*--post-file|requests\.(?:post|put)\s*\()", re.IGNORECASE)),
    ("secret-access", "high", re.compile(r"\b(?:os\.(?:environ|getenv)\b|id_rsa\b|(?:api|secret|access)[_-]?key\b)|(?:~?/\.ssh/)", re.IGNORECASE)),
    ("prompt-injection", "high", re.compile(r"\b(?:ignore (?:all )?(?:previous|prior) instructions|reveal (?:the )?(?:system prompt|secrets)|bypass (?:the )?safety)", re.IGNORECASE)),
)


def load_skill_policy(directory: str | Path) -> SkillPolicy:
    """Load and validate the optional policy JSON using the standard library."""
    path = Path(directory) / "skill-policy.json"
    if not path.is_file():
        raise SkillCatalogError("missing catalog policy file: skill-policy.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SkillCatalogError(f"invalid JSON in skill-policy.json: {exc}") from exc
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != SCHEMA_VERSION:
        raise SkillCatalogError("unsupported or malformed skill-policy.json schema_version")
    licenses = value.get("allowed_licenses")
    severities = value.get("blocking_severities")
    limits = value.get("limits", {})
    if not isinstance(licenses, list) or any(not isinstance(x, str) or not x.strip() for x in licenses):
        raise SkillCatalogError("skill-policy.json allowed_licenses must be an array of non-empty strings")
    if not isinstance(severities, list) or not severities or any(x not in {"low", "medium", "high", "critical"} for x in severities):
        raise SkillCatalogError("skill-policy.json blocking_severities contains an unsupported severity")
    if not isinstance(limits, dict):
        raise SkillCatalogError("skill-policy.json limits must be an object")
    max_files = limits.get("max_files", MAX_SKILL_FILES)
    max_bytes = limits.get("max_bytes", MAX_SKILL_BYTES)
    if type(max_files) is not int or max_files < 1 or type(max_bytes) is not int or max_bytes < 1:
        raise SkillCatalogError("skill-policy.json limits must be positive integers")
    return SkillPolicy(
        allowed_licenses=tuple(licenses), blocking_severities=tuple(severities),
        max_files=max_files, max_bytes=max_bytes,
    )


def scan_skill(snapshot: SkillIngestionResult, *, policy: SkillPolicy = SkillPolicy()) -> SkillScanReport:
    """Run documented static patterns over text; never evaluate skill instructions."""
    if not isinstance(snapshot, SkillIngestionResult):
        raise SkillCatalogError("scan_skill requires a SkillIngestionResult")
    findings = []
    for rule_id, severity, pattern in _STATIC_RULES:
        for path, file_content in snapshot._contents:
            for line_number, line in enumerate(file_content.splitlines(), start=1):
                match = pattern.search(line)
                if match:
                    findings.append(SkillScanFinding(
                        rule_id=rule_id, severity=severity, path=path,
                        line_number=line_number, evidence=line.strip()[:240],
                    ))
    return SkillScanReport(
        sha256=snapshot.sha256,
        rules_scanned=tuple(rule_id for rule_id, _, _ in _STATIC_RULES),
        findings=tuple(findings),
        blocking_severities=policy.blocking_severities,
    )


_ALLOWED_TRANSITIONS = {
    "discovered": frozenset({"pinned", "quarantined", "revoked"}),
    "pinned": frozenset({"metadata_validated", "quarantined", "revoked"}),
    "metadata_validated": frozenset({"scanned", "quarantined", "revoked"}),
    "scanned": frozenset({"evaluated", "quarantined", "revoked"}),
    "evaluated": frozenset({"approved", "quarantined", "revoked"}),
    "approved": frozenset({"available", "quarantined", "revoked"}),
    "available": frozenset({"active", "quarantined", "revoked"}),
    "active": frozenset({"available", "quarantined", "revoked"}),
    "quarantined": frozenset({"revoked"}),
    "revoked": frozenset(),
}


def transition_skill(
    record: SkillTrustRecord,
    target_state: str,
    *,
    approval: Optional[SkillApproval] = None,
    current_digest: Optional[str] = None,
    source: Optional[SkillSource] = None,
    scan_report: Optional[SkillScanReport] = None,
    policy: SkillPolicy = SkillPolicy(),
) -> SkillTrustRecord:
    """Advance one trust state, requiring scan, licence, digest and human approval evidence."""
    if not isinstance(record, SkillTrustRecord):
        raise SkillCatalogError("record must be a SkillTrustRecord")
    if not isinstance(record.sha256, str) or not _SHA256_RE.fullmatch(record.sha256):
        raise SkillCatalogError("record must contain a valid SHA-256 digest")
    record = replace(record, sha256=record.sha256.lower())
    if target_state not in LIFECYCLE_STATES:
        raise SkillCatalogError(f"unsupported target state: {target_state}")
    if target_state not in _ALLOWED_TRANSITIONS.get(record.state, frozenset()):
        raise SkillCatalogError(f"invalid lifecycle transition: {record.state} -> {target_state}")

    if target_state == "scanned":
        if scan_report is None or scan_report.sha256 != record.sha256:
            raise SkillCatalogError("scanned state requires a scan report for the current digest")
    elif target_state == "evaluated":
        if scan_report is None or scan_report.sha256 != record.sha256:
            raise SkillCatalogError("evaluation requires a scan report for the current digest")
        if scan_report.blocking:
            raise SkillCatalogError("critical static finding blocks evaluation")
        if source is None:
            raise SkillCatalogError("evaluation requires matching source provenance")
        source = _parse_source({
            "source_id": source.source_id, "skill_id": source.skill_id,
            "repository_url": source.repository_url, "skill_path": source.skill_path,
            "commit_sha": source.commit_sha, "license_spdx": source.license_spdx,
            "upstream_identity": source.upstream_identity, "maintainer": source.maintainer,
        }, "source")
        if source.skill_id != record.skill_id or source.source_id != record.source_id:
            raise SkillCatalogError("evaluation requires matching source provenance")
        if source.license_spdx not in policy.allowed_licenses:
            raise SkillCatalogError("unknown or disallowed skill license blocks evaluation")
    elif target_state == "approved":
        if not isinstance(approval, SkillApproval):
            raise SkillCatalogError("approved state requires explicit human approval evidence")
        if (not isinstance(approval.approver, str) or not approval.approver.strip()
                or not isinstance(approval.reference, str) or not approval.reference.strip()):
            raise SkillCatalogError("approval requires a human approver and review reference")
        if not isinstance(approval.digest, str) or not _SHA256_RE.fullmatch(approval.digest) or approval.digest.lower() != record.sha256:
            raise SkillCatalogError("approval digest does not match the current skill digest")
        approval = replace(approval, digest=approval.digest.lower())
    elif target_state in {"available", "active"}:
        if approval is not None:
            raise SkillCatalogError("approval can only be supplied when entering approved state")
        if current_digest is None or not _SHA256_RE.fullmatch(current_digest):
            raise SkillCatalogError(f"{target_state} state requires the current SHA-256 digest")
        if current_digest.lower() != record.sha256:
            raise SkillCatalogError("current digest changed since review; skill cannot be activated")
        if record.approval is None or record.approval.digest != record.sha256:
            raise SkillCatalogError(f"{target_state} state requires a current human approval")
    elif approval is not None:
        raise SkillCatalogError("approval evidence is only accepted for the approved transition")

    return replace(record, state=target_state, approval=approval if target_state == "approved" else record.approval)
