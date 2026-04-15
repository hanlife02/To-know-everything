from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from app.sources.pku_reagent.models import PkuReagentSession
from app.storage.json_store import JsonStore


class PkuReagentAuthError(RuntimeError):
    pass


class PkuReagentInteractiveAuthRequired(PkuReagentAuthError):
    pass


class PkuReagentSessionExpiredError(PkuReagentAuthError):
    pass


class PkuReagentAuthenticator(Protocol):
    def authenticate(self, *, force_refresh: bool = False) -> PkuReagentSession | None:
        ...


@dataclass(slots=True)
class StaticPkuReagentAuthenticator:
    username: str
    token: str
    cookie_header: str

    def authenticate(self, *, force_refresh: bool = False) -> PkuReagentSession | None:
        del force_refresh
        if not (self.username and self.token and self.cookie_header):
            return None
        return PkuReagentSession(
            username=self.username,
            token=self.token,
            cookie_header=self.cookie_header,
            acquired_at=datetime.now(UTC),
            source="static",
        )


@dataclass(slots=True)
class CachedPkuReagentAuthenticator:
    delegate: PkuReagentAuthenticator
    store_path: Path
    _store: JsonStore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._store = JsonStore(self.store_path)

    def authenticate(self, *, force_refresh: bool = False) -> PkuReagentSession | None:
        if not force_refresh:
            cached = self._load()
            if cached is not None:
                return cached
        session = self.delegate.authenticate(force_refresh=force_refresh)
        if session is not None:
            self._store.save(session.as_dict())
        return session

    def _load(self) -> PkuReagentSession | None:
        payload = self._store.load(default={})
        if not isinstance(payload, dict) or not payload:
            return None
        session = PkuReagentSession.from_dict(payload)
        if not (session.username and session.token and session.cookie_header):
            return None
        return session


