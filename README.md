# Data Product MCP

A Model Context Protocol (MCP) server for discovering data products and requesting access in [Data Mesh Manager](https://datamesh-manager.com/).

## Concept

> Idea: Enable AI agents to access high-quality business data with semantic context while respecting data governance policies.

Data Products are managed high-quality business data sets shared with other teams within an organization and specified by data contracts. 
Data contracts describe the structure, semantics, quality, and terms of use. Data products provide the semantic context AI needs to understand not just what data exists, but what it means and how to use it correctly. They are a perfect fit for AI agents to _discover_ which data product are available, evaluate, if they are relevant, and use them to build executable queries to answer business questions or handle specific tasks. 

Data Mesh Manager is a central data product marketplace. AI agents use its MCP server to find relevant data products and to request access while enforcing _data governance_ rules and data contract specific terms of use.

When the relevant data products are identified, we (for now) use technology-specific MCP servers to _query_ the actual data (typically tables in Databricks, Snowflake, S3, or APIs). The LLM can formulate SQL queries by analyzing the structure and semantics stated in the data contracts and execute queries through the MCP servers.


Steps:
1. **Discovery:** Find relevant data products for task in the data product marketplace
2. **Governance:** Check and request access to data products
3. **Query:** Use platform-specific MCP servers to execute SQL statements.


## Tools

1. `dataproduct_list`
    - Lists all data products, or a filtered list, if an optional input is used.
    - Optional inputs:
      - `search_term` (string): Search term to filter data products. Searches in the id, title, and description. Multiple search terms are supported, separated by space.
      - `archetype` (string): Filter for specific data product types. Typical values are: `consumer-aligned`, `aggregate`, `source-aligned`, `application`, `dataconsumer`
      - `status` (string): Filter for specific status, such as `active`
    - Returns: Structured list of data products with their ID, name and description, owner team ID, status, and output ports with server information.

2. `dataproduct_search`
    - A semantic search for data products for a specific user question of use case.
    - Optional inputs:
      - `search_term` (string): Search term to filter data products. Searches in the id, title, and description. Multiple search terms are supported, separated by space.
    - Returns: Structured list of data products with their ID, name and description, owner team ID, status, and output ports with server information.

3. `dataproduct_get`
    - Get a data product by its ID. The data product contains all its output ports and server information.
    - Required inputs:
      - `data_product_id` (string): The data product ID.
    - Returns: Data product details, including access-status

4. `datacontract_get`
    - Get a data contract by its ID.
    - Required inputs:
      - `data_contract_id` (string): The data contract ID.
    - Returns: Data contract as YAML

5. `dataproduct_request_access`
    - Request access to a specific output port of a data product. This creates an access request. Based on the data product configuration, purpose, and data governance rules, the access will be automatically granted, or it will be reviewed by the data product owner.
    - Required inputs:
      - `data_product_id` (string): The data product ID.
      - `output_port_id` (string): The output port ID.
      - `purpose` (string): The specific purpose what the user is doing with the data and and reason why they need access. If the access request need to be approved by the data owner, the purpose is used by the data owner to decide if the access is eligable from a business, technical, and governance point of view.
    - Returns: The status of the access request


## Development Setup

### Install dependencies

```bash
uv sync --extra dev
uv pip install -e .
```

### Run all tests
```bash
uv run pytest
```

### Usage

```bash
uv run python -m dataproduct_mcp.server
```

### Use in Claude Desktop (Dev Mode)

Open `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this entry:

```
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

```
npx @modelcontextprotocol/inspector --config config.json --server dataproduct
```

