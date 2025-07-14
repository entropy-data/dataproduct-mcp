# Data Product MCP

A Model Context Protocol (MCP) server for discovering data products and requesting access in [Data Mesh Manager](https://datamesh-manager.com/), and executing queries on the data platform to access business data.


https://github.com/user-attachments/assets/8c8cd04d-33f6-4e33-856f-6141a41af2bb


## Concept

> Idea: Enable AI agents to find and access any data product for semantic business context while enforcing data governance policies.

or, if you prefer:

> Enable AI to answer any business question.

[Data Products](https://www.datamesh-manager.com/learn/what-is-a-data-product) are managed high-quality business data sets shared with other teams within an organization and specified by data contracts. 
Data contracts describe the structure, semantics, quality, and terms of use. Data products provide the semantic context AI needs to understand not just what data exists, but what it means and how to use it correctly. 
We use [Data Mesh Manager](https://datamesh-manager.com/) as a data product marketplace to search for available data products and evaluate if these are relevant for the task by analyzing its metadata. 

Once a data product is identified, data governance plays a crucial role in ensuring that access to data products is controlled, queries are in line with the data contract's terms of use, and its compliance with organizational global policies. If necessary, the AI agent can request access to the data product's output port, which may require manual approval from the data product owner.

Finally, the LLM can generate SQL queries based on the data contracts data model descriptions and semantics. The SQL queries are executed, while security guardrails are in place to ensure that no sensitive data is misused and attack vectors (such as prompt injections) are mitigated. The results are returned to the AI agent, which can then use them to answer the original business question.

![](docs/architecture.svg)


Steps:
1. **Discovery:** Find relevant data products for task in the data product marketplace
2. **Governance:** Check and request access to data products
3. **Query:** Use platform-specific MCP servers to execute SQL statements.

**Data Mesh Manager** serves as the central data product marketplace and governance layer, providing metadata, access controls, and data contracts for all data products in your organization.

**Data Platforms** (Snowflake, Databricks, etc.) host the actual data and execute queries. The MCP server connects to these platforms to run SQL queries against the data products you have access to.

## Tools

1. `dataproduct_search`
    - Search data products based on the search term. Uses multiple search approaches (list, semantic search) for comprehensive results. Only returns active data products.
    - Optional inputs:
      - `search_term` (string): Search term to filter data products. Searches in the id, title, and description. Multiple search terms are supported, separated by space.
    - Returns: Structured list of data products with their ID, name and description, owner information, and source of the result.

2. `dataproduct_get`
    - Get a data product by its ID. The data product contains all its output ports and server information. The response includes access status for each output port and inlines any data contracts.
    - Required inputs:
      - `data_product_id` (string): The data product ID.
    - Returns: Data product details with enhanced output ports, including access status and inlined data contracts

3. `dataproduct_request_access`
    - Request access to a specific output port of a data product. This creates an access request. Based on the data product configuration, purpose, and data governance rules, the access will be automatically granted, or it will be reviewed by the data product owner.
    - Required inputs:
      - `data_product_id` (string): The data product ID.
      - `output_port_id` (string): The output port ID.
      - `purpose` (string): The specific purpose what the user is doing with the data and the reason why they need access. If the access request needs to be approved by the data owner, the purpose is used by the data owner to decide if the access is eligible from a business, technical, and governance point of view.
    - Returns: Access request details including access_id, status, and approval information

4. `dataproduct_query`
    - Execute a SQL query on a data product's output port. This tool connects to the underlying data platform and executes the provided SQL query. You must have active access to the output port to execute queries.
    - Required inputs:
      - `data_product_id` (string): The data product ID.
      - `output_port_id` (string): The output port ID.
      - `query` (string): The SQL query to execute.
    - Returns: Query results as structured data (limited to 100 rows)
    
## Installation

[//]: # (### Claude Desktop)

[//]: # ()
[//]: # (For Claude Desktop, you can install the MCP server as a [desktop extension]&#40;https://www.anthropic.com/engineering/desktop-extensions&#41;:)

[//]: # ()
[//]: # (Download and open:)

[//]: # ()
[//]: # ([dataproduct-mcp.dxt]&#40;https://github.com/entropy-data/dataproduct-mcp/releases/latest/download/dataproduct-mcp.dxt&#41;)

[//]: # ()
[//]: # (### Other MCP Clients)

Add this entry to your MCP client configuration:

```json
{
  "mcpServers": {
    "dataproduct": {
      "command": "uvx",
      "args": [
        "dataproduct_mcp"
      ],
      "env": {
        "DATAMESH_MANAGER_API_KEY": "dmm_live_user_...",
        "DATAMESH_MANAGER_HOST": "https://api.datamesh-manager.com",
        "SNOWFLAKE_USER": "",
        "SNOWFLAKE_PASSWORD": "",
        "SNOWFLAKE_ROLE": "",
        "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
        "DATABRICKS_HOST": "adb-xxx.azuredatabricks.net",
        "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/xxx",
        "DATABRICKS_CLIENT_ID": "",
        "DATABRICKS_CLIENT_SECRET": "",
        "BIGQUERY_CREDENTIALS_PATH": "/path/to/service-account-key.json"
      }
    }
  }
}
```

This is the format for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`), other MCP clients have similar config options.


### Configuration

#### Data Mesh Manager Configuration

| Environment Variable | Description | Required | Default |
|---------------------|-------------|----------|---------|
| `DATAMESH_MANAGER_API_KEY` | API key for authentication | Yes | N/A |
| `DATAMESH_MANAGER_HOST` | Base URL for self-hosted instances | No | `https://api.datamesh-manager.com` |

To authenticate with Data Mesh Manager, you need to set the `DATAMESH_MANAGER_API_KEY` variable to your API key.

[How to create an API Key in Data Mesh Manager](https://docs.datamesh-manager.com/authentication).

For self-hosted Data Mesh Manager instances, set the `DATAMESH_MANAGER_HOST` environment variable to your instance URL.

(Yes, we will work on OAuth2 based authentication to simplify this in the future.)

#### Snowflake

If you use Snowflake as a data platform, create a [programmatic access token](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens) for your user. Create a new user in Snowflake if the AI agent is not acting on behalf of a real user, create a new service user for the AI agent, and grant it the necessary permissions to access the data products.

You also might need to configure the [network policies](
https://docs.snowflake.com/en/user-guide/programmatic-access-tokens#label-pat-prerequisites-network) to enable programmatic access tokens.


The user needs:
- The `USAGE` privilege on the warehouse you want to use.
- An assigned role (e.g., `DATAPRODUCT_MCP`) with the `USAGE` privilege on the database and schema of the data products you want to access.

You can use the [Snowflake Connector](https://github.com/datamesh-manager/datamesh-manager-connector-snowflake) to automatically grant access to the data in Snowflake, when the access request is approved in Data Mesh Manager.

| Environment Variable                        | Description                                          |
|---------------------------------------------|------------------------------------------------------|
| `DATACONTRACT_SNOWFLAKE_USERNAME`           | Your username                                        |
| `DATACONTRACT_SNOWFLAKE_PASSWORD`           | Your programmatic access token                       |
| `DATACONTRACT_SNOWFLAKE_WAREHOUSE`          | The warehouse you want to use, such as `COMPUTE_WH`. |
| `DATACONTRACT_SNOWFLAKE_ROLE`               | The assigned user role, e.g. `DATAPRODUCT_MCP`       |


#### Databricks

If you use Databricks as a data platform, you need to create a [service principal](https://docs.databricks.com/dev-tools/api/latest/authentication.html#service-principals) and assign it the necessary permissions to access the data products. Create an OAuth2 client ID and secret for the service principal.

You can use the [Databricks Connector](https://github.com/datamesh-manager/datamesh-manager-connector-databricks/) to automatically grant access to the data in Databricks, when the access request is approved in Data Mesh Manager.

You need to configure a Databricks SQL warehouse. The serverless warehouse is recommended for fast query execution.

| Environment Variable                        | Description                                                                                                                                                                            |
|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DATABRICKS_CLIENT_ID`                      | The OAuth2 client ID of the service principal                                                                                                                                          |
| `DATABRICKS_CLIENT_SECRET`                  | The OAuth2 client secret of the service principal                                                                                                                                      |
| `DATABRICKS_HOST`                           | The Databricks workspace URL, without leading https://. e.g. `adb-xxx.azuredatabricks.net`. Go to Compute -> SQL warehouses -> Your Warehouse -> Connection details -> Server hostname |
| `DATABRICKS_HTTP_PATH`                      | The HTTP path for the SQL endpoint, e.g. `/sql/1.0/warehouses/xxx`. Go to Compute -> SQL warehouses -> Your Warehouse -> Connection details -> HTTP path                               |

#### BigQuery

If you use BigQuery as a data platform, you need to create a [service account](https://cloud.google.com/iam/docs/service-accounts) and assign it the necessary permissions to access the data products. Download the service account key as a JSON file.

You can use the [BigQuery Connector](https://github.com/datamesh-manager/datamesh-manager-connector-bigquery/) to automate permission management in BigQuery, when the access request is approved in Data Mesh Manager.

The service account needs the following IAM roles:
- `BigQuery Data Viewer` - to query datasets
- `BigQuery Job User` - to execute queries as jobs

| Environment Variable                        | Description                                                                                                                                                                            |
|---------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `BIGQUERY_CREDENTIALS_PATH`                 | Path to the service account key JSON file                                                                                                                                              |

**Note**: Google Cloud Project ID and dataset information are specified in the data product's output port server configuration, not as environment variables.

To get your service account credentials:
1. Go to the Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Create a new service account or use an existing one
4. Add the `BigQuery Data Viewer` and `BigQuery Job User` roles
5. Generate and download a JSON key file
6. Set `BIGQUERY_CREDENTIALS_PATH` to the path of the JSON file




## Supported Server Types

The `dataproduct_query` tool supports executing queries on data products. The MCP client formulates SQL queries based on the data contract with its data model structure and semantics. 

The following server types are currently supported out-of-the-box:

 | Server Type | Status      | Notes                                                                                                                |
 |-------------|-------------|----------------------------------------------------------------------------------------------------------------------|
 | Snowflake   | ✅           | Requires SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_ROLE environment variables               |
 | Databricks  | ✅           | Requires DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET environment variables |
 | BigQuery    | ✅           | Requires BIGQUERY_CREDENTIALS_PATH environment variable                                                              |
 | S3          | Coming soon | Implemented through DuckDB client                                                                                    |
 | Fabric      | Coming soon |                                                                                                                      |
 
 > **Note:** Use additional Platform-specific MCP servers for other data platform types (e.g., Redshift, PostgreSQL) by adding them to your MCP client.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

## Credits

Maintained by [Simon Harrer](https://www.linkedin.com/in/simonharrer/), [André Deuerling](https://www.linkedin.com/in/andre-deuerling/), and [Jochen Christ](https://www.linkedin.com/in/jochenchrist/).
