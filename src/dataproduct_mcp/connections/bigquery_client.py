from typing import Any, Dict, List
import logging
import os
from google.cloud import bigquery
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


async def execute_bigquery_query(server_info: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Execute query on BigQuery."""
    # Parse connection parameters
    project_id = server_info.get("project_id") or server_info.get("project")
    credentials_path = os.getenv("BIGQUERY_CREDENTIALS_PATH")
    
    # Validate required parameters
    if not project_id:
        raise ValueError("Missing required parameter: project_id must be specified in server configuration")
    
    if not credentials_path:
        raise ValueError(
            "Missing required parameter: credentials_path\n"
            "Set BIGQUERY_CREDENTIALS_PATH environment variable or specify credentials_path in server configuration"
        )
    
    if not os.path.exists(credentials_path):
        raise ValueError(f"Credentials file not found: {credentials_path}")
    
    try:
        logger.info(f"Executing BigQuery query: {query[:100]}...")
        
        # Create credentials and client
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(project=project_id, credentials=credentials)
        
        # Execute query
        query_job = client.query(query)
        results = query_job.result()
        
        # Convert results to list of dictionaries
        rows = []
        for row in results:
            row_dict = {}
            for field in results.schema:
                field_name = field.name
                field_value = row[field_name]
                
                # Handle special BigQuery types
                if field_value is None:
                    row_dict[field_name] = None
                elif hasattr(field_value, 'isoformat'):  # datetime objects
                    row_dict[field_name] = field_value.isoformat()
                elif isinstance(field_value, (int, float, str, bool)):
                    row_dict[field_name] = field_value
                else:
                    row_dict[field_name] = str(field_value)
            
            rows.append(row_dict)
        
        logger.info(f"BigQuery query executed successfully, returned {len(rows)} rows")
        return rows
        
    except ImportError:
        logger.error("google-cloud-bigquery is not installed")
        raise ValueError("google-cloud-bigquery package is required for BigQuery connections")
    except Exception as e:
        logger.error(f"Failed to execute query on BigQuery: {str(e)}")
        raise