# Contributing to Data Product MCP

Thank you for your interest in contributing to the Data Product MCP project!

## Development Setup

### Prerequisites

- Python 3.11 or higher
- uv package manager

### Install Dependencies

```bash
uv sync --extra dev
uv pip install -e .
```

### Testing

Run all tests:
```bash
uv run pytest
```

## Development Configuration

### Use in Claude Desktop (Dev Mode)

Open `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this entry:

```json
{
  "mcpServers": {
    "dataproduct": {
      "command": "uv",
      "args": [
        "run", 
        "--directory", "<path_to_folder>/dataproduct-mcp", 
        "python", "-m", "dataproduct_mcp.server"
      ],
      "env": {
        "DATAMESH_MANAGER_API_KEY": "dmm_live_..."
      }
    }
  }
}
```

### Use with MCP Inspector

```bash
npx @modelcontextprotocol/inspector --config example.config.json --server dataproduct
```

## Code Style

- Follow existing code patterns and conventions
- Use async/await for asynchronous operations
- Include proper error handling
- Add type hints where appropriate
- Write tests for new functionality

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure everything works
5. Submit a pull request with a clear description