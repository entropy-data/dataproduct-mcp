# Data Product MCP

A Model Context Protocol (MCP) server for discovering data products and requesting access in [Data Mesh Manager](https://datamesh-manager.com/), and executing queries on the data platform to access business data.

{% include youtube.html id="egKCGGmIFLI" %}


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

You must have [uv](https://docs.astral.sh/uv/#__tabbed_1_1) installed.

Then add this entry to your MCP client configuration:

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
        "QUERY_ACCESS_EVALUATION_ENABLED": "true",
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
| `QUERY_ACCESS_EVALUATION_ENABLED` | Enable/disable AI-based query access evaluation | No | `true` |

To authenticate with Data Mesh Manager, you need to set the `DATAMESH_MANAGER_API_KEY` variable to your API key.

[How to create an API Key in Data Mesh Manager](https://docs.datamesh-manager.com/authentication).

For self-hosted Data Mesh Manager instances, set the `DATAMESH_MANAGER_HOST` environment variable to your instance URL.

Set `QUERY_ACCESS_EVALUATION_ENABLED` to `false` to disable AI-based query access evaluation when AI features are not enabled in your Data Mesh Manager instance.

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

<a href="https://github.com/entropy-data/dataproduct-mcp" class="github-corner" aria-label="View source on GitHub"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;" aria-hidden="true"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>