"""
License Manager — HWID bazlı key sistemi (GitHub backend)
"""
import hashlib
import uuid
import platform
import json
import base64
import datetime
import os
import sys
import requests

GITHUB_TOKEN = os.environ.get("GB_TOKEN", "")  # set via config.dat
GITHUB_REPO  = "yamannerhan/REHA"
GITHUB_API   = "https://api.github.com"
LICENSE_FILE = "licenses.json"
VERSION_FILE = "version.json"
APP_VERSION  = "1.0.0"


def _get_base_dir() -> str:
    """PyInstaller frozen EXE veya normal Python — doğru dizini döndür."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


LOCAL_CACHE = os.path.join(_get_base_dir(), ".lic_cache")
CONFIG_FILE = os.path.join(_get_base_dir(), ".gbcfg")


def _fix_ssl():
    """PyInstaller'da SSL sertifikası yolunu düzelt."""
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE",      certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    except Exception:
        pass


_fix_ssl()

_XOR_KEY = 0x5A


def _xor(data: bytes) -> bytes:
    return bytes(b ^ _XOR_KEY for b in data)


def _load_token() -> str:
    try:
        with open(CONFIG_FILE, "rb") as f:
            return _xor(f.read()).decode("utf-8").strip()
    except Exception:
        return os.environ.get("GB_TOKEN", "")


def _save_token(token: str):
    try:
        with open(CONFIG_FILE, "wb") as f:
            f.write(_xor(token.encode("utf-8")))
    except Exception:
        pass


def get_token() -> str:
    t = _load_token()
    if not t:
        t = os.environ.get("GB_TOKEN", "")
    return t


def get_headers():
    return {
        "Authorization": f"token {get_token()}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_hwid() -> str:
    try:
        mac  = str(uuid.getnode())
        cpu  = platform.processor() or platform.machine()
        node = platform.node()
        raw  = f"{mac}|{cpu}|{node}|GREEDY"
        return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
    except Exception:
        return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:24].upper()


def _gh_get(path: str):
    tok = get_token()
    if not tok:
        raise RuntimeError("Token bulunamadı (.gbcfg eksik)")
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers=get_headers(), timeout=15)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    if r.status_code == 401:
        raise RuntimeError("GitHub token geçersiz (401)")
    if r.status_code == 403:
        raise RuntimeError("GitHub erişim reddedildi (403)")
    if r.status_code == 404:
        raise RuntimeError(f"GitHub dosya bulunamadı: {path}")
    return None, None


def _gh_put(path: str, content_obj: dict, sha: str, message: str = "update"):
    url     = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    content = base64.b64encode(
        json.dumps(content_obj, indent=2, ensure_ascii=False).encode()
    ).decode()
    payload = {"message": message, "content": content}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=get_headers(), json=payload, timeout=12)
    return r.status_code in (200, 201), r


def fetch_licenses():
    return _gh_get(LICENSE_FILE)


def save_licenses(data: dict, sha: str):
    return _gh_put(LICENSE_FILE, data, sha, "Key güncelleme")


def generate_key(key_type: str = "unlimited", days: int = 0) -> str:
    import random, string
    chars = string.ascii_uppercase + string.digits
    part  = lambda n: "".join(random.choices(chars, k=n))
    return f"GB-{part(5)}-{part(5)}-{part(5)}"


