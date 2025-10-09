from typing import Any, Dict, List, Optional
import logging
import os
import json
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)


def _load_credentials(credentials_path: Optional[str]) -> tuple[Optional[Any], Optional[str]]:
    """
    Load Google Cloud credentials using a flexible authentication strategy.

    Authentication priority:
    1. If credentials_path is provided and exists:
       a. Try to load as service account JSON
       b. Try to load as workload identity federation config
    2. Fall back to Application Default Credentials (ADC) for local user credentials

    Returns:
        tuple: (credentials, project_id) - project_id may be None if not in credentials
    """
    credentials = None
    project_id = None

    # Strategy 1: Try credentials file if path is provided
    if credentials_path:
        if not os.path.exists(credentials_path):
            raise ValueError(f"Credentials file not found: {credentials_path}")

        try:
            # Try service account JSON
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            logger.info("Using service account credentials from JSON file")

            # Extract project_id from service account file if available
            with open(credentials_path, 'r') as f:
                sa_info = json.load(f)
                project_id = sa_info.get('project_id')

            return credentials, project_id

        except (ValueError, KeyError) as e:
            # Not a valid service account file, try workload identity federation
            logger.debug(f"Not a service account file: {e}")

            try:
                # Try workload identity federation (external account)
                from google.auth import load_credentials_from_file
                credentials, project_id = load_credentials_from_file(credentials_path)
                logger.info("Using workload identity federation credentials")
                return credentials, project_id

            except Exception as e:
                logger.warning(f"Failed to load credentials from file: {e}")
                raise ValueError(
                    f"Credentials file is neither a valid service account JSON nor "
                    f"workload identity federation config: {credentials_path}"
                )

    # Strategy 2: Fall back to Application Default Credentials (ADC)
    try:
        credentials, project_id = default()
        logger.info("Using Application Default Credentials (local user credentials or environment-based)")
        return credentials, project_id

    except DefaultCredentialsError as e:
        raise ValueError(
            "No valid credentials found. Please either:\n"
            "1. Set BIGQUERY_CREDENTIALS_PATH to a service account JSON file\n"
            "2. Set BIGQUERY_CREDENTIALS_PATH to a workload identity federation config\n"
            "3. Run 'gcloud auth application-default login' for local development\n"
            "4. Ensure your environment has valid Application Default Credentials\n"
            f"Error: {e}"
        )


async def execute_bigquery_query(server_info: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """Execute query on BigQuery."""
    # Parse connection parameters
    project_id = server_info.get("project_id") or server_info.get("project")
    credentials_path = os.getenv("BIGQUERY_CREDENTIALS_PATH")

    # Validate required parameters
    if not project_id:
        raise ValueError("Missing required parameter: project_id must be specified in server configuration")

    try:
        logger.info(f"Executing BigQuery query: {query[:100]}...")

        # Load credentials using flexible authentication strategy
        credentials, cred_project_id = _load_credentials(credentials_path)

        # Use project_id from server_info, fall back to credentials if not specified
        if not project_id and cred_project_id:
            project_id = cred_project_id
            logger.info(f"Using project_id from credentials: {project_id}")

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
