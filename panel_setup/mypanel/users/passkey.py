import json
import logging
from django.utils import timezone
from django.conf import settings
from users.models import UserPasskey
from file_manager.models import UserSettings

try:
    import webauthn
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        UserVerificationRequirement,
        AuthenticatorSelectionCriteria,
        ResidentKeyRequirement,
    )
except ImportError:
    webauthn = None

logger = logging.getLogger(__name__)


def get_rp_id(request):
    """
    Extract RP ID (domain / hostname without port).
    """
    try:
        host = request.get_host().split(':')[0]
        if host:
            return host
    except Exception:
        pass
    return "localhost"


def get_origin(request):
    """
    Extract origin (scheme + host:port).
    Prioritizes the browser's actual Origin and Referer headers.
    """
    origin = request.META.get('HTTP_ORIGIN') or request.headers.get('Origin')
    if origin:
        return str(origin).rstrip('/')

    referer = request.META.get('HTTP_REFERER') or request.headers.get('Referer')
    if referer:
        try:
            from urllib.parse import urlparse
            p = urlparse(referer)
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}"
        except Exception:
            pass

    scheme = "https" if (
        request.is_secure() or
        request.headers.get("X-Forwarded-Proto") == "https" or
        request.META.get("HTTP_X_FORWARDED_PROTO") == "https" or
        request.META.get("HTTPS") == "on" or
        str(request.get_port()) in ('2087', '443') or
        (not request.get_host().startswith("127.0.0.1") and not request.get_host().startswith("localhost"))
    ) else "http"
    return f"{scheme}://{request.get_host()}"


def get_rp_name():
    """
    Get panel brand name.
    """
    from users.context_processors import branding
    try:
        brand = branding(None).get('branding', {})
        name = brand.get('brand_title')
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    return "OLSPanel"



def _mark_modified(session_obj):
    if hasattr(session_obj, 'modified'):
        session_obj.modified = True


def _cred_id_to_bytes(cred_id_str):
    if not cred_id_str:
        return b""
    try:
        return bytes.fromhex(cred_id_str)
    except Exception:
        pass
    try:
        return webauthn.helpers.base64url_to_bytes(cred_id_str)
    except Exception:
        pass
    return cred_id_str.encode('utf-8')


def generate_reg_options(request, user):
    """
    Generate WebAuthn registration options for a user.
    """
    if not webauthn:
        raise RuntimeError("webauthn library is not installed.")

    rp_id = get_rp_id(request)
    rp_name = get_rp_name()

    # Exclude existing credentials
    existing_passkeys = UserPasskey.objects.filter(user=user)
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=_cred_id_to_bytes(pk.credential_id))
        for pk in existing_passkeys
        if pk.credential_id
    ]

    options = webauthn.generate_registration_options(
        rp_name=rp_name,
        rp_id=rp_id,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.username,
        user_display_name=user.get_full_name() or user.username,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
    )

    # Save challenge to session
    challenge_b64 = webauthn.helpers.bytes_to_base64url(options.challenge)
    if hasattr(request, 'admin_session') and request.path.startswith('/whm/'):
        request.admin_session['webauthn_reg_challenge'] = challenge_b64
        _mark_modified(request.admin_session)
    else:
        request.session['webauthn_reg_challenge'] = challenge_b64
        _mark_modified(request.session)

    return json.loads(webauthn.options_to_json(options))


