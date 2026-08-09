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
import contextlib
import getpass
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from bimarz.constants import PROFILES_FILE
from bimarz.models import ServerProfile

_PBKDF2_ITERATIONS = 480_000
_SALT_SIZE_BYTES = 16
_PASSWORD_ENV_VAR = "BIMARZ_PROFILE_PASSWORD"


class ProfileStoreError(Exception):
    """Base error for profile storage.

    Base error for profile storage.
    """


class WrongPasswordError(ProfileStoreError):
    """Raised when profile data cannot be decrypted.

    Raised when profile data cannot be decrypted.
    """


class ProfileNotFoundError(ProfileStoreError):
    """Raised when a profile does not exist.

    Raised when a profile does not exist.
    """


def _derive_key(
    password: str,
    salt: bytes,
) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(
        kdf.derive(password.encode("utf-8")),
    )


def _prompt_for_password() -> str:
    env_password = os.environ.get(_PASSWORD_ENV_VAR)

    if env_password:
        return env_password

    return getpass.getpass("Profile store password: ")


class ProfileStore:
    """Encrypted CRUD store backed by a JSON file.

    Encrypted CRUD store backed by a JSON file.
    """

    def __init__(
        self,
        path: Path = PROFILES_FILE,
        password: str | None = None,
    ) -> None:
        self._path = path
        self._password = password if password is not None else _prompt_for_password()

        if not self._password:
            raise ProfileStoreError(
                "profile store password must not be empty",
            )

    def _read_encrypted_state(
        self,
    ) -> tuple[str, dict[str, Any]]:
        if not self._path.exists():
            fresh_salt = base64.urlsafe_b64encode(
                os.urandom(_SALT_SIZE_BYTES),
            ).decode("ascii")
            return fresh_salt, {}

        try:
            raw = json.loads(
                self._path.read_text(encoding="utf-8"),
            )

            salt_b64 = raw["salt"]
            ciphertext = raw["ciphertext"]

            salt = base64.urlsafe_b64decode(salt_b64)
            key = _derive_key(self._password, salt)

            fernet = Fernet(key)
            decrypted = fernet.decrypt(
                ciphertext.encode("ascii"),
            )

            profiles = json.loads(
                decrypted.decode("utf-8"),
            )

        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProfileStoreError(
                "profile store contains invalid data",
            ) from exc
        except InvalidToken as exc:
            raise WrongPasswordError(
                "could not decrypt the profile store: wrong password, or the file is corrupted",
            ) from exc

        if not isinstance(profiles, dict):
            raise ProfileStoreError(
                "profile store payload must be a mapping",
            )

        return salt_b64, profiles

    def _write_encrypted_state(
        self,
        salt_b64: str,
        profiles: dict[str, Any],
    ) -> None:
        salt = base64.urlsafe_b64decode(salt_b64)
        key = _derive_key(self._password, salt)
        fernet = Fernet(key)

        plaintext = json.dumps(
            profiles,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        ciphertext = fernet.encrypt(plaintext).decode("ascii")

        payload = json.dumps(
            {
                "salt": salt_b64,
                "ciphertext": ciphertext,
            },
            ensure_ascii=False,
            indent=2,
        )

        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self._path.name}.",
            dir=self._path.parent,
            text=True,
        )

        try:
            os.fchmod(fd, 0o600)

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as temp_file:
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_name, self._path)

            directory_fd = os.open(
                self._path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )

            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except Exception:
            with contextlib.suppress(OSError):
                os.close(fd)

            with contextlib.suppress(OSError):
                os.unlink(temp_name)

            raise

        with contextlib.suppress(OSError):
            os.chmod(self._path, 0o600)

    def list_profiles(self) -> list[ServerProfile]:
        _salt, profiles = self._read_encrypted_state()

        return [ServerProfile(**data) for data in profiles.values()]

    def get_profile(
        self,
        profile_id: str,
    ) -> ServerProfile:
        _salt, profiles = self._read_encrypted_state()

        if profile_id not in profiles:
            raise ProfileNotFoundError(
                f"no profile with id '{profile_id}'",
            )

        return ServerProfile(
            **profiles[profile_id],
        )

    def add_profile(
        self,
        profile: ServerProfile,
    ) -> None:
        salt, profiles = self._read_encrypted_state()

        profiles[profile.profile_id] = asdict(profile)

        self._write_encrypted_state(
            salt,
            profiles,
        )

    def remove_profile(
        self,
        profile_id: str,
    ) -> None:
        salt, profiles = self._read_encrypted_state()

        if profile_id not in profiles:
            raise ProfileNotFoundError(
                f"no profile with id '{profile_id}'",
            )

        del profiles[profile_id]

        self._write_encrypted_state(
            salt,
            profiles,
        )
