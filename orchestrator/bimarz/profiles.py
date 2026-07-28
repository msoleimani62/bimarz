"""Encrypted local storage for server profiles.

The whole profiles file is encrypted at rest with a password-derived key
(PBKDF2-HMAC-SHA256 -> Fernet), so the UUIDs and Reality keys inside never
sit on disk in plaintext. Zero sys.exit() here — every failure is a raised
exception, per this project's boundary rule (cli.py is the only place
allowed to exit).

ذخیره‌سازی محلی و رمزنگاری‌شده‌ی پروفایل‌های سرور.

کل فایل پروفایل‌ها در حالت سکون با یک کلید مشتق‌شده از پسورد رمزنگاری
می‌شود (PBKDF2-HMAC-SHA256 -> Fernet)، پس UUID ها و کلیدهای Reality هرگز
به‌صورت متن ساده روی دیسک نمی‌مانند. اینجا صفر sys.exit() است — هر خطا
یک استثنای پرتاب‌شده است، طبق قانون مرزی این پروژه (cli.py تنها جای
مجاز برای خروج است).
"""

from __future__ import annotations

import base64
import getpass
import json
import os
from dataclasses import asdict
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from bimarz.constants import PROFILES_FILE
from bimarz.models import ServerProfile

_PBKDF2_ITERATIONS = 480_000
_SALT_SIZE_BYTES = 16
_PASSWORD_ENV_VAR = "BIMARZ_PROFILE_PASSWORD"


class ProfileStoreError(Exception):
    """Base class for every profile-store error.

    کلاس پایه برای تمام خطاهای فروشگاه پروفایل.
    """


class WrongPasswordError(ProfileStoreError):
    """Raised when the stored profiles cannot be decrypted with the given
    password (wrong password, or the file is corrupted).

    زمانی پرتاب می‌شود که پروفایل‌های ذخیره‌شده با پسورد داده‌شده قابل
    رمزگشایی نیستند (پسورد اشتباه، یا فایل خراب است).
    """


class ProfileNotFoundError(ProfileStoreError):
    """Raised when removing or looking up a profile_id that doesn't exist.

    زمانی پرتاب می‌شود که profile_id ای برای حذف یا جستجو داده شده که
    وجود ندارد.
    """


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def _prompt_for_password() -> str:
    env_password = os.environ.get(_PASSWORD_ENV_VAR)
    if env_password:
        return env_password
    return getpass.getpass("Profile store password: ")


class ProfileStore:
    """Encrypted CRUD store for server profiles, backed by a single JSON
    file on disk (see constants.PROFILES_FILE). The first password used
    against a fresh (non-existent) file becomes that file's password;
    every later open must use the same one.

    فروشگاه رمزنگاری‌شده‌ی CRUD برای پروفایل‌های سرور، بر پایه‌ی یک فایل
    JSON واحد روی دیسک (نگاه کنید به constants.PROFILES_FILE). اولین
    پسوردی که روی یک فایل تازه (ناموجود) استفاده شود، پسورد آن فایل
    می‌شود؛ هر بار باز کردن بعدی باید همان را استفاده کند.
    """

    def __init__(self, path: Path = PROFILES_FILE, password: str | None = None) -> None:
        self._path = path
        self._password = password if password is not None else _prompt_for_password()

    def _read_encrypted_state(self) -> tuple[str, dict]:
        if not self._path.exists():
            fresh_salt = base64.urlsafe_b64encode(os.urandom(_SALT_SIZE_BYTES)).decode("ascii")
            return fresh_salt, {}

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        salt = base64.urlsafe_b64decode(raw["salt"])
        key = _derive_key(self._password, salt)
        fernet = Fernet(key)
        try:
            decrypted = fernet.decrypt(raw["ciphertext"].encode("ascii"))
        except InvalidToken as exc:
            raise WrongPasswordError(
                "could not decrypt the profile store: wrong password, or the file is corrupted"
            ) from exc

        profiles = json.loads(decrypted.decode("utf-8"))
        return raw["salt"], profiles

    def _write_encrypted_state(self, salt_b64: str, profiles: dict) -> None:
        salt = base64.urlsafe_b64decode(salt_b64)
        key = _derive_key(self._password, salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(json.dumps(profiles).encode("utf-8"))

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"salt": salt_b64, "ciphertext": ciphertext.decode("ascii")}, indent=2),
            encoding="utf-8",
        )

    def list_profiles(self) -> list[ServerProfile]:
        _salt, profiles = self._read_encrypted_state()
        return [ServerProfile(**data) for data in profiles.values()]

    def get_profile(self, profile_id: str) -> ServerProfile:
        _salt, profiles = self._read_encrypted_state()
        if profile_id not in profiles:
            raise ProfileNotFoundError(f"no profile with id '{profile_id}'")
        return ServerProfile(**profiles[profile_id])

    def add_profile(self, profile: ServerProfile) -> None:
        salt, profiles = self._read_encrypted_state()
        profiles[profile.profile_id] = asdict(profile)
        self._write_encrypted_state(salt, profiles)

    def remove_profile(self, profile_id: str) -> None:
        salt, profiles = self._read_encrypted_state()
        if profile_id not in profiles:
            raise ProfileNotFoundError(f"no profile with id '{profile_id}'")
        del profiles[profile_id]
        self._write_encrypted_state(salt, profiles)
