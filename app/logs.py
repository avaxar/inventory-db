from .app import *
from .login import privileged


@app.get("/api/logs")
@privileged("r")
def get_logs():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT *
            FROM inventory_logs;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "time": row["time"],
            "type": row["type"],
            "product_id": row["product_id"],
            "delta": row["delta"],
            "note": row["note"],
        }
        for row in rows
    }


@app.get("/api/logs/<int:log_id>")
@privileged("r")
def get_log(log_id):
    with get_database() as db:
        row = db.execute(
            """
            SELECT time, type, product_id, delta, note
            FROM inventory_logs
            WHERE id = ?;
            """,
            (log_id,),
        ).fetchone()

    if row is None:
        return {"message": "Log entry is not found!"}, 404

    return dict(row)


@app.post("/api/logs")
@privileged("a")
def create_log():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    type_ = data.get("type")
    if not type_:
        return {"message": "A type is required!"}, 400

    product_id = data.get("product_id")
    if not product_id:
        return {"message": "A product is required!"}, 400

    delta = data.get("delta")
    if delta is None:
        return {"message": "A delta value is required!"}, 400

    try:
        with get_database() as db:
            cursor = db.execute(
                """
                INSERT INTO inventory_logs (type, product_id, delta, note)
                VALUES (?, ?, ?, ?);
                """,
                (type_, product_id, delta, data.get("note")),
            )
            log_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        if "product_id" in str(e):
            return {"message": "Product does not exist!"}, 400
        if "type" in str(e):
            return {"message": "Invalid type!"}, 400
        return {"message": "Invalid input or constraint violation!"}, 400

    return {"message": "Log entry has been created.", "id": log_id}, 201


@app.patch("/api/logs/<int:log_id>")
@privileged("a")
def update_log(log_id):
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    fields = []
    values = []

    for key in {"type", "product_id", "delta", "note"}:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return {"message": "Nothing to update."}, 400

    try:
        with get_database() as db:
            result = db.execute(
                f"""
                UPDATE inventory_logs
                SET {', '.join(fields)}
                WHERE id = ?;
                """,
                tuple(values + [log_id]),
            )
    except sqlite3.IntegrityError as exc:
        msg = str(exc).lower()
        if "product_id" in msg:
            return {"message": "Product does not exist!"}, 400
        if "type" in msg:
            return {"message": "Invalid type!"}, 400
        return {"message": "Invalid input or constraint violation!"}, 400

    if result.rowcount == 0:
        return {"message": "Log entry is not found!"}, 404

    return {"message": "Log entry has been updated."}


@app.delete("/api/logs/<int:log_id>")
@privileged("a")
def delete_log(log_id):
    with get_database() as db:
        result = db.execute(
            """
            DELETE FROM inventory_logs
            WHERE id = ?;
            """,
            (log_id,),
        )

    if result.rowcount == 0:
        return {"message": "Log entry is not found!"}, 404

    return {"message": "Log entry has been deleted."}
