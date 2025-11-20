-- Forces SQLite to check foreign keys
PRAGMA foreign_keys = ON;

------------------
-- System users --
------------------

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('d', 'r', 'w', 'a'))
    -- `d`eactivated (None), `r`ead (R), `w`rite (CR), `a`dmin (CRUD)
);

CREATE INDEX IF NOT EXISTS index_username ON users(username);

---------------------------------
-- Client/customer information --
---------------------------------

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT CHECK (email LIKE '%_@__%.__%'),
    phone TEXT,
    address TEXT,
    city TEXT, -- Or town
    state TEXT, -- Or province
    post_code TEXT,
    country TEXT
);

------------------------
-- Product information --
------------------------

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT -- Optional
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE, -- Optionally tied
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    quantity INTEGER NOT NULL DEFAULT (0) CHECK (quantity >= 0),
    description TEXT, -- Optional
    category_id INTEGER, -- Optional

    FOREIGN KEY (category_id) REFERENCES categories(id) 
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS index_sku ON products(sku);

--------------------
-- Inventory logs --
--------------------

CREATE TABLE IF NOT EXISTS inventory_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time INTEGER NOT NULL DEFAULT (unixepoch()),
    type TEXT NOT NULL CHECK (type IN ('s', 'f', 'r', 'd', 'a', 'o')),
    -- `s`ale, re`f`ill (restock), `r`eturned, `d`amaged, `a`djustment, `o`ther
    product_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,

    FOREIGN KEY (product_id) REFERENCES products(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TRIGGER IF NOT EXISTS insert_quantity_delta
AFTER INSERT ON inventory_logs
BEGIN
    UPDATE products
    SET quantity = products.quantity + NEW.delta
    WHERE products.id = NEW.product_id;
END;

CREATE TRIGGER IF NOT EXISTS delete_quantity_delta
AFTER DELETE ON inventory_logs
BEGIN
    UPDATE products
    SET quantity = products.quantity - OLD.delta
    WHERE products.id = OLD.product_id;
END;

CREATE TRIGGER IF NOT EXISTS update_quantity_delta
AFTER UPDATE ON inventory_logs
BEGIN
    UPDATE products
    SET quantity = products.quantity - OLD.delta
    WHERE products.id = OLD.product_id;

    UPDATE products
    SET quantity = products.quantity + NEW.delta
    WHERE products.id = NEW.product_id;
END;

-----------------------
-- Sales information --
-----------------------

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time INTEGER NOT NULL DEFAULT (unixepoch()),
    total_cents INTEGER NOT NULL DEFAULT (0),
    customer_id INTEGER NOT NULL,
    user_id INTEGER, -- Optional, linking to the writer

    FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtotal_cents INTEGER NOT NULL,
    sale_id INTEGER NOT NULL,
    log_id INTEGER UNIQUE, -- Optional, linking to the product being bought
    note TEXT, -- Optional

    FOREIGN KEY (sale_id) REFERENCES sales(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (log_id) REFERENCES inventory_logs(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TRIGGER IF NOT EXISTS insert_subtotal
AFTER INSERT ON sales_details
BEGIN
    UPDATE sales
    SET total_cents = sales.total_cents + NEW.subtotal_cents
    WHERE sales.id = NEW.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS delete_subtotal
AFTER DELETE ON sales_details
BEGIN
    UPDATE sales
    SET total_cents = sales.total_cents - OLD.subtotal_cents
    WHERE sales.id = OLD.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS update_subtotal
AFTER UPDATE ON sales_details
BEGIN
    UPDATE sales
    SET total_cents = sales.total_cents - OLD.subtotal_cents
    WHERE sales.id = OLD.sale_id;

    UPDATE sales
    SET total_cents = sales.total_cents + NEW.subtotal_cents
    WHERE sales.id = NEW.sale_id;
END;
