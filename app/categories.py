from .app import *
from .login import privileged


@app.get("/api/categories")
@privileged("r")
def get_categories():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT *
            FROM categories;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "name": row["name"],
            "description": row["description"],
        }
        for row in rows
    }


@app.get("/api/categories/<int:category_id>")
@privileged("r")
def get_category(category_id):
    with get_database() as db:
        row = db.execute(
            """
            SELECT name, description
            FROM categories
            WHERE id = ?;
            """,
            (category_id,),
        ).fetchone()

    if row is None:
        return {"message": "Category is not found!"}, 404

    return dict(row)


@app.post("/api/categories")
@privileged("a")
def create_category():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    name = data.get("name")
    if not name:
        return {"message": "A name is required!"}, 400

    with get_database() as db:
        cursor = db.execute(
            """
            INSERT INTO categories (name, description)
            VALUES (?, ?);
            """,
            (
                name,
                data.get("description"),
            ),
        )

        category_id = cursor.lastrowid

    return {"message": "Category has been created", "id": category_id}, 201


@app.patch("/api/categories/<int:category_id>")
@privileged("a")
def update_category(category_id):
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    fields = []
    values = []

    for key in {"name", "description"}:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return {"message": "Nothing to update."}, 400

    with get_database() as db:
        result = db.execute(
            f"""
            UPDATE categories
            SET {', '.join(fields)}
            WHERE id = ?;""",
            tuple(values + [category_id]),
        )

    if result.rowcount == 0:
        return {"message": "Category is not found!"}, 404

    return {"message": "Category has been updated."}


@app.delete("/api/categories/<int:category_id>")
@privileged("a")
def delete_category(category_id):
    with get_database() as db:
        result = db.execute(
            """
            DELETE FROM categories
            WHERE id = ?;
            """,
            (category_id,),
        )

    if result.rowcount == 0:
        return {"message": "Category is not found!"}, 404

    return {"message": "Category has been deleted."}
