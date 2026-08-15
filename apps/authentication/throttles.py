from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = 'login'

    def get_cache_key(self, request, view):
        email = None
        if hasattr(request, 'data'):
            email = request.data.get('email')
        if not email and hasattr(request, 'POST'):
            email = request.POST.get('email')
        if email:
            return f'login-email:{email.lower()}'
        return self.get_ident(request)
