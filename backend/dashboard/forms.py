"""Dashboard forms."""

from django import forms

from notifications.models import EmailSettings
from payments.models import PaymentSettings, PayPalSettings


class BootstrapFormMixin:
    """
    Apply Bootstrap's form classes to every widget.

    Done here rather than in the templates so a new field is styled the moment
    it is added, and so the markup stays declarative -- a template that has to
    remember `class="form-control"` on each field will eventually forget one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{existing} {css}".strip()


class PaymentSettingsForm(BootstrapFormMixin, forms.ModelForm):
    """
    Stripe credentials.

    The two secret fields are write-only: they render empty every time and an
    empty submission means "leave the stored value alone". A form that echoed
    the secret back would put a live charge-and-refund credential into the HTML
    of a page, into the browser cache, and into anyone's screen recording.
    """

    secret_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "off", "placeholder": "sk_live_… or sk_test_…"},
        ),
        help_text="Leave blank to keep the current key. Encrypted at rest.",
    )
    webhook_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "off", "placeholder": "whsec_…"},
        ),
        help_text="From the Stripe webhook endpoint. Leave blank to keep the current value.",
    )

    class Meta:
        model = PaymentSettings
        fields = ["mode", "is_enabled", "publishable_key", "statement_descriptor"]
        widgets = {
            "publishable_key": forms.TextInput(
                attrs={"placeholder": "pk_live_… or pk_test_…", "size": 50},
            ),
            "statement_descriptor": forms.TextInput(
                attrs={"placeholder": "AUSTIN LIMO", "maxlength": 22},
            ),
        }

    def clean_publishable_key(self):
        value = (self.cleaned_data.get("publishable_key") or "").strip()
        if value and not value.startswith(("pk_test_", "pk_live_")):
            raise forms.ValidationError(
                "A publishable key starts with pk_test_ or pk_live_. "
                "If this starts with sk_, it is a secret key and must not go here."
            )
        return value

    def clean_secret_key(self):
        value = (self.cleaned_data.get("secret_key") or "").strip()
        if value and not value.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
            raise forms.ValidationError(
                "A secret key starts with sk_ (or rk_ for a restricted key)."
            )
        return value

    def clean_webhook_secret(self):
        value = (self.cleaned_data.get("webhook_secret") or "").strip()
        if value and not value.startswith("whsec_"):
            raise forms.ValidationError("A webhook signing secret starts with whsec_.")
        return value

    def clean(self):
        """
        Cross-check the keys against the selected mode.

        Live mode with test keys is a silent failure: the checkout appears to
        work and no money moves. Test keys in live mode is the reverse and
        charges real cards during testing.
        """
        cleaned = super().clean()
        mode = cleaned.get("mode")
        enabled = cleaned.get("is_enabled")

        secret = cleaned.get("secret_key") or (self.instance.secret_key or "")
        publishable = cleaned.get("publishable_key") or ""

        if mode == PaymentSettings.Mode.LIVE:
            if secret and not secret.startswith(("sk_live_", "rk_live_")):
                self.add_error(
                    "mode",
                    "Live mode is selected but the secret key is a test key. "
                    "Payments would silently never reach a real card.",
                )
            if publishable and not publishable.startswith("pk_live_"):
                self.add_error("publishable_key", "Live mode needs a pk_live_ key.")
        elif mode == PaymentSettings.Mode.TEST:
            if secret and secret.startswith(("sk_live_", "rk_live_")):
                self.add_error(
                    "mode",
                    "Test mode is selected but the secret key is a LIVE key. "
                    "Testing would charge real cards.",
                )
            if publishable and publishable.startswith("pk_live_"):
                self.add_error("publishable_key", "Test mode needs a pk_test_ key.")

        if enabled:
            if not publishable:
                self.add_error(
                    "is_enabled", "A publishable key is required before enabling payments.",
                )
            if not secret:
                self.add_error(
                    "is_enabled", "A secret key is required before enabling payments.",
                )

        return cleaned

    def save(self, commit=True):
        """Only overwrite a secret when a replacement was actually supplied."""
        instance = super().save(commit=False)

        if secret := self.cleaned_data.get("secret_key"):
            instance.secret_key = secret
        if webhook := self.cleaned_data.get("webhook_secret"):
            instance.webhook_secret = webhook

        if commit:
            instance.save()
        return instance


class EmailSettingsForm(BootstrapFormMixin, forms.ModelForm):
    """
    SMTP credentials.

    The password is write-only, for the same reason as the Stripe secret: a
    mailbox password sends mail as the business, and a leaked one is a phishing
    platform with the client's own domain behind it.
    """

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "placeholder": "mailbox password"},
        ),
        help_text="Leave blank to keep the current password. Encrypted at rest.",
    )

    class Meta:
        model = EmailSettings
        fields = [
            "is_enabled", "host", "port", "security", "username",
            "from_name", "from_email", "reply_to", "ops_notification_email",
            "timeout_seconds",
        ]
        widgets = {
            "host": forms.TextInput(attrs={"placeholder": "mail.austinlimoshuttle.com",
                                           "size": 40}),
            "from_email": forms.EmailInput(
                attrs={"placeholder": "bookings@austinlimoshuttle.com", "size": 40}),
            "reply_to": forms.EmailInput(attrs={"size": 40}),
            "ops_notification_email": forms.EmailInput(attrs={"size": 40}),
        }

    def clean(self):
        cleaned = super().clean()
        security = cleaned.get("security")
        port = cleaned.get("port")

        # Not fatal -- hosts vary -- but the mismatch is worth surfacing, because
        # the symptom is a connection that hangs rather than an error.
        if security == EmailSettings.Security.SSL and port == 587:  # noqa: PLR2004
            self.add_error(
                "port",
                "Port 587 is normally STARTTLS, not SSL/TLS. SSL usually uses 465.",
            )
        if security == EmailSettings.Security.TLS and port == 465:  # noqa: PLR2004
            self.add_error(
                "port",
                "Port 465 is normally SSL/TLS, not STARTTLS. STARTTLS usually uses 587.",
            )

        if cleaned.get("is_enabled"):
            if not cleaned.get("host"):
                self.add_error("is_enabled", "A host is required before enabling email.")
            if not cleaned.get("from_email"):
                self.add_error(
                    "is_enabled", "A from address is required before enabling email.",
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if password := self.cleaned_data.get("password"):
            instance.password = password
        if commit:
            instance.save()
        return instance


class PayPalSettingsForm(BootstrapFormMixin, forms.ModelForm):
    """
    PayPal REST credentials.

    The client secret is write-only, as with the Stripe key and the SMTP
    password: a form that echoes a secret back puts it into page HTML, the
    browser cache, and any screen recording.

    Unlike Stripe, PayPal credentials carry no sandbox/live prefix, so the mode
    cannot be cross-checked against the strings. The "Test connection" action on
    the page covers that instead.
    """

    client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "off", "placeholder": "PayPal client secret"},
        ),
        help_text="Leave blank to keep the current secret. Encrypted at rest.",
    )

    class Meta:
        model = PayPalSettings
        fields = ["mode", "is_enabled", "client_id", "webhook_id", "brand_name"]
        widgets = {
            "client_id": forms.TextInput(attrs={"placeholder": "AY…", "size": 50}),
            "webhook_id": forms.TextInput(attrs={"placeholder": "8SW…"}),
            "brand_name": forms.TextInput(attrs={"placeholder": "Austin Limo Shuttle"}),
        }

    def clean_client_id(self):
        value = (self.cleaned_data.get("client_id") or "").strip()
        if value and value.startswith(("sk_", "pk_", "whsec_")):
            raise forms.ValidationError(
                "That looks like a Stripe key. PayPal credentials belong on this "
                "page; Stripe keys belong on the Payments page."
            )
        return value

    def clean_client_secret(self):
        return (self.cleaned_data.get("client_secret") or "").strip()

    def clean(self):
        cleaned = super().clean()
        secret = cleaned.get("client_secret") or (self.instance.client_secret or "")

        if cleaned.get("is_enabled"):
            if not cleaned.get("client_id"):
                self.add_error(
                    "is_enabled", "A client ID is required before enabling PayPal.",
                )
            if not secret:
                self.add_error(
                    "is_enabled", "A client secret is required before enabling PayPal.",
                )
            if not cleaned.get("webhook_id"):
                # Not fatal: a webhook id is only needed once payments are taken,
                # and enabling without one is a legitimate intermediate state.
                self.add_error(
                    "webhook_id",
                    "A webhook ID is needed to verify PayPal events. Add it before "
                    "taking live payments.",
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if secret := self.cleaned_data.get("client_secret"):
            instance.client_secret = secret
        if commit:
            instance.save()
        return instance
