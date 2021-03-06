from datetime import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User

from .models import Invitations


ALLOWED_SIGNUP_DOMAINS = [
    'getpocket.com', 'mozilla.com', 'mozillafoundation.org'
]


def invitations_only(sender, **kwargs):
    sociallogin = kwargs['sociallogin']
    email = sociallogin.account.extra_data['email']

    # Mozilla domain FXA's should always be allowed
    domain_part = email.split('@')[1]
    for allowed_domain in ALLOWED_SIGNUP_DOMAINS:
        if domain_part == allowed_domain:
            return True

    # Explicit invitations for an email address can get in
    try:
        active_invitation = Invitations.objects.get(email=email, active=True)
        if not active_invitation.date_redeemed:
            active_invitation.date_redeemed = datetime.now()
            active_invitation.save()
        return True

    except Invitations.DoesNotExist:
        # If we're not doing token-based invites; reject immediately
        if not settings.ALPHA_INVITE_TOKEN:
            raise PermissionDenied

        # Token inviations are subject to max accounts limit
        active_accounts_count = User.objects.count()
        if active_accounts_count >= settings.MAX_ACTIVE_ACCOUNTS:
            raise PermissionDenied("There are too many active accounts on "
                                   "Relay. Please try again later.")

        # Must have visited the invitation link which put the token in their
        # session
        if 'alpha_token' not in kwargs['request'].session:
            raise PermissionDenied(
                "You must visit the invitation link in your invite email "
                "before signing up for Relay.")

        # Check the token in their session matches the setting
        session_token = kwargs['request'].session['alpha_token']
        if (session_token == settings.ALPHA_INVITE_TOKEN):
            Invitations.objects.create(
                email=email, active=True, date_redeemed=datetime.now()
            )
            del kwargs['request'].session['alpha_token']
            return True

    # Deny-by-default in case the logic above missed anything
    raise PermissionDenied
