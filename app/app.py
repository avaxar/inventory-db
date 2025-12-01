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


# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add(
        "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,PATCH,OPTIONS"
    )
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@app.get("/")
def root_page():
    return app.send_static_file("index.html")


def get_database():
    db_path = os.path.join(os.path.dirname(__file__), "../db.sqlite")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


@app.before_request
def init_database():
    # Only runs once
    app.before_request_funcs[None].remove(init_database)

    try:
        info("Initializing database...")
        with get_database() as db:
            # Use absolute path for schema file
            schema_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "schema.sql"
            )
            info(f"Looking for schema at: {schema_path}")
            with open(schema_path) as schema:
                db.executescript(schema.read())

            info("Schema loaded successfully")

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
            info("Database initialization completed successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise
