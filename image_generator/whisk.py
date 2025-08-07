import requests
import json
from django.conf import settings

def get_authorization_token():
    url = "https://labs.google/fx/api/auth/session"
    headers = {"Cookie": settings.WHISK_COOKIE}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ValueError("No access token in response")
        return token
    except requests.Timeout:
        raise Exception("Authorization request timed out")
    except requests.RequestException as e:
        raise Exception(f"Authorization request failed: {str(e)}")
    except (json.JSONDecodeError, ValueError) as e:
        raise Exception(f"Invalid authorization response: {str(e)}")

def get_new_project_id(title):
    url = "https://labs.google/fx/api/trpc/media.createOrUpdateWorkflow"
    headers = {
        "Cookie": settings.WHISK_COOKIE,
        "Content-Type": "application/json",
    }
    data = {
        "json": {
            "clientContext": {
                "tool": "BACKBONE",
                "sessionId": ";1748266079775"
            },
            "workflowMetadata": {"workflowName": title}
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        try:
            data = response.json()
            return data.get("result", {}).get("data", {}).get("json", {}).get("result", {}).get("workflowId")
        except json.JSONDecodeError:
            return None
    return None

def generate_image(prompt, auth_token, project_id):
    url = "https://aisandbox-pa.googleapis.com/v1/whisk:generateImage"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    data = {
        "clientContext": {
            "workflowId": project_id,
            "tool": "BACKBONE",
            "sessionId": ";1748281496093"
        },
        "imageModelSettings": {
            "imageModel": "IMAGEN_3_5",
            "aspectRatio": "IMAGE_ASPECT_RATIO_LANDSCAPE",
        },
        "seed": 0,
        "prompt": prompt,
        "mediaCategory": "MEDIA_CATEGORY_BOARD"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            return None
    return None
