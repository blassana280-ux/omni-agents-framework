# Résultats de tests — exécution réelle

Commande : `python3 -m unittest discover -s tests -t .`
Date : 2026-10-31 11:05 UTC
Environnement : Python 3.11.2, stdlib seule (pas de pytest), aucun accès réseau requis.

```
test_classification (tests.test_audit.TestAuditAnalysis.test_classification) ... ok
test_overwrite_detected_only_when_upstream_had_the_file (tests.test_audit.TestAuditAnalysis.test_overwrite_detected_only_when_upstream_had_the_file) ... ok
test_detect_clis_reports_availability_truthfully (tests.test_executor.TestProviderDetection.test_detect_clis_reports_availability_truthfully) ... ok
test_env_with_real_command_builds_subprocess_provider (tests.test_executor.TestProviderDetection.test_env_with_real_command_builds_subprocess_provider) ... ok
test_env_with_unusable_command_falls_back_to_manual (tests.test_executor.TestProviderDetection.test_env_with_unusable_command_falls_back_to_manual) ... ok
test_env_without_command_falls_back_to_manual (tests.test_executor.TestProviderDetection.test_env_without_command_falls_back_to_manual) ... ok
test_manual_provider_never_claims_execution (tests.test_executor.TestProviderDetection.test_manual_provider_never_claims_execution) ... ok
test_brief_file_is_written_and_prompt_substituted (tests.test_executor.TestSubprocessProvider.test_brief_file_is_written_and_prompt_substituted) ... ok
test_missing_executable_is_reported_not_faked (tests.test_executor.TestSubprocessProvider.test_missing_executable_is_reported_not_faked) ... ok
test_non_zero_exit_is_a_failure (tests.test_executor.TestSubprocessProvider.test_non_zero_exit_is_a_failure) ... ok
test_successful_command_is_really_executed (tests.test_executor.TestSubprocessProvider.test_successful_command_is_really_executed) ... ok
test_timeout_is_a_failure (tests.test_executor.TestSubprocessProvider.test_timeout_is_a_failure) ... ok
test_insufficient_permission_is_not_reported_as_protected (tests.test_gitops.TestBranchProtectionProbe.test_insufficient_permission_is_not_reported_as_protected) ... ok
test_missing_rule_is_unprotected (tests.test_gitops.TestBranchProtectionProbe.test_missing_rule_is_unprotected) ... ok
test_protected_branch_is_detected (tests.test_gitops.TestBranchProtectionProbe.test_protected_branch_is_detected) ... ok
test_request_protection_is_a_dry_run_by_default (tests.test_gitops.TestBranchProtectionProbe.test_request_protection_is_a_dry_run_by_default) ... ok
test_creates_branch_and_commits_without_touching_main (tests.test_gitops.TestGitWorkflow.test_creates_branch_and_commits_without_touching_main) ... ok
test_dry_run_executes_nothing (tests.test_gitops.TestGitWorkflow.test_dry_run_executes_nothing) ... ok
test_refuses_to_commit_on_main (tests.test_gitops.TestGitWorkflow.test_refuses_to_commit_on_main) ... ok
test_refuses_to_create_or_push_a_protected_branch (tests.test_gitops.TestGitWorkflow.test_refuses_to_create_or_push_a_protected_branch) ... ok
test_live_probe_returns_a_known_state (tests.test_gitops.TestLiveGitHubProbe.test_live_probe_returns_a_known_state) ... skipped 'live GitHub probe disabled (set OMNI_LIVE=1)'
test_open_pr_builds_and_runs_the_github_command (tests.test_gitops.TestPullRequestCommands.test_open_pr_builds_and_runs_the_github_command) ... ok
test_open_pr_dry_run_does_not_call_gh (tests.test_gitops.TestPullRequestCommands.test_open_pr_dry_run_does_not_call_gh) ... ok
test_open_pr_rejects_protected_head_or_identical_branch (tests.test_gitops.TestPullRequestCommands.test_open_pr_rejects_protected_head_or_identical_branch) ... ok
test_more_evidence_wins (tests.test_orchestration.TestArbitration.test_more_evidence_wins) ... ok
test_tie_is_left_unresolved_and_fails_the_gate (tests.test_orchestration.TestArbitration.test_tie_is_left_unresolved_and_fails_the_gate) ... ok
test_incomplete_deliverable_is_sent_back (tests.test_orchestration.TestCorrectionLoop.test_incomplete_deliverable_is_sent_back) ... ok
test_persistently_incomplete_stays_needs_work (tests.test_orchestration.TestCorrectionLoop.test_persistently_incomplete_stays_needs_work) ... ok
test_failure_is_retried_then_reassigned (tests.test_orchestration.TestFailureRecovery.test_failure_is_retried_then_reassigned) ... ok
test_provider_exception_does_not_kill_the_run (tests.test_orchestration.TestFailureRecovery.test_provider_exception_does_not_kill_the_run) ... ok
test_total_failure_escalates_and_never_claims_success (tests.test_orchestration.TestFailureRecovery.test_total_failure_escalates_and_never_claims_success) ... ok
test_manual_provider_never_claims_an_agent_ran (tests.test_orchestration.TestHonestExecution.test_manual_provider_never_claims_an_agent_ran) ... ok
test_every_agent_in_wave_received_a_brief (tests.test_orchestration.TestParallelExecution.test_every_agent_in_wave_received_a_brief) ... ok
test_review_wave_runs_after_work_wave (tests.test_orchestration.TestParallelExecution.test_review_wave_runs_after_work_wave) ... ok
test_wave_is_parallel_not_sequential (tests.test_orchestration.TestParallelExecution.test_wave_is_parallel_not_sequential) ... ok
test_deliverable_is_one_coherent_document (tests.test_orchestration.TestTraceability.test_deliverable_is_one_coherent_document) ... ok
test_trace_records_the_whole_run (tests.test_orchestration.TestTraceability.test_trace_records_the_whole_run) ... ok
test_manifest_is_content_free_and_hashes_the_plan (tests.test_overlays.TestManifest.test_manifest_is_content_free_and_hashes_the_plan) ... ok
test_composition_is_idempotent (tests.test_overlays.TestOverlayComposition.test_composition_is_idempotent) ... ok
test_overlay_does_not_present_the_broken_reference_as_valid (tests.test_overlays.TestOverlayComposition.test_overlay_does_not_present_the_broken_reference_as_valid) ... ok
test_overlay_is_a_separate_marked_section (tests.test_overlays.TestOverlayComposition.test_overlay_is_a_separate_marked_section) ... ok
test_overlay_points_at_the_verified_framework (tests.test_overlays.TestOverlayComposition.test_overlay_points_at_the_verified_framework) ... ok
test_upstream_survives_byte_for_byte (tests.test_overlays.TestOverlayComposition.test_upstream_survives_byte_for_byte) ... ok
test_content_is_hidden_unless_requested (tests.test_overlays.TestOverlayReporting.test_content_is_hidden_unless_requested) ... ok
test_other_runs_are_isolated (tests.test_policy_memory_messaging.TestMessageBus.test_other_runs_are_isolated) ... ok
test_roundtrip (tests.test_policy_memory_messaging.TestMessageBus.test_roundtrip) ... ok
test_unknown_agent_is_rejected (tests.test_policy_memory_messaging.TestMessageBus.test_unknown_agent_is_rejected) ... ok
test_dangerous_action_requires_confirmation (tests.test_policy_memory_messaging.TestPolicy.test_dangerous_action_requires_confirmation) ... ok
test_granted_tool_is_allowed (tests.test_policy_memory_messaging.TestPolicy.test_granted_tool_is_allowed) ... ok
test_path_rule_denies_secrets (tests.test_policy_memory_messaging.TestPolicy.test_path_rule_denies_secrets) ... ok
test_reviewer_cannot_push (tests.test_policy_memory_messaging.TestPolicy.test_reviewer_cannot_push) ... ok
test_ungranted_tool_is_denied (tests.test_policy_memory_messaging.TestPolicy.test_ungranted_tool_is_denied) ... ok
test_unknown_agent_is_denied (tests.test_policy_memory_messaging.TestPolicy.test_unknown_agent_is_denied) ... ok
test_own_namespace_write_and_read (tests.test_policy_memory_messaging.TestSharedMemory.test_own_namespace_write_and_read) ... ok
test_search_finds_value (tests.test_policy_memory_messaging.TestSharedMemory.test_search_finds_value) ... ok
test_secrets_are_redacted_before_persisting (tests.test_policy_memory_messaging.TestSharedMemory.test_secrets_are_redacted_before_persisting) ... ok
test_shared_write_requires_grant (tests.test_policy_memory_messaging.TestSharedMemory.test_shared_write_requires_grant) ... ok
test_ttl_expiry (tests.test_policy_memory_messaging.TestSharedMemory.test_ttl_expiry) ... ok
test_complex_request_forms_squad (tests.test_routing.TestClassification.test_complex_request_forms_squad) ... ok
test_medium_request_uses_one_to_three_agents (tests.test_routing.TestClassification.test_medium_request_uses_one_to_three_agents) ... ok
test_missing_skill_suggests_existing_skills (tests.test_routing.TestClassification.test_missing_skill_suggests_existing_skills) ... ok
test_no_trigger_defaults_to_research (tests.test_routing.TestClassification.test_no_trigger_defaults_to_research) ... ok
test_simple_request_selects_one_specialist (tests.test_routing.TestClassification.test_simple_request_selects_one_specialist) ... ok
test_all_required_specialties_present (tests.test_routing.TestRegistryIntegrity.test_all_required_specialties_present) ... ok
test_duplicate_agent_id_is_rejected (tests.test_routing.TestRegistryIntegrity.test_duplicate_agent_id_is_rejected) ... ok
test_every_agent_documents_provenance (tests.test_routing.TestRegistryIntegrity.test_every_agent_documents_provenance) ... ok
test_shipped_registries_are_coherent (tests.test_routing.TestRegistryIntegrity.test_shipped_registries_are_coherent) ... ok
test_skills_marked_unverified_are_reported_as_such (tests.test_routing.TestRegistryIntegrity.test_skills_marked_unverified_are_reported_as_such) ... ok
test_validation_catches_agent_without_permissions (tests.test_routing.TestRegistryIntegrity.test_validation_catches_agent_without_permissions) ... ok
test_validation_catches_broken_agent_reference (tests.test_routing.TestRegistryIntegrity.test_validation_catches_broken_agent_reference)
The exact class of bug behind the optimiser-mes-agents-IA reference. ... ok

----------------------------------------------------------------------
Ran 70 tests in 4.340s

OK (skipped=1)
```

## Test live (réseau, opt-in)

```
test_live_probe_returns_a_known_state (tests.test_gitops.TestLiveGitHubProbe.test_live_probe_returns_a_known_state) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.311s

OK

[live] branch protection main: {'state': 'insufficient_permission', 'detail': 'token cannot read branch protection (needs Administration:read)'}
```
