PY ?= python3
PORT ?= 8000

.PHONY: run install data verify

install:
	$(PY) -m pip install -r requirements.txt

# Testsatz laden und vorverarbeiten (siehe DATA.md)
data:
	./preprocess/fetch_testset.sh
	$(PY) preprocess/prep_bhsd.py --n-per-type 2
	$(PY) preprocess/prep_cq500.py $(shell cat preprocess/testset_cq500.txt)

verify:
	$(PY) preprocess/verify.py

# Startet den Server und öffnet den Browser
run:
	@(sleep 1.5 && $(PY) -m webbrowser -t http://localhost:$(PORT) >/dev/null 2>&1 &)
	$(PY) -m uvicorn server.app:app --port $(PORT)
