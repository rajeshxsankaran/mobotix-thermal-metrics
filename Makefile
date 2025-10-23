all:

.PHONY: test
test:
	docker build -t mobotix-thermal-metrics .
