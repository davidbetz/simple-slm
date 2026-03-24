.PHONY: help demo check start stop health test test-all test-disable test-enable test-status test-clarify test-batch benchmark interactive record-tests record-tests-full clean install

PYTHON = python
API_URL = http://localhost:5000

help:
	@echo "Process Command Parser - Make Targets"
	@echo "======================================"
	@echo ""
	@echo "Quick Start:"
	@echo "  make demo           - Run console demo with test suite"
	@echo "  make check          - Verify installation and imports"
	@echo ""
	@echo "Server Management:"
	@echo "  make start          - Start the API server"
	@echo "  make stop           - Stop the API server"
	@echo "  make health         - Check server health"
	@echo ""
	@echo "API Testing:"
	@echo "  make test           - Run basic API test"
	@echo "  make test-all       - Run all API test cases"
	@echo "  make test-disable   - Test disable process commands"
	@echo "  make test-enable    - Test enable process commands"
	@echo "  make test-status    - Test status query commands"
	@echo "  make test-clarify   - Test ambiguous commands"
	@echo "  make test-batch     - Test batch processing"
	@echo ""
	@echo "Performance & Recording:"
	@echo "  make benchmark      - Run performance comparison"
	@echo "  make interactive    - Start interactive test client"
	@echo "  make record-tests   - Quick CSV test report (15 tests)"
	@echo "  make record-tests-full - Full CSV test report (64 tests)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean up temporary files"
	@echo "  make install        - Setup virtual environment (if needed)"

check:
	@echo "Checking installation..."
	@$(PYTHON) -c "import sys; print(f'Python: {sys.version}')"
	@$(PYTHON) -c "from slm import ProcessCommandParser, parse_command; print('✓ slm package imports successfully')"
	@$(PYTHON) -c "from server import app; print('✓ server imports successfully')"
	@$(PYTHON) -c "import sys; sys.path.insert(0, 'tests'); from record_tests import TEST_CASES; print(f'✓ tests import successfully ({len(TEST_CASES)} test cases)')"
	@echo ""
	@echo "✅ All imports working correctly!"

demo:
	@echo "Running console demo..."
	@source env/bin/activate && $(PYTHON) examples/demo.py

start:
	@echo "Starting API server..."
	@echo "Model will load (takes a few seconds)..."
	@source env/bin/activate && $(PYTHON) server.py

stop:
	@echo "Stopping API server..."
	@pkill -f "python server.py" || echo "No server running"

health:
	@echo "Checking server health..."
	@curl -s $(API_URL)/health | python -m json.tool

test: health
	@echo "\n=== Testing: turn off process 94 ==="
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "turn off process 94"}' | python -m json.tool

test-disable:
	@echo "\n=== Test: Disable Commands ==="
	@echo "\n1. turn off process 94:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "turn off process 94"}' | python -m json.tool
	@echo "\n2. disable 77:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "disable 77"}' | python -m json.tool
	@echo "\n3. kill process 42:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "kill process 42"}' | python -m json.tool

test-enable:
	@echo "\n=== Test: Enable Commands ==="
	@echo "\n1. enable process 12:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "enable process 12"}' | python -m json.tool
	@echo "\n2. turn on process 99:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "turn on process 99"}' | python -m json.tool
	@echo "\n3. start process 55:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "start process 55"}' | python -m json.tool

test-status:
	@echo "\n=== Test: Status Queries ==="
	@echo "\n1. what is process 94 doing:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "what is process 94 doing"}' | python -m json.tool
	@echo "\n2. status of process 77:"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "status of process 77"}' | python -m json.tool

test-clarify:
	@echo "\n=== Test: Ambiguous/Unclear Commands ==="
	@echo "\n1. disable process (no ID):"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "disable process"}' | python -m json.tool
	@echo "\n2. don't disable process 94 (negated):"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "don'\''t disable process 94"}' | python -m json.tool
	@echo "\n3. disable process 94 and 95 (multiple):"
	@curl -s -X POST $(API_URL)/parse \
		-H "Content-Type: application/json" \
		-d '{"message": "disable process 94 and 95"}' | python -m json.tool

test-batch:
	@echo "\n=== Test: Batch Processing ==="
	@curl -s -X POST $(API_URL)/batch \
		-H "Content-Type: application/json" \
		-d '{"messages": ["turn off process 94", "enable process 12", "what is process 77 doing", "disable process", "don'\''t disable process 94"]}' | python -m json.tool

test-all: test-disable test-enable test-status test-clarify test-batch
	@echo "\n=== All tests completed ==="

benchmark:
	@echo "Running performance benchmark..."
	@source env/bin/activate && $(PYTHON) tests/benchmark.py

interactive:
	@echo "Starting interactive test client..."
	@source env/bin/activate && $(PYTHON) tests/test_client.py

record-tests:
	@echo "Recording test results to CSV (quick version)..."
	@source env/bin/activate && $(PYTHON) tests/quick_csv.py

record-tests-full:
	@echo "Recording FULL test results to CSV (64 tests, takes ~2 minutes)..."
	@source env/bin/activate && $(PYTHON) tests/record_tests_api.py

install:
	@echo "Setting up Python virtual environment..."
	@if [ ! -d "env" ]; then \
		python3 -m venv env; \
		echo "✓ Virtual environment created"; \
	else \
		echo "✓ Virtual environment already exists"; \
	fi
	@echo "Installing dependencies..."
	@source env/bin/activate && pip install -q flask llama-cpp-python pandas requests
	@echo "✓ Dependencies installed"
	@echo ""
	@echo "Run 'make check' to verify installation"

clean:
	@echo "Cleaning up temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f *.csv 2>/dev/null || true
	@echo "✓ Cleanup complete!"