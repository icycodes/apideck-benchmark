#!/usr/bin/env python3
"""
Fetch all Issue Tracking collection users from Apideck and persist them to users.json.
"""

import json
import logging
import os

from apideck_unify import Apideck, UNSET
from apideck_unify.types.basemodel import Unset

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "output.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Also mirror INFO+ to stdout for visibility during development
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

# ---------------------------------------------------------------------------
# Credentials & config (all sourced from environment variables)
# ---------------------------------------------------------------------------
API_KEY = os.environ["APIDECK_API_KEY"]
APP_ID = os.environ["APIDECK_APP_ID"]
CONSUMER_ID = os.environ["APIDECK_CONSUMER_ID"]
COLLECTION_ID = os.environ["APIDECK_ISSUE_TRACKING_COLLECTION_ID"]
SERVICE_ID = "github"


def fetch_all_users() -> list[dict]:
    """Return every user in the collection by traversing cursor-based pagination."""
    client = Apideck(
        api_key=API_KEY,
        app_id=APP_ID,
        consumer_id=CONSUMER_ID,
    )

    users: list[dict] = []
    page = client.issue_tracking.collection_users.list(
        collection_id=COLLECTION_ID,
        service_id=SERVICE_ID,
    )

    def _val(v):
        """Convert SDK Unset sentinel to None for JSON serialisation."""
        return None if isinstance(v, Unset) else v

    while page is not None:
        if page.get_collection_users_response and page.get_collection_users_response.data:
            for user in page.get_collection_users_response.data:
                users.append(
                    {
                        "id": str(user.id) if (user.id is not None and not isinstance(user.id, Unset)) else "",
                        "name": _val(user.name),
                        "first_name": _val(user.first_name),
                        "last_name": _val(user.last_name),
                        "email": _val(user.email),
                    }
                )
        page = page.next()

    return users


def main() -> None:
    logger.info("Starting Apideck Issue Tracking users export for collection '%s'", COLLECTION_ID)

    users = fetch_all_users()

    artifact = {
        "collection_id": COLLECTION_ID,
        "service_id": SERVICE_ID,
        "users": users,
    }

    output_path = os.path.join(os.path.dirname(__file__), "users.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    logger.info("User count: %d", len(users))
    logger.info("Artifact written to %s", output_path)


if __name__ == "__main__":
    main()
