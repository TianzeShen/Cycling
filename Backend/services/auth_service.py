from sqlalchemy import text

try:
    from Backend.database import fetch_one, get_transaction_connection
    from Backend.schemas import AuthLoginRequest, AuthRegisterRequest, AuthUserResponse
except ModuleNotFoundError:
    from database import fetch_one, get_transaction_connection
    from schemas import AuthLoginRequest, AuthRegisterRequest, AuthUserResponse


class UsernameTakenError(ValueError):
    pass


def register_username(payload: AuthRegisterRequest) -> AuthUserResponse:
    username = payload.username.strip()
    username_normalized = normalise_username(username)

    with get_transaction_connection() as connection:
        ensure_local_uuid_user_exists(connection, payload.user_id)

        existing_username_owner = (
            connection.execute(
                text(
                    """
                    SELECT user_id::text AS user_id
                    FROM ridesmart.app_user
                    WHERE username_normalized = :username_normalized
                    LIMIT 1
                    """
                ),
                {"username_normalized": username_normalized},
            )
            .mappings()
            .first()
        )

        if (
            existing_username_owner is not None
            and existing_username_owner["user_id"] != payload.user_id
        ):
            raise UsernameTakenError("This username is already in use.")

        row = (
            connection.execute(
                text(
                    """
                    UPDATE ridesmart.app_user
                    SET
                        username = :username,
                        username_normalized = :username_normalized,
                        is_registered = true,
                        full_name = :username
                    WHERE user_id = CAST(:user_id AS uuid)
                    RETURNING
                        user_id::text AS user_id,
                        username,
                        COALESCE(is_registered, false) AS is_registered
                    """
                ),
                {
                    "user_id": payload.user_id,
                    "username": username,
                    "username_normalized": username_normalized,
                },
            )
            .mappings()
            .first()
        )

    if row is None:
        raise RuntimeError("Unable to register this username right now.")

    return AuthUserResponse(**dict(row))


def login_with_username(payload: AuthLoginRequest) -> AuthUserResponse:
    row = fetch_one(
        """
        SELECT
            user_id::text AS user_id,
            username,
            COALESCE(is_registered, false) AS is_registered
        FROM ridesmart.app_user
        WHERE username_normalized = :username_normalized
          AND COALESCE(is_registered, false) = true
        LIMIT 1
        """,
        {"username_normalized": normalise_username(payload.username)},
    )
    if row is None:
        raise LookupError("No registered account was found for this username.")
    return AuthUserResponse(**row)


def get_user_identity(user_id: str) -> AuthUserResponse:
    row = fetch_one(
        """
        SELECT
            user_id::text AS user_id,
            username,
            COALESCE(is_registered, false) AS is_registered
        FROM ridesmart.app_user
        WHERE user_id = CAST(:user_id AS uuid)
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    if row is None:
        with get_transaction_connection() as connection:
            ensure_local_uuid_user_exists(connection, user_id)
        row = {
            "user_id": user_id,
            "username": None,
            "is_registered": False,
        }
    return AuthUserResponse(**row)


def normalise_username(username: str) -> str:
    return " ".join(username.strip().lower().split())


def ensure_local_uuid_user_exists(connection, user_id: str) -> None:
    exists = connection.execute(
        text(
            """
            SELECT 1
            FROM ridesmart.app_user
            WHERE user_id = CAST(:user_id AS uuid)
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).scalar()
    if exists:
        return

    connection.execute(
        text(
            """
            INSERT INTO ridesmart.app_user (
                user_id,
                full_name,
                email,
                password_hash
            )
            VALUES (
                CAST(:user_id AS uuid),
                :full_name,
                :email,
                :password_hash
            )
            """
        ),
        {
            "user_id": user_id,
            "full_name": f"Local User {user_id[:8]}",
            "email": f"local-{user_id}@ridesmart.local",
            "password_hash": "localstorage-uuid-placeholder",
        },
    )
