PYTHON ?= python3

.PHONY: install test examples clean

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -v

examples:
	@for f in examples/*.conf; do \
		echo "== $$f"; \
		PYTHONPATH=src $(PYTHON) -m confjson < $$f; \
	done

clean:
	rm -rf .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
