from .app import *
from .login import privileged


@app.get("/api/users")
@privileged("r")
def get_users():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT id, username, role
            FROM users;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "username": row["username"],
            "role": row["role"],
        }
        for row in rows
    }


@app.get("/api/users/<int:user_id>")
@privileged("r")
def get_user(user_id):
    with get_database() as db:
        row = db.execute(
            """
            SELECT username, role
            FROM users
            WHERE id = ?;
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return {"message": "User is not found!"}, 404

    return dict(row)


@app.post("/api/users")
@privileged("a")
def create_user():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    username = data.get("username")
    if not username:
        return {"message": "A username is required!"}, 400

    password = data.get("password")
    if not password:
        return {"message": "A password is required!"}, 400

    role = data.get("role")
    if role not in {"r", "w", "a", "d"}:
        return {"message": "Invalid role!"}, 400

    with get_database() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?);
                """,
                (username, bcrypt.generate_password_hash(password).decode(), role),
            )
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return {"message": "Username already exists!"}, 409
            return {"message": "Invalid input or constraint violation!"}, 400

    return {"message": "User has been created.", "id": user_id}, 201


@app.patch("/api/users/<int:user_id>")
@privileged("a")
def update_user(user_id):
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    fields = []
    values = []

    if "username" in data:
        fields.append("username = ?")
        values.append(data["username"])
    if "password" in data:
        fields.append("password_hash = ?")
        values.append(bcrypt.generate_password_hash(data["password"]).decode())
    if "role" in data:
        if data["role"] not in {"r", "w", "a", "d"}:
            return {"message": "Invalid role!"}, 400
        fields.append("role = ?")
        values.append(data["role"])

    if not fields:
        return {"message": "Nothing to update."}, 400

    values.append(user_id)

    with get_database() as db:
        result = db.execute(
            f"""
            UPDATE users
            SET {', '.join(fields)}
            WHERE id = ?;
            """,
            tuple(values),
        )

    if result.rowcount == 0:
        return {"message": "User is not found!"}, 404

    return {"message": "User has been updated."}


@app.delete("/api/users/<int:user_id>")
@privileged("a")
def delete_user(user_id):
    with get_database() as db:
        result = db.execute(
            """
            DELETE FROM users
            WHERE id = ?;
            """,
            (user_id,),
        )

    if result.rowcount == 0:
        return {"message": "User is not found!"}, 404

    return {"message": "User has been deleted."}
