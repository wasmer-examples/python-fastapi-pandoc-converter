
run-native:
	uv run python ./src/main.py

run-wasmer:
	uvx shipit-cli --wasmer --start

format:
	uv format

deploy:
	uvx shipit-cli \
		--wasmer \
		--wasmer-deploy \
		--wasmer-registry https://registry.wasmer.io \
		--wasmer-app-owner wasmer-examples \
		--wasmer-app-name pandoc-converter-example
