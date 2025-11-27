import logging
from logging import info, warning
import os

from dotenv import load_dotenv
from flask import Flask, request, session
from flask_bcrypt import Bcrypt
import sqlite3


load_dotenv()
app = Flask(__name__, static_folder="../static")
app.secret_key = os.environ.get("INVENTORY_DB_KEY", "debug_test")
bcrypt = Bcrypt(app)
logging.basicConfig(level=logging.INFO)


@app.get("/")
def root_page():
    return app.redirect("/login")


def get_database():
    db = sqlite3.connect("db.sqlite")
    db.row_factory = sqlite3.Row
    return db


@app.before_request
def init_database():
    # Only runs once
    app.before_request_funcs[None].remove(init_database)

    info("Initializing database...")
    with get_database() as db:
        with open("schema.sql") as schema:
            db.executescript(schema.read())

        if (
            db.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE users.role = 'a' OR users.username = "admin";
                """
            ).fetchone()[0]
            == 0
        ):
            info("No admin account exists. Creating one...")
            db.execute(
                """
                INSERT INTO users(username, password_hash, role)
                VALUES ("admin", ?, 'a');
                """,
                (bcrypt.generate_password_hash("admin").decode(),),
            )
            info(
                "Please log into 'admin' with the password 'admin' and change the password."
            )

        db.commit()
