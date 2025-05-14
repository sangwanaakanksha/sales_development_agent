# ===== utils/template.py =====
from jinja2 import Template

# Example email template with placeholders
EMAIL_TEMPLATE = """
Subject: {{ subject }}

Hi {{ first_name }},

{{ intro_paragraph }}

Would you be open to a quick 15-minute call next week to discuss how {{ org_name }} can support {{ company_name }}'s goals?

Best regards,
{{ user_name }}
{{ org_name }}
"""

def render_email(context: dict) -> str:
    """
    Renders the email using Jinja2 templating
    """
    tmpl = Template(EMAIL_TEMPLATE)
    return tmpl.render(**context)