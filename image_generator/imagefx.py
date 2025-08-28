import requests
from .models import ImageFXSettings

def generate_image_api(auth_token, prompt, count=4, aspect_ratio="IMAGE_ASPECT_RATIO_LANDSCAPE", model="IMAGEN_3_5", return_response=False):
    """Generate images using the ImageFX API"""
    url = "https://aisandbox-pa.googleapis.com/v1:runImageFx"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    data = {
        "userInput": {
            "candidatesCount": count,
            "prompts": [prompt],
            "seed": 0
        },
        "aspectRatio": aspect_ratio,
        "modelInput": {
            "modelNameType": model
        },
        "clientContext": {
            "sessionId": ";1740658431200", 
            "tool": "IMAGE_FX"
        }
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    
    if return_response:
        return response
    
    if not response.ok:
        print("Error:", response.status_code, response.text)
        return None
    
    result = response.json()
    if "imagePanels" not in result:
        return None
    
    return result["imagePanels"][0]["generatedImages"]

def generate_image(prompt):
    """Generate image using ImageFX API with settings from database"""
    imagefx_settings = ImageFXSettings.get_settings()
    if not imagefx_settings.auth_token:
        return None
    
    # Use the new API function
    generated_images = generate_image_api(imagefx_settings.auth_token, prompt)
    if not generated_images:
        return None
    
    # Format response to match expected structure
    return {
        "imagePanels": [{
            "generatedImages": generated_images
        }]
    }