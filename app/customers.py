from .app import *
from .login import privileged


@app.get("/api/customers")
@privileged("r")
def get_customers():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT *
            FROM customers;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "address": row["address"],
            "city": row["city"],
            "state": row["state"],
            "post_code": row["post_code"],
            "country": row["country"],
        }
        for row in rows
    }


@app.get("/api/customers/<int:customer_id>")
@privileged("r")
def get_customer(customer_id):
    with get_database() as db:
        row = db.execute(
            """
            SELECT name, email, phone, address, city, state, post_code, country
            FROM customers
            WHERE id = ?;
            """,
            (customer_id,),
        ).fetchone()

    if row is None:
        return {"message": "Customer is not found!"}, 404

    return dict(row)


@app.post("/api/customers")
@privileged("w")
def create_customer():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    name = data.get("name")
    if not name:
        return {"message": "A name is required!"}, 400

    with get_database() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO customers (name, email, phone, address, city, state, post_code, country)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    name,
                    data.get("email"),
                    data.get("phone"),
                    data.get("address"),
                    data.get("city"),
                    data.get("state"),
                    data.get("post_code"),
                    data.get("country"),
                ),
            )
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                return {"message": "Invalid e-mail format!"}, 400
            return {"message": "Invalid input or constraint violation!"}, 400

        customer_id = cursor.lastrowid

    return {"message": "Customer has been created.", "id": customer_id}, 201


@app.patch("/api/customers/<int:customer_id>")
@privileged("w")
def update_customer(customer_id):
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    fields = []
    values = []

    for key in {
        "name",
        "email",
        "phone",
        "address",
        "city",
        "state",
        "post_code",
        "country",
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
                UPDATE customers
                SET {', '.join(fields)}
                WHERE id = ?;""",
                tuple(values + [customer_id]),
            )
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                return {"message": "Invalid e-mail format!"}, 400
            return {"message": "Invalid input or constraint violation!"}, 400

    if result.rowcount == 0:
        return {"message": "Customer is not found!"}, 404

    return {"message": "Customer has been updated."}


@app.delete("/api/customers/<int:customer_id>")
@privileged("a")
def delete_customer(customer_id):
    with get_database() as db:
        result = db.execute(
            """
            DELETE FROM customers
            WHERE id = ?;
            """,
            (customer_id,),
        )

    if result.rowcount == 0:
        return {"message": "Customer is not found!"}, 404

    return {"message": "Customer has been deleted."}
