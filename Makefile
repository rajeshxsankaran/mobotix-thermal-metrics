all:

.PHONY: test
test:
	docker build -t mobotix-thermal-metrics .
	docker run --rm --entrypoint=python3 mobotix-thermal-metrics app/test.py
