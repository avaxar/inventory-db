from .app import *
from .login import privileged


@app.get("/api/products")
@privileged("r")
def get_products():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT *
            FROM products;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "sku": row["sku"],
            "active": row["active"],
            "name": row["name"],
            "price_cents": row["price_cents"],
            "quantity": row["quantity"],
            "description": row["description"],
            "category_id": row["category_id"],
        }
        for row in rows
    }


@app.get("/api/products/<int:product_id>")
@privileged("r")
def get_product(product_id):
    with get_database() as db:
        row = db.execute(
            """
            SELECT sku, active, name, price_cents, quantity, description, category_id
            FROM products
            WHERE id = ?;
            """,
            (product_id,),
        ).fetchone()

    if row is None:
        return {"message": "Product is not found!"}, 404

    return dict(row)


@app.post("/api/products")
@privileged("w")
def create_product():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    name = data.get("name")
    if not name:
        return {"message": "A name is required!"}, 400

    active = data.get("active")
    if not active or not isinstance(active, bool):
        return {"message": "A boolean active value is required!"}, 400

    with get_database() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO products (
                    sku, active, name, price_cents, description, category_id
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    data.get("sku"),
                    int(active),
                    name,
                    data.get("price_cents"),
                    data.get("description"),
                    data.get("category_id"),
                ),
            )

            product_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "sku" in str(e):
                return {"message": "SKU already exists!"}, 409
            if "category_id" in str(e):
                return {"message": "Category does not exist!"}, 400
            return {"message": "Invalid input or constraint violation!"}, 400

    return {"message": "Product has been created.", "id": product_id}, 201


@app.patch("/api/products/<int:product_id>")
@privileged("w")
def update_product(product_id):
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    fields = []
    values = []

    for key in {
        "sku",
        "active",
        "name",
        "price_cents",
        "description",
        "category_id",
    }:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    if not fields:
        return {"message": "Nothing to update."}, 400

    with get_database() as db:
        try:
            result = db.execute(
                f"""
                UPDATE products
                SET {', '.join(fields)}
                WHERE id = ?;
                """,
                tuple(values + [product_id]),
            )
        except sqlite3.IntegrityError as e:
            if "sku" in str(e):
                return {"message": "SKU already exists!"}, 409
            if "category_id" in str(e):
                return {"message": "Category does not exist!"}, 400
            return {"message": "Invalid input or constraint violation!"}, 400

    if result.rowcount == 0:
        return {"message": "Product is not found!"}, 404

    return {"message": "Product has been updated."}


@app.delete("/api/products/<int:product_id>")
@privileged("a")
def delete_product(product_id):
    with get_database() as db:
        result = db.execute(
            """
            DELETE FROM products
            WHERE id = ?;
            """,
            (product_id,),
        )

    if result.rowcount == 0:
        return {"message": "Product is not found!"}, 404

    return {"message": "Product has been deleted."}
