from django import forms
from .models import WhiskSettings

class WhiskSettingsForm(forms.ModelForm):
    class Meta:
        model = WhiskSettings
        fields = ['auth_token', 'project_id']
        widgets = {
            'auth_token': forms.TextInput(attrs={
                'style': 'width: 100%; padding: 1rem; border: 1px solid #dddfe2; border-radius: 6px; font-size: 1rem; box-sizing: border-box; transition: border-color 0.3s, box-shadow 0.3s;',
                'placeholder': 'Enter your Whisk API authentication token',
                'required': True,
                'onfocus': 'this.style.borderColor="#1877f2"; this.style.boxShadow="0 0 0 2px rgba(24, 119, 242, 0.2)";',
                'onblur': 'this.style.borderColor="#dddfe2"; this.style.boxShadow="none";'
            }),
            'project_id': forms.TextInput(attrs={
                'style': 'width: 100%; padding: 1rem; border: 1px solid #dddfe2; border-radius: 6px; font-size: 1rem; box-sizing: border-box; transition: border-color 0.3s, box-shadow 0.3s;',
                'placeholder': 'Enter your default project ID',
                'required': True,
                'onfocus': 'this.style.borderColor="#1877f2"; this.style.boxShadow="0 0 0 2px rgba(24, 119, 242, 0.2)";',
                'onblur': 'this.style.borderColor="#dddfe2"; this.style.boxShadow="none";'
            })
        }
        labels = {
            'auth_token': 'Authentication Token',
            'project_id': 'Project ID'
        }