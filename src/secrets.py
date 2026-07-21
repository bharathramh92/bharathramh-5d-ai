import os
from typing import Optional

def get_secret(secret_name: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
    """Retrieves secret from GCP Secret Manager or falls back to local environment variables.

    Args:
        secret_name (str): Secret identifier name.
        fallback_env_var (str, optional): Environment variable fallback name.

    Returns:
        Optional[str]: Secret string value if found, else None.
    """
    env_var_name = fallback_env_var or secret_name
    val = os.getenv(env_var_name)
    if val:
        return val

    # GCP Secret Manager integration attempt
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if project_id:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
    except Exception:
        pass

    return None
