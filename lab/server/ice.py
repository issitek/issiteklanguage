import base64
import hashlib
import hmac
import os
import time

TTL_DEFAULT = 300  # 5 minutos, igual que la política prevista para el MVP


def _secret() -> bytes:
    return os.environ["TURN_SHARED_SECRET"].encode()


def turn_hmac_credential(username_prefix: str, ttl: int = TTL_DEFAULT) -> dict:
    """Cuaja credencial TURN REST/HMAC de vida corta.

    Mismo patrón que mxerp/app/telephony/webrtc_ice.py:
    username = "<unix_expira>_<nombre>", credential = base64(HMAC_SHA1(secret, username)).
    """
    expiry = int(time.time()) + ttl
    username = f"{expiry}_{username_prefix}"
    digest = hmac.new(_secret(), username.encode(), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode()
    return {"username": username, "credential": credential, "ttl": ttl}


def ice_servers(host: str = "127.0.0.1", ttl: int = TTL_DEFAULT) -> list:
    """iceServers listos para RTCPeerConnection en el cliente."""
    cred = turn_hmac_credential("talkdrill", ttl)
    return [
        {"urls": ["stun:127.0.0.1:3478"]},
        {
            "urls": [
                "turn:127.0.0.1:3478?transport=udp",
                "turn:127.0.0.1:3478?transport=tcp",
            ],
            "username": cred["username"],
            "credential": cred["credential"],
        },
    ]
