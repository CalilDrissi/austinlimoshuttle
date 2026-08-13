"""
Security headers not covered by Django's SecurityMiddleware.

Django 5.2 ships no Content-Security-Policy support, and `django-csp` is a whole
dependency for two response headers. This is deliberately small: it sets a
policy and nothing else.

The policy is written for the Django-served surfaces (admin and dashboard),
which use no inline scripts of their own. The Next.js frontend is served
separately and will need its own policy, including whatever Stripe Elements
requires when payments are wired up.
"""

from django.utils.deprecation import MiddlewareMixin

# Django's admin uses inline styles heavily, so 'unsafe-inline' is unavoidable
# for style-src. Scripts are deliberately not granted it.
CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data:",
    "font-src": "'self'",
    "connect-src": "'self'",
    "frame-ancestors": "'none'",
    "form-action": "'self'",
    "base-uri": "'self'",
    "object-src": "'none'",
}


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Adds Content-Security-Policy and Permissions-Policy to every response."""

    def process_response(self, request, response):
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = "; ".join(
                f"{directive} {value}" for directive, value in CSP_DIRECTIVES.items()
            )

        if "Permissions-Policy" not in response:
            # Nothing here needs a camera, microphone or the payment API.
            response["Permissions-Policy"] = (
                "geolocation=(), camera=(), microphone=(), payment=()"
            )

        return response
