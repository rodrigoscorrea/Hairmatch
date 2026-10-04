import hashlib

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class EmailRateThrottle(SimpleRateThrottle):
    """
    Counts the requests that aim at one e-mail, whatever their IP: it stops a bot from spamming one
    inbox through the sender's SES reputation or from guessing codes with many addresses. Each subclass
    has its own `scope`, so the counters of two routes never share a key.
    """

    def get_cache_key(self, request, view):
        data = request.data
        if not hasattr(data, 'get') or data.get('google_signup_token'):
            return None  # a Google sign-up takes its e-mail from the token, not from the body
        email = data.get('email')
        if not isinstance(email, str) or not email.strip():
            return None  # the view answers 400
        # Hashed so the address is not written in clear text to the cache table.
        ident = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class RegisterEmailThrottle(EmailRateThrottle):
    scope = 'register_email'
    rate = '3/hour'


class ConfirmEmailThrottle(EmailRateThrottle):
    scope = 'confirm_email'
    rate = '10/hour'


class ResendCodeEmailThrottle(EmailRateThrottle):
    scope = 'resend_code_email'
    rate = '3/hour'


class ConfirmIpThrottle(AnonRateThrottle):
    scope = 'confirm_ip'
    rate = '10/min'


class ResendCodeIpThrottle(AnonRateThrottle):
    scope = 'resend_code_ip'
    rate = '10/hour'
