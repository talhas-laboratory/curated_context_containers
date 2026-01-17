#!/bin/bash
# Install and configure MCP Gateway for Claude Desktop

set -e

echo "🚀 Installing Local Latent Containers MCP Gateway for Claude Desktop"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if backend is running
echo "Step 1: Checking if LLC backend is running..."
if curl -s http://localhost:7801/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running${NC}"
    echo ""
    echo "Please start the backend first:"
    echo "  cd $PROJECT_ROOT"
    echo "  make up"
    echo ""
    exit 1
fi

# Step 2: Get token
echo ""
echo "Step 2: Reading token..."
TOKEN="${LLC_MCP_TOKEN:-}"
if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ Token found in LLC_MCP_TOKEN${NC}"
else
    echo -e "${RED}✗ LLC_MCP_TOKEN not set${NC}"
    echo "Export LLC_MCP_TOKEN before running this script."
    exit 1
fi

# Step 3: Install MCP gateway
echo ""
echo "Step 3: Installing MCP gateway..."
cd "$SCRIPT_DIR"
pip install -e . -q
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ MCP gateway installed${NC}"
else
    echo -e "${RED}✗ Installation failed${NC}"
    exit 1
fi

# Step 4: Test MCP server
echo ""
echo "Step 4: Testing MCP server..."
LLC_BASE_URL="http://localhost:7801" LLC_MCP_TOKEN="$TOKEN" timeout 3 python -m llc_mcp_gateway.server > /dev/null 2>&1 &
PID=$!
sleep 2
if kill -0 $PID 2>/dev/null; then
    kill $PID 2>/dev/null
    echo -e "${GREEN}✓ MCP server works${NC}"
else
    echo -e "${YELLOW}⚠ Could not fully test MCP server (this is OK)${NC}"
fi

# Step 5: Create Claude Desktop config
echo ""
echo "Step 5: Setting up Claude Desktop configuration..."

CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

# Create directory if it doesn't exist
mkdir -p "$CLAUDE_CONFIG_DIR"

# Backup existing config
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    cp "$CLAUDE_CONFIG_FILE" "$CLAUDE_CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}⚠ Backed up existing config${NC}"
fi

# Check if config already has our server
if [ -f "$CLAUDE_CONFIG_FILE" ] && grep -q "local-latent-containers" "$CLAUDE_CONFIG_FILE"; then
    echo -e "${YELLOW}⚠ Configuration already exists in Claude Desktop config${NC}"
    echo "  If you want to update it, edit: $CLAUDE_CONFIG_FILE"
else
    # Create or update config
    if [ ! -f "$CLAUDE_CONFIG_FILE" ] || [ ! -s "$CLAUDE_CONFIG_FILE" ]; then
        # File doesn't exist or is empty - create new
        cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "local-latent-containers": {
      "command": "python",
      "args": [
        "-m",
        "llc_mcp_gateway.server"
      ],
      "env": {
        "LLC_BASE_URL": "http://localhost:7801",
        "LLC_MCP_TOKEN": "$TOKEN"
      }
    }
  }
}
EOF
        echo -e "${GREEN}✓ Created new Claude Desktop config${NC}"
    else
        # File exists with content - need to merge
        echo -e "${YELLOW}⚠ Claude Desktop config exists with other servers${NC}"
        echo "  You need to manually add the MCP server config."
        echo "  Copy this configuration into your existing file:"
        echo ""
        echo "  File: $CLAUDE_CONFIG_FILE"
        echo ""
        cat "$SCRIPT_DIR/claude_desktop_config_READY.json"
        echo ""
    fi
fi

# Step 6: Verify expressionist-art container
echo ""
echo "Step 6: Verifying expressionist-art container..."
CONTAINER_CHECK=$(curl -s -X POST http://localhost:7801/v1/containers/list \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": "active"}' | grep -o "expressionist-art" | head -1)

if [ "$CONTAINER_CHECK" = "expressionist-art" ]; then
    echo -e "${GREEN}✓ expressionist-art container found${NC}"
    
    # Get stats
    STATS=$(curl -s -X POST http://localhost:7801/v1/containers/describe \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"container": "expressionist-art"}')
    
    DOC_COUNT=$(echo "$STATS" | grep -o '"document_count":[0-9]*' | cut -d: -f2)
    CHUNK_COUNT=$(echo "$STATS" | grep -o '"chunk_count":[0-9]*' | cut -d: -f2)
    
    echo "  Documents: $DOC_COUNT"
    echo "  Chunks: $CHUNK_COUNT"
else
    echo -e "${YELLOW}⚠ expressionist-art container not found${NC}"
    echo "  You may need to create it first"
fi

# Final instructions
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "1. ${YELLOW}Restart Claude Desktop${NC}"
echo "   - Quit Claude completely (Cmd+Q)"
echo "   - Reopen Claude Desktop"
echo ""
echo "2. ${YELLOW}Test the connection${NC}"
echo "   Ask Claude: \"What MCP tools are available?\""
echo "   You should see: containers_list, containers_search, etc."
echo ""
echo "3. ${YELLOW}Search the expressionist-art container${NC}"
echo "   Try: \"Search the expressionist-art container for information"
echo "         about how expressionists used color\""
echo ""
echo "Configuration saved to:"
echo "  $CLAUDE_CONFIG_FILE"
echo ""
echo "For troubleshooting, see:"
echo "  $PROJECT_ROOT/CLAUDE_DESKTOP_SETUP.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"






















