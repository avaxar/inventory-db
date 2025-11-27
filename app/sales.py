from .app import *
from .login import privileged


@app.get("/api/sales")
@privileged("r")
def get_sales():
    with get_database() as db:
        rows = db.execute(
            """
            SELECT id, time, total_cents, customer_id, user_id
            FROM sales;
            """
        ).fetchall()

    return {
        str(row["id"]): {
            "time": row["time"],
            "total_cents": row["total_cents"],
            "customer_id": row["customer_id"],
            "user_id": row["user_id"],
        }
        for row in rows
    }


@app.get("/api/sales/<int:sale_id>")
@privileged("r")
def get_sale(sale_id):
    with get_database() as db:
        head = db.execute(
            """
            SELECT id, time, total_cents, customer_id, user_id
            FROM sales
            WHERE id = ?;
            """,
            (sale_id,),
        ).fetchone()

        if head is None:
            return {"message": "Sale is not found!"}, 404

        details = db.execute(
            """
            SELECT sl.subtotal_cents, sl.log_id, sl.note, il.product_id, -il.delta AS quantity
            FROM sales_details AS sd
                LEFT JOIN inventory_logs AS il
                ON (sd.log_id = il.id)
            WHERE sale_id = ?;
            """,
            (sale_id,),
        ).fetchall()

    return {
        "id": head["id"],
        "time": head["time"],
        "total_cents": head["total_cents"],
        "customer_id": head["customer_id"],
        "user_id": head["user_id"],
        "details": [dict(row) for row in details],
    }


@app.post("/api/sales")
@privileged("w")
def create_sale():
    data = request.get_json(force=True)
    if not data:
        return {"message": "A JSON body is required!"}, 400

    customer_id = data.get("customer_id")
    if not customer_id:
        return {"message": "A customer is required!"}, 400

    details = data.get("details")
    if not details or not isinstance(details, list):
        return {"message": "A non-empty list of details is required!"}, 400

    with get_database() as db:
        try:
            cursor = db.execute(
                """
                INSERT INTO sales (customer_id, user_id)
                VALUES (?, ?);
                """,
                (customer_id, session["user_id"]),
            )
            sale_id = cursor.lastrowid

            for item in details:
                product_id = item.get("product_id")
                quantity = item.get("quantity")
                subtotal = item.get("subtotal_cents")
                note = item.get("note")

                if not subtotal:
                    return {"message": "Each detail requires a subtotal!"}, 400

                log_id = None
                if product_id:
                    if not quantity:
                        return {
                            "message": "Each detail that contains inventory change must have a quantity!"
                        }, 400

                    log_cur = db.execute(
                        """
                        INSERT INTO inventory_logs (type, product_id, delta, note)
                        VALUES ('s', ?, ?, ?);
                        """,
                        (
                            product_id,
                            -quantity,
                            f"Automatic logging from sale #{sale_id}: {note}",
                        ),
                    )
                    log_id = log_cur.lastrowid

                db.execute(
                    """
                    INSERT INTO sales_details (subtotal_cents, sale_id, log_id, note)
                    VALUES (?, ?, ?, ?);
                    """,
                    (subtotal, sale_id, log_id, note),
                )
        except sqlite3.IntegrityError as exc:
            msg = str(exc).lower()
            if "customer_id" in msg:
                return {"message": "Customer does not exist!"}, 400
            if "product_id" in msg:
                return {"message": "Product does not exist!"}, 400
            return {"message": "Invalid input or constraint violation!"}, 400

    return {"message": "Sale has been created.", "id": sale_id}, 201


@app.delete("/api/sales/<int:sale_id>")
@privileged("a")
def delete_sale(sale_id):
    with get_database() as db:
        rows = db.execute(
            """
            SELECT log_id
            FROM sales_details
            WHERE sale_id = ?;
            """,
            (sale_id,),
        ).fetchall()

        log_ids = [row["log_id"] for row in rows if row["log_id"] is not None]
        if log_ids:
            db.execute(
                f"""
                DELETE FROM inventory_logs
                WHERE id IN ({','.join('?' * len(log_ids))});
                """,
                tuple(log_ids),
            )

        db.execute(
            """
            DELETE FROM sales_details
            WHERE sale_id = ?;
            """,
            (sale_id,),
        )

        result = db.execute(
            """
            DELETE FROM sales
            WHERE id = ?;
            """,
            (sale_id,),
        )

        if result.rowcount == 0:
            return {"message": "Sale is not found!"}, 404

    return {"message": "Sale has been deleted."}
