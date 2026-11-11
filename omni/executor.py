"""Execution providers.

The framework never pretends an agent ran. A run either goes through a provider
that really executed something (executed=True), or through ManualProvider
which reports pending_human and executed=False.

Configured providers are taken from the environment, never from committed
secrets::

    OMNI_PROVIDER_CMD='claude -p {prompt}'   # local agent CLI
    OMNI_PROVIDER_NAME=claude

The native Mistral provider is selected explicitly with OMNI_PROVIDER=mistral.
It reads credentials from MISTRAL_API_KEY_FILE (preferred) or MISTRAL_API_KEY.
Paid inference is locked unless OMNI_MISTRAL_ALLOW_PAID=1 is explicitly set
for that run. Merely checking provider availability never sends a network
request.
"""