#!/bin/bash

# This script runs the deployment validation test.

# Set the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Python test script
python3 "${SCRIPT_DIR}/test_deployment.py"