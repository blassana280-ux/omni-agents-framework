"""Providers stdlib : exécution RÉELLE, refus de simuler, résultats exacts."""

from __future__ import annotations

import pytest

from cf100.providers.stdlib import (ProviderUnavailable, analyze_file,
                                    analyze_logs, make_provider_for,
                                    read_file, scan_dependencies,
                                    scan_text)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_read_file_real_sha256(tmp_path):
    path = _write(tmp_path, "note.txt", "contenu de démonstration")
    result = read_file({"path": path})
    assert result["content"] == "contenu de démonstration"
    assert len(result["sha256"]) == 64
    assert result["size_bytes"] > 0


def test_read_file_missing_refused(tmp_path):
    with pytest.raises(ProviderUnavailable):
        read_file({"path": str(tmp_path / "inexistant.txt")})


def test_analyze_file_detects_secrets_and_suspicious(tmp_path):
    path = _write(tmp_path, "suspect.py",
                  "token = ghp_DEMOdemoDEMOdemoDEMOdemoDEMOde\n"
                  "os.system('demo')\n")
    result = analyze_file({"path": path})
    assert result["secrets_found"] >= 1
    assert any("os.system" in s for s in result["suspicious_patterns"])
    assert result["verdict"] == "suspect"


def test_analyze_file_clean_verdict(tmp_path):
    path = _write(tmp_path, "propre.py", "def add(a, b):\n    return a + b\n")
    result = analyze_file({"path": path})
    assert result["verdict"] == "clean"
    assert result["secrets_found"] == 0


def test_scan_text_never_logs_full_secret():
    findings = scan_text({"text": "le ghp_DEMOdemoDEMOdemoDEMOdemoDEMOde "
                                  "fuit dans le code"})
    assert findings["count"] >= 1
    assert findings["secret_material_logged"] is False
    for f in findings["findings"]:
        assert "DEMOdemo" not in f["sample"]  # échantillon tronqué


def test_scan_dependencies_reports_findings(tmp_path):
    path = _write(tmp_path, "requirements.txt",
                  "requests\nflask==3.0.0\nrequests==2.31.0\n"
                  "git+https://example.com/demo\n")
    result = scan_dependencies({"path": path})
    assert result["count"] == 4
    assert "requests" in result["unpinned"][0]
    assert "requests" in result["duplicates"]
    assert len(result["external_sources"]) == 1


def test_analyze_logs_counts_errors_and_logins(tmp_path):
    path = _write(tmp_path, "app.log",
                  "ERROR timeout service-x\n"
                  "Failed login from 203.0.113.7\n"
                  "Failed login from 203.0.113.7\n"
                  "INFO ok\n")
    result = analyze_logs({"path": path})
    assert result["errors"] == 1
    assert result["failed_logins"] == 2
    assert result["top_ips"][0]["ip"] == "203.0.113.7"
    assert result["verdict"] == "suspect"


def test_provider_refuses_unimplemented_action():
    provider = make_provider_for()
    with pytest.raises(ProviderUnavailable):
        provider({"action": "write_doc", "path": "x"})  # jamais simulé


def test_provider_executes_real_action(tmp_path):
    path = _write(tmp_path, "f.txt", "donnée réelle")
    provider = make_provider_for()
    result = provider({"action": "read_file", "path": path})
    assert result["content"] == "donnée réelle"
