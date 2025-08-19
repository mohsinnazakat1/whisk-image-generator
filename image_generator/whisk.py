import requests
import json
from django.conf import settings
from .models import WhiskSettings

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

def generate_image(prompt):
    url = "https://aisandbox-pa.googleapis.com/v1/whisk:generateImage"
    whisk_settings = WhiskSettings.get_settings()
    
    headers = {
        "Authorization": f"Bearer {whisk_settings.auth_token}",
        "Content-Type": "application/json",
    }
    data = {
        "clientContext": {
            "workflowId": whisk_settings.project_id,
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
