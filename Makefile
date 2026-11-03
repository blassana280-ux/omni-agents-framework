PY ?= python3

.PHONY: test registry providers plan run audit protection clean

test:            ## run the real test suite (no network)
	$(PY) -m unittest discover -s tests -t .

registry:        ## validate agents / skills / specialties / permissions
	$(PY) -m omni registry

providers:       ## truthful probe of what can really execute briefs
	$(PY) -m omni providers

plan:            ## make plan REQUEST="..."
	$(PY) -m omni plan "$(REQUEST)"

run:             ## make run REQUEST="..." (needs OMNI_PROVIDER_CMD for real execution)
	$(PY) -m omni run "$(REQUEST)"

audit:           ## read-only audit of the GitHub account
	$(PY) -m omni audit --account blassana280-ux --out audit.json

protection:      ## make protection REPO=owner/name
	$(PY) -m omni protection "$(REPO)"

clean:
	rm -rf .omni __pycache__ */__pycache__ */*/__pycache__ audit.json
