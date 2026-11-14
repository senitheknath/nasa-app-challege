"""Private farm repository. Only the trusted server supplies an authenticated owner."""

from contextlib import contextmanager, closing
import hashlib
import json
import math
import time
import uuid
from agroshift.identity.farm_records import validate_profile
from agroshift.science.knowledge.knowledge_store import postgres_connect
from agroshift.science.climate.power import DataError

OWNER_NAMESPACE = uuid.UUID("bb33730d-f65f-48e5-a238-d853d88e1593")


def owner_from_claims(claims, expected_issuer, now=None):
    """Use claims already verified by Streamlit OIDC; reject expired or mismatched sessions."""
    current = time.time() if now is None else now
    exp = claims.get("exp")
    sub = claims.get("sub")
    if (
        claims.get("is_logged_in") is not True
        or not expected_issuer
        or claims.get("iss") != expected_issuer
        or not isinstance(sub, str)
        or not 1 <= len(sub) <= 512
        or type(exp) not in (float, int)
        or not math.isfinite(exp)
        or exp <= current
    ):
        raise DataError("Sign in again to use private saved farms.")
    return str(
        uuid.uuid5(
            OWNER_NAMESPACE, json.dumps([expected_issuer, sub], separators=(",", ":"))
        )
    )


class PrivateStore:
    def __init__(self, dsn, owner):
        self.dsn = dsn
        self.owner = str(uuid.UUID(str(owner)))

    @contextmanager
    def connection(self):
        try:
            with closing(postgres_connect(self.dsn)) as conn:
                role = conn.execute(
                    "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                ).fetchone()
                if role["rolsuper"] or role["rolbypassrls"]:
                    raise DataError(
                        "Private storage needs the restricted application database role."
                    )
                with conn.transaction():
                    conn.execute(
                        "SELECT set_config('agroshift.owner_id',%s,true)", (self.owner,)
                    )
                    yield conn
        except DataError:
            raise
        except Exception as exc:
            # Never expose connection strings, SQL, or records in a browser error.
            raise DataError(
                "Private storage is unavailable. Your changes have not been saved."
            ) from exc

    def farms(self):
        with self.connection() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT id,profile,revision,updated_at FROM farm_profiles WHERE owner_id=%s ORDER BY updated_at DESC LIMIT 100",
                    (self.owner,),
                )
            ]

    def save_farm(self, value, identifier=None, revision=0):
        from psycopg.types.json import Jsonb

        value = validate_profile(value)
        with self.connection() as conn:
            if identifier:
                row = conn.execute(
                    """UPDATE farm_profiles SET profile=%s,revision=revision+1,updated_at=now()
                 WHERE id=%s AND owner_id=%s AND revision=%s RETURNING id,profile,revision,updated_at""",
                    (Jsonb(value), uuid.UUID(str(identifier)), self.owner, revision),
                ).fetchone()
                if row is None:
                    raise DataError(
                        "This farm changed in another session. Reload it before saving."
                    )
            else:
                if (
                    conn.execute(
                        "SELECT count(*) AS n FROM farm_profiles WHERE owner_id=%s",
                        (self.owner,),
                    ).fetchone()["n"]
                    >= 100
                ):
                    raise DataError("This account has reached the 100-farm limit.")
                row = conn.execute(
                    "INSERT INTO farm_profiles(owner_id,profile) VALUES (%s,%s) RETURNING id,profile,revision,updated_at",
                    (self.owner, Jsonb(value)),
                ).fetchone()
            return dict(row)

    def save_analysis(self, farm_id, record):
        from psycopg.types.json import Jsonb

        if record.get("schema") != "agroshift.crop-finder.v1":
            raise DataError("Only completed Crop Finder assessments can be saved.")
        body = json.dumps(
            {k: v for k, v in record.items() if k != "generated_at"},
            sort_keys=True,
            allow_nan=False,
        )
        if len(body) > 2_000_000:
            raise DataError("This assessment is too large to save.")
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self.connection() as conn:
            if not conn.execute(
                "SELECT 1 FROM farm_profiles WHERE id=%s AND owner_id=%s",
                (uuid.UUID(str(farm_id)), self.owner),
            ).fetchone():
                raise DataError("This farm is no longer available to your account.")
            conn.execute(
                """INSERT INTO saved_analyses(owner_id,farm_id,report,fingerprint)
                SELECT %s,id,%s,%s FROM farm_profiles WHERE id=%s AND owner_id=%s
                ON CONFLICT (owner_id,farm_id,fingerprint) DO NOTHING""",
                (
                    self.owner,
                    Jsonb(record),
                    digest,
                    uuid.UUID(str(farm_id)),
                    self.owner,
                ),
            )

    def history(self, farm_id, offset=0):
        if type(offset) is not int or offset < 0:
            raise DataError("Invalid history page.")
        with self.connection() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """SELECT id,created_at,report FROM saved_analyses
             WHERE owner_id=%s AND farm_id=%s ORDER BY created_at DESC,id DESC LIMIT 10 OFFSET %s""",
                    (self.owner, uuid.UUID(str(farm_id)), offset),
                )
            ]

    def account(self, display_name=None):
        with self.connection() as conn:
            if display_name is not None:
                if not isinstance(display_name, str) or len(display_name.strip()) > 80:
                    raise DataError("Use a display name of up to 80 characters.")
                conn.execute(
                    """INSERT INTO farmer_accounts(owner_id,display_name) VALUES (%s,%s)
                 ON CONFLICT(owner_id) DO UPDATE SET display_name=excluded.display_name,updated_at=now()""",
                    (self.owner, display_name.strip()),
                )
            row = conn.execute(
                "SELECT display_name FROM farmer_accounts WHERE owner_id=%s",
                (self.owner,),
            ).fetchone()
            return row["display_name"] if row else ""
