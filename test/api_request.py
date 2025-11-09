import requests

BASE_CUSTOM_SPACE_BACKEND_URL = "http://localhost:5000"

def get_todos(widget_id, token, accept_type="application/json"):
    """
    Send a GET request to retrieve a specific todo widget.

    Args:
        widget_id (str): The widget's unique ID
        token (str): Bearer token for authorization
        accept_type (str, optional): Accept header value. Defaults to "application/json".

    Returns:
        dict | str: Parsed JSON response or text if JSON decoding fails.
    """
    url = f"{BASE_CUSTOM_SPACE_BACKEND_URL}/api/widgets/todo/{widget_id}"
    
    headers = {
        "accept": accept_type,
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    
    try:
        return response.json()
    except ValueError:
        return response.text


# Example usage:
if __name__ == "__main__":
    widget_id = "690e35693447aa7994378d79"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIzOGUyM2FiMS1kNzNlLTQ2NjYtOTExYi0yNWNkZmRlZGMwY2UiLCJ1c2VybmFtZSI6InVzZXIxIiwiYXV0aE1ldGhvZElkIjoiMzBjMzI3ZDQtOTkxMC00NjI5LTgyYTktZWZjNGNmN2NhZDgwIiwidG9rZW5QdXJwb3NlIjoidXNlci1hdXRoIiwiaWF0IjoxNzYyNjYwNjc3LCJleHAiOjE3NjI2NjQyNzd9.EbG6y_bKk7wHMMyOejlesRTLeKMJqDVFVgvs-Il6Ag4"

    result = get_todos(widget_id, token)
    print(result)