@dataclass(slots=True)
class IaaaOauthPkuReagentAuthenticator:
    base_url: str
    username: str
    password: str
    captcha_code: str = ""
    sms_code: str = ""
    otp_code: str = ""
    iaaa_base_url: str = "https://iaaa.pku.edu.cn/iaaa"
    timeout_seconds: int = 30

    def authenticate(self, *, force_refresh: bool = False) -> PkuReagentSession | None:
        del force_refresh
        if not (self.username and self.password):
            return None
        cookie_jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(cookie_jar))
        self._bootstrap_auth_session(opener)
        public_key = self._get_public_key(opener)
        encrypted_password = _encrypt_password_with_public_key(public_key, self.password) if public_key else self.password
        oauth_token = self._login(opener, encrypted_password)
        nonce = _build_nonce()
        callback_params = self._consume_callback(opener, oauth_token=oauth_token, nonce=nonce)
        session = self._exchange_business_session(opener, oauth_token=oauth_token, nonce=nonce, callback_params=callback_params)
        return PkuReagentSession(
            username=session.username,
            token=session.token,
            cookie_header=_build_cookie_header(cookie_jar, self.base_url),
            acquired_at=datetime.now(UTC),
            source="iaaa_oauth",
        )

    def _bootstrap_auth_session(self, opener) -> None:
        request = Request(
            url=f"{self.base_url.rstrip('/')}/authredirect.aspx?urlfrom=shop",
            headers={"User-Agent": "to-know-everything/0.1"},
            method="GET",
        )
        with opener.open(request, timeout=self.timeout_seconds):
            return None

    def _get_public_key(self, opener) -> str:
        payload = self._open_json(opener, f"{self.iaaa_base_url.rstrip('/')}/getPublicKey.do")
        return str(payload.get("key") or "")

    def _login(self, opener, encrypted_password: str) -> str:
        payload = self._open_json(
            opener,
            f"{self.iaaa_base_url.rstrip('/')}/oauthlogin.do",
            data={
                "appid": "reagent",
                "userName": self.username,
                "password": encrypted_password,
                "randCode": self.captcha_code,
                "smsCode": self.sms_code,
                "otpCode": self.otp_code,
                "remTrustChk": "false",
                "redirUrl": "http://reagent.pku.edu.cn/callback.aspx",
            },
        )
        if payload.get("success") is True:
            token = str(payload.get("token") or "")
            if token:
                return token
        errors = payload.get("errors") if isinstance(payload.get("errors"), dict) else {}
        message = str(errors.get("msg") or payload.get("message") or "PKU IAAA login failed")
        if any(keyword in message for keyword in ("验证码", "短信验证码", "手机令牌")):
            raise PkuReagentInteractiveAuthRequired(message)
        raise PkuReagentAuthError(message)

    def _consume_callback(self, opener, *, oauth_token: str, nonce: str) -> dict[str, str]:
        request = Request(
            url=f"{self.base_url.rstrip('/')}/callback.aspx?token={oauth_token}&_rand={nonce}",
            headers={"User-Agent": "to-know-everything/0.1", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            method="GET",
        )
        with opener.open(request, timeout=self.timeout_seconds) as response:
            final_url = response.geturl()
            charset = response.headers.get_content_charset() or "utf-8"
            response_text = response.read().decode(charset, errors="replace")
        if "token无效" in response_text:
            raise PkuReagentAuthError(response_text.strip())
        route_params = _extract_route_query_params(final_url)
        if route_params:
            return route_params
        return {"token": oauth_token, "_rand": nonce}

    def _exchange_business_session(
        self,
        opener,
        *,
        oauth_token: str,
        nonce: str,
        callback_params: dict[str, str],
    ) -> PkuReagentSession:
        exchange_payload = {
            "query": "vueoauth",
            "system": "shop",
            "from": "PC",
            **callback_params,
        }
        if "token" not in exchange_payload and oauth_token:
            exchange_payload["token"] = oauth_token
        if "_rand" not in exchange_payload and nonce:
            exchange_payload["_rand"] = nonce
        payload = self._open_json(
            opener,
            f"{self.base_url.rstrip('/')}/Jpost",
            data=exchange_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows:
            raise PkuReagentAuthError(payload.get("message", "failed to exchange PKU reagent oauth session"))
        row = rows[0]
        if not isinstance(row, dict):
            raise PkuReagentAuthError("PKU reagent oauth exchange returned invalid user payload")
        username = str(row.get("username") or "")
        token = str(row.get("token") or "")
        if not (username and token):
            raise PkuReagentAuthError("PKU reagent oauth exchange did not return username/token")
        return PkuReagentSession(username=username, token=token, cookie_header="")

    def _open_json(
        self,
        opener,
        url: str,
        *,
        data: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        text = self._open_text(opener, url, data=data, headers=headers)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise PkuReagentAuthError("PKU reagent auth returned non-object JSON")
        return payload

    def _open_text(
        self,
        opener,
        url: str,
        *,
        data: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        request_headers = {"User-Agent": "to-know-everything/0.1", "Accept": "application/json, text/plain, */*"}
        if headers:
            request_headers.update(headers)
        body = urlencode(data).encode("utf-8") if data is not None else None
        request = Request(url=url, data=body, headers=request_headers, method="POST" if body is not None else "GET")
        with opener.open(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")


def _build_nonce() -> str:
    return secrets.token_hex(8)


def _build_cookie_header(cookie_jar: CookieJar, base_url: str) -> str:
    host = (urlparse(base_url).hostname or "").lower()
    parts: list[str] = []
    for cookie in cookie_jar:
        domain = cookie.domain.lstrip(".").lower()
        if host == domain or host.endswith(f".{domain}"):
            parts.append(f"{cookie.name}={cookie.value}")
    return "; ".join(parts)


def _extract_route_query_params(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    query = parsed.query
    if not query and "?" in parsed.fragment:
        query = parsed.fragment.split("?", 1)[1]
    return dict(parse_qsl(query, keep_blank_values=True))


def _encrypt_password_with_public_key(public_key_pem: str, password: str) -> str:
    modulus, exponent = _parse_rsa_public_key(public_key_pem)
    key_size = (modulus.bit_length() + 7) // 8
    message = password.encode("utf-8")
    if len(message) > key_size - 11:
        raise PkuReagentAuthError("PKU IAAA password is too long for RSA encryption")
    padding_length = key_size - len(message) - 3
    padding = bytearray()
    while len(padding) < padding_length:
        chunk = secrets.token_bytes(padding_length - len(padding))
        padding.extend(byte for byte in chunk if byte != 0)
    encoded = b"\x00\x02" + bytes(padding[:padding_length]) + b"\x00" + message
    encrypted = pow(int.from_bytes(encoded, "big"), exponent, modulus)
    return base64.b64encode(encrypted.to_bytes(key_size, "big")).decode("ascii")


def _parse_rsa_public_key(public_key_pem: str) -> tuple[int, int]:
    der = _pem_to_der(public_key_pem)
    _, spki_content, _ = _read_tlv(der, 0)
    _, _, offset = _read_tlv(spki_content, 0)
    bit_string_tag, bit_string_content, _ = _read_tlv(spki_content, offset)
    if bit_string_tag != 0x03 or not bit_string_content:
        raise PkuReagentAuthError("PKU IAAA public key is not a valid RSA bit string")
    if bit_string_content[0] != 0:
        raise PkuReagentAuthError("PKU IAAA public key uses unsupported bit padding")
    _, rsa_content, _ = _read_tlv(bit_string_content[1:], 0)
    _, modulus_content, offset = _read_tlv(rsa_content, 0)
    _, exponent_content, _ = _read_tlv(rsa_content, offset)
    return int.from_bytes(modulus_content, "big"), int.from_bytes(exponent_content, "big")


def _pem_to_der(public_key_pem: str) -> bytes:
    lines = [
        line.strip()
        for line in public_key_pem.strip().splitlines()
        if line.strip() and not line.startswith("-----BEGIN") and not line.startswith("-----END")
    ]
    if not lines:
        raise PkuReagentAuthError("PKU IAAA public key is empty")
    return base64.b64decode("".join(lines))


def _read_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    if offset >= len(data):
        raise PkuReagentAuthError("PKU IAAA public key is truncated")
    tag = data[offset]
    length, length_offset = _read_length(data, offset + 1)
    value_offset = length_offset
    end = value_offset + length
    if end > len(data):
        raise PkuReagentAuthError("PKU IAAA public key length is invalid")
    value = data[value_offset:end]
    if tag == 0x02 and value and value[0] == 0:
        value = value[1:]
    return tag, value, end


def _read_length(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise PkuReagentAuthError("PKU IAAA public key length is truncated")
    first = data[offset]
    if first < 0x80:
        return first, offset + 1
    byte_count = first & 0x7F
    if byte_count == 0 or offset + 1 + byte_count > len(data):
        raise PkuReagentAuthError("PKU IAAA public key uses unsupported length encoding")
    length = int.from_bytes(data[offset + 1 : offset + 1 + byte_count], "big")
    return length, offset + 1 + byte_count
