#!/bin/bash

# Load user configuration if present
if [ -f "$HOME/.llc_mcp_config" ]; then
    source "$HOME/.llc_mcp_config"
fi

# Debug Log
LOG=/tmp/cherry_mcp_debug.log
echo "--- $(date) ---" >> $LOG
echo "Starting wrapper script" >> $LOG
echo "LLC_MCP_BRIDGE_URL: $LLC_MCP_BRIDGE_URL" >> $LOG
echo "LLC_MCP_BRIDGE_TOKEN: ${LLC_MCP_BRIDGE_TOKEN:0:20}..." >> $LOG

# Ensure we are in the right directory
SCRIPT_DIR="/Users/talhauddin/software/curated_context_containers/mcp-server"
echo "Changing directory to $SCRIPT_DIR" >> $LOG
cd "$SCRIPT_DIR" || { echo "Failed to cd to $SCRIPT_DIR" >> $LOG; exit 1; }

# Ensure absolute path to uv
UV="/opt/homebrew/bin/uv"

if [ ! -f "$UV" ]; then
    echo "ERROR: uv not found at $UV" >> $LOG
    exit 1
fi

echo "Executing uv run..." >> $LOG

# Execute uv run with explicit environment variable passing
# We redirect stderr to our log so it doesn't pollute the generic stderr (or we can let it pass if needed)
# Crucially, we MUST let STDOUT pass through to Cherry Studio.
LLC_MCP_BRIDGE_URL="$LLC_MCP_BRIDGE_URL" LLC_MCP_BRIDGE_TOKEN="$LLC_MCP_BRIDGE_TOKEN" "$UV" run -q mcp_bridge.py 2>> $LOG

EXIT_CODE=$?
echo "Exited with $EXIT_CODE" >> $LOG
exit $EXIT_CODE
