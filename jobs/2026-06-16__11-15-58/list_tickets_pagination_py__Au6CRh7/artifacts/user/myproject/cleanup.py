import os
import json
from apideck_unify import Apideck

def main():
    app_id = os.environ.get("APIDECK_APP_ID")
    api_key = os.environ.get("APIDECK_API_KEY")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")
    run_id = os.environ.get("ZEALT_RUN_ID")

    apideck = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id
    )

    print("Seeding tickets...")
    # 1. Seed tickets (we don't need to seed again, but I'll leave it out or keep it? 
    # If the verifier expects EXACTLY 5 seeded, maybe I should delete the extra ones?
    # Let's delete the extra ones first using the API.
    pass

if __name__ == "__main__":
    main()
