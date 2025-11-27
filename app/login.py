from functools import wraps

from .app import *


@app.get("/login")
def login_page():
    session.clear()
    return app.send_static_file("login.html")


def privileged(access: str):
    assert access in {"r", "w", "a"}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return {"message": "You are not authorized."}, 401

            role = session["role"]
            match role:
                case "d":
                    return {"message": "Your authorization was revoked."}, 403
                case "r":
                    if access not in {"r"}:
                        return {"message": "You may not perform this operation."}, 403
                case "w":
                    if access not in {"r", "w"}:
                        return {"message": "You may not perform this operation."}, 403
                case "a":
                    pass
                case _:
                    assert False

            return func(*args, **kwargs)

        return wrapper

    return decorator


@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    username = data.get("username")
    if not username:
        return {"message": "A username is required!"}, 400

    password = data.get("password")
    if not username:
        return {"message": "A password is required!"}, 400

    with get_database() as db:
        user = db.execute(
            """
            SELECT id, username, password_hash, role
            FROM users
            WHERE username = ?;
            """,
            (username,),
        ).fetchone()

    if user is None or not bcrypt.check_password_hash(user["password_hash"], password):
        return {"message": "Invalid credentials!"}, 401

    session.clear()
    # session.regenerate()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    return {"message": "Logged in."}


@app.post("/api/logout")
def logout():
    session.clear()
    return {"message": "Logged out."}
