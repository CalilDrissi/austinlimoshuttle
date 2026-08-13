"""
Account forms.

Django's own `PasswordResetForm` is used everywhere, with one deliberate
override -- see below.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()


class MigrationPasswordResetForm(PasswordResetForm):
    """
    A reset form that also serves accounts with no usable password.

    Django's `PasswordResetForm.get_users()` filters on `has_usable_password()`.
    That default is sound in general -- it stops a reset email being sent to an
    account that authenticates some other way, such as SSO-only users.

    It is exactly wrong here. All 1,251 migrated customers have an unusable
    password *by design*: the legacy passwords were plaintext and were discarded
    rather than carried across. Under the stock form none of them could ever
    request a reset, and every one would be permanently locked out of an account
    holding their booking history.

    Nothing is weakened by this. The token still goes only to the registered
    address, is single-use, and expires. The one requirement Django enforces and
    we keep is that the account is active.
    """

    def get_users(self, email):
        email_field = User.get_email_field_name()
        candidates = User._default_manager.filter(
            **{f"{email_field}__iexact": email, "is_active": True},
        )
        # No has_usable_password() filter -- that is the whole point.
        return (u for u in candidates if getattr(u, email_field))
