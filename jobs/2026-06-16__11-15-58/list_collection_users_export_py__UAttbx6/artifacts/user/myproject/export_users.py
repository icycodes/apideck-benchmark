import os
import json
from apideck_unify import Apideck

def main():
    api_key = os.environ.get("APIDECK_API_KEY")
    app_id = os.environ.get("APIDECK_APP_ID")
    consumer_id = os.environ.get("APIDECK_CONSUMER_ID")
    collection_id = os.environ.get("APIDECK_ISSUE_TRACKING_COLLECTION_ID")

    apideck = Apideck(
        api_key=api_key,
        app_id=app_id,
        consumer_id=consumer_id
    )

    all_users = []
    
    response = apideck.issue_tracking.collection_users.list(
        collection_id=collection_id,
        service_id="github"
    )
    
    while response is not None:
        if hasattr(response, 'get_collection_users_response') and response.get_collection_users_response:
            data = response.get_collection_users_response.data
            if data:
                for user in data:
                    def get_val(val):
                        if val is None or type(val).__name__ == 'Unset':
                            return None
                        return val

                    user_dict = {
                        "id": get_val(getattr(user, "id", None)),
                        "name": get_val(getattr(user, "name", None)),
                        "first_name": get_val(getattr(user, "first_name", None)),
                        "last_name": get_val(getattr(user, "last_name", None)),
                        "email": get_val(getattr(user, "email", None))
                    }
                    all_users.append(user_dict)
        
        if callable(response.next):
            response = response.next()
        else:
            break

    output_data = {
        "collection_id": collection_id,
        "service_id": "github",
        "users": all_users
    }

    with open("/home/user/myproject/users.json", "w") as f:
        json.dump(output_data, f, indent=2)

    with open("/home/user/myproject/output.log", "w") as f:
        f.write(f"User count: {len(all_users)}\n")

if __name__ == "__main__":
    main()
