"""Versioned, read-only metadata catalog for external agent skills.

The catalog stores provenance and trust metadata only. It never downloads,
imports, evaluates, or executes skill content.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
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
class SkillTrustRecord:
    """Pinned content digest and review lifecycle state for a skill."""

    skill_id: str
    source_id: str
    sha256: str
    state: str


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
    if (parts.scheme != "https" or parts.hostname != "github.com" or parts.username
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
    return SkillTrustRecord(skill_id=skill_id, source_id=source_id, sha256=digest.lower(), state=state)