def validate_key(key: str, hwid: str) -> tuple[bool, str]:
    """
    Returns (ok: bool, message: str)
    """
    try:
        data, sha = fetch_licenses()
        if data is None:
            return False, "Sunucuya bağlanılamadı"

        licenses = data.get("licenses", [])
        entry    = next((x for x in licenses if x.get("key") == key), None)

        if entry is None:
            return False, "Geçersiz key"
        if not entry.get("active", True):
            return False, "Key deaktif edilmiş"

        # Süre kontrolü
        expires = entry.get("expires_at")
        if expires:
            exp = datetime.datetime.fromisoformat(expires)
            if datetime.datetime.now() > exp:
                return False, f"Key süresi dolmuş ({exp.strftime('%d.%m.%Y')})"

        # HWID kontrolü
        bound = entry.get("machine_id")
        if not bound:
            # İlk aktivasyon — HWID bağla
            entry["machine_id"]   = hwid
            entry["activated"]    = True
            entry["activated_at"] = datetime.datetime.now().isoformat()
            if entry.get("type") in ("daily", "monthly", "yearly") and not expires:
                d = entry.get("duration_days", 0)
                entry["expires_at"] = (
                    datetime.datetime.now() + datetime.timedelta(days=d)
                ).isoformat()
            data_new = dict(data)
            data_new["licenses"] = [e if e["key"] != key else entry for e in licenses]
            save_licenses(data_new, sha)
            return True, f"Key aktifleştirildi ({entry.get('type','?')})"
        elif bound == hwid:
            ktype   = entry.get("type", "?")
            exp_str = ""
            if expires:
                exp = datetime.datetime.fromisoformat(expires)
                exp_str = f" | Bitiş: {exp.strftime('%d.%m.%Y')}"
            return True, f"Geçerli key ({ktype}{exp_str})"
        else:
            return False, "Bu key başka bir PC'ye kayıtlı (HWID uyuşmuyor)"

    except requests.exceptions.ConnectionError as e:
        return False, f"İnternet bağlantısı yok ({e.__class__.__name__})"
    except requests.exceptions.Timeout:
        return False, "Bağlantı zaman aşımı (timeout)"
    except Exception as ex:
        return False, f"Hata: {ex}"


def reset_hwid(key: str) -> tuple[bool, str]:
    try:
        data, sha = fetch_licenses()
        if data is None:
            return False, "Bağlantı hatası"
        licenses = data.get("licenses", [])
        entry    = next((x for x in licenses if x.get("key") == key), None)
        if entry is None:
            return False, "Key bulunamadı"
        entry["machine_id"]   = None
        entry["activated"]    = False
        entry["activated_at"] = None
        data["licenses"]      = [e if e["key"] != key else entry for e in licenses]
        ok, _ = save_licenses(data, sha)
        return (ok, "HWID sıfırlandı") if ok else (False, "GitHub yazma hatası")
    except Exception as ex:
        return False, str(ex)


def add_key(key: str, key_type: str, days: int = 0) -> tuple[bool, str]:
    try:
        data, sha = fetch_licenses()
        if data is None:
            return False, "Bağlantı hatası"
        if any(x["key"] == key for x in data.get("licenses", [])):
            return False, "Key zaten mevcut"
        now = datetime.datetime.now()
        expires = None
        if key_type == "daily":
            expires = (now + datetime.timedelta(days=days or 1)).isoformat()
        elif key_type == "monthly":
            expires = (now + datetime.timedelta(days=days or 30)).isoformat()
        elif key_type == "yearly":
            expires = (now + datetime.timedelta(days=days or 365)).isoformat()
        new_entry = {
            "key":          key,
            "type":         key_type,
            "duration_days": days,
            "created_at":   now.strftime("%Y-%m-%d"),
            "activated":    False,
            "active":       True,
            "machine_id":   None,
            "activated_at": None,
            "expires_at":   expires,
        }
        data["licenses"].append(new_entry)
        ok, _ = save_licenses(data, sha)
        return (ok, f"Key eklendi: {key}") if ok else (False, "GitHub yazma hatası")
    except Exception as ex:
        return False, str(ex)


def revoke_key(key: str) -> tuple[bool, str]:
    try:
        data, sha = fetch_licenses()
        if data is None:
            return False, "Bağlantı hatası"
        licenses = data.get("licenses", [])
        entry    = next((x for x in licenses if x.get("key") == key), None)
        if entry is None:
            return False, "Key bulunamadı"
        entry["active"] = False
        data["licenses"] = [e if e["key"] != key else entry for e in licenses]
        ok, _ = save_licenses(data, sha)
        return (ok, "Key iptal edildi") if ok else (False, "GitHub yazma hatası")
    except Exception as ex:
        return False, str(ex)


def check_update() -> dict:
    try:
        data, _ = _gh_get(VERSION_FILE)
        if data:
            return data
    except Exception:
        pass
    return {}


def save_local_key(key: str):
    try:
        with open(LOCAL_CACHE, "w") as f:
            f.write(key)
    except Exception:
        pass


def load_local_key() -> str:
    try:
        with open(LOCAL_CACHE, "r") as f:
            return f.read().strip()
    except Exception:
        return ""