def verify_reg_response(request, user, credential_data, passkey_name="Passkey"):
    """
    Verify WebAuthn registration response and save UserPasskey.
    """
    if not webauthn:
        raise RuntimeError("webauthn library is not installed.")

    if hasattr(request, 'admin_session') and request.path.startswith('/whm/'):
        challenge_b64 = request.admin_session.get('webauthn_reg_challenge')
    else:
        challenge_b64 = request.session.get('webauthn_reg_challenge')

    if not challenge_b64:
        raise ValueError("Registration challenge not found in session.")

    expected_challenge = webauthn.helpers.base64url_to_bytes(challenge_b64)
    expected_rp_id = get_rp_id(request)
    expected_origin = get_origin(request)

    if isinstance(credential_data, str):
        credential_data = json.loads(credential_data)

    verification = webauthn.verify_registration_response(
        credential=credential_data,
        expected_challenge=expected_challenge,
        expected_rp_id=expected_rp_id,
        expected_origin=expected_origin,
        require_user_verification=False,
    )

    # Hex-encode credential ID and public key for clean storage
    cred_id_hex = verification.credential_id.hex()
    pub_key_hex = verification.credential_public_key.hex()
    aaguid_str = str(verification.aaguid) if verification.aaguid else None

    transports_list = credential_data.get('response', {}).get('transports', [])
    transports_str = ",".join(transports_list) if isinstance(transports_list, list) else ""

    passkey, created = UserPasskey.objects.update_or_create(
        credential_id=cred_id_hex,
        defaults={
            'user': user,
            'name': passkey_name or "Passkey",
            'public_key': pub_key_hex,
            'sign_count': verification.sign_count,
            'aaguid': aaguid_str,
            'transports': transports_str,
            'last_used_at': timezone.now(),
        }
    )

    # Clear challenge

    if hasattr(request, 'admin_session') and request.path.startswith('/whm/'):
        request.admin_session.pop('webauthn_reg_challenge', None)
        _mark_modified(request.admin_session)
    else:
        request.session.pop('webauthn_reg_challenge', None)
        _mark_modified(request.session)

    return passkey


def generate_auth_options(request, user):
    """
    Generate WebAuthn authentication options for user login challenge.
    """
    if not webauthn:
        raise RuntimeError("webauthn library is not installed.")

    rp_id = get_rp_id(request)
    existing_passkeys = UserPasskey.objects.filter(user=user)

    if not existing_passkeys.exists():
        return None

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=_cred_id_to_bytes(pk.credential_id))
        for pk in existing_passkeys
        if pk.credential_id
    ]

    options = webauthn.generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    challenge_b64 = webauthn.helpers.bytes_to_base64url(options.challenge)
    request.session['webauthn_auth_challenge'] = challenge_b64
    request.session['webauthn_auth_user_id'] = user.id
    _mark_modified(request.session)

    return json.loads(webauthn.options_to_json(options))


def verify_auth_response(request, user, credential_data):
    """
    Verify WebAuthn authentication response against stored UserPasskey.
    """
    if not webauthn:
        raise RuntimeError("webauthn library is not installed.")

    challenge_b64 = request.session.get('webauthn_auth_challenge')
    if not challenge_b64:
        raise ValueError("Authentication challenge not found in session.")

    expected_challenge = webauthn.helpers.base64url_to_bytes(challenge_b64)
    expected_rp_id = get_rp_id(request)
    expected_origin = get_origin(request)

    if isinstance(credential_data, str):
        credential_data = json.loads(credential_data)

    raw_cred_id = credential_data.get('id', '')
    try:
        cred_id_bytes = webauthn.helpers.base64url_to_bytes(raw_cred_id)
        cred_id_hex = cred_id_bytes.hex()
    except Exception:
        cred_id_hex = raw_cred_id

    try:
        passkey = UserPasskey.objects.get(user=user, credential_id=cred_id_hex)
    except UserPasskey.DoesNotExist:
        passkey = UserPasskey.objects.filter(user=user).first()
        if not passkey:
            raise ValueError("Registered passkey not found for this user.")

    verification = webauthn.verify_authentication_response(
        credential=credential_data,
        expected_challenge=expected_challenge,
        expected_rp_id=expected_rp_id,
        expected_origin=expected_origin,
        credential_public_key=bytes.fromhex(passkey.public_key),
        credential_current_sign_count=passkey.sign_count,
        require_user_verification=False,
    )

    # Update sign count and last used timestamp
    passkey.sign_count = verification.new_sign_count
    passkey.last_used_at = timezone.now()
    passkey.save()

    # Clear challenge
    request.session.pop('webauthn_auth_challenge', None)
    request.session.pop('webauthn_auth_user_id', None)
    _mark_modified(request.session)

    return True

