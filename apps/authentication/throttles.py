from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = 'login'
    THROTTLE_RATES = {'login': '10/min'}

    def get_rate(self):
        default_rates = getattr(settings, 'REST_FRAMEWORK', {}).get('DEFAULT_THROTTLE_RATES', {})
        rate = default_rates.get(self.scope)
        if rate is not None:
            return rate
        return self.THROTTLE_RATES.get(self.scope)

    def get_cache_key(self, request, view):
        email = None
        if hasattr(request, 'data'):
            email = request.data.get('email')
        if not email and hasattr(request, 'POST'):
            email = request.POST.get('email')
        if email:
            return f'login-email:{email.lower()}'
        return self.get_ident(request)
