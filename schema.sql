-- Forces SQLite to check foreign keys
PRAGMA foreign_keys = ON;

------------------
-- System users --
------------------

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,

    CONSTRAINT username_check UNIQUE (username),
    CONSTRAINT role_check CHECK (role IN ('d', 'r', 'w', 'a'))
    -- `d`eactivated (None), `r`ead (R), `w`rite (CR), `a`dmin (CRUD)
);

CREATE INDEX IF NOT EXISTS index_username ON users(username);

---------------------------------
-- Client/customer information --
---------------------------------

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT, -- Or town
    state TEXT, -- Or province
    post_code TEXT,
    country TEXT,

    CONSTRAINT email_check CHECK (email LIKE '%_@__%.__%')
);

------------------------
-- Product information --
------------------------

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT, -- Optional

    CONSTRAINT name_check UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT, -- Optionally tied
    active INTEGER NOT NULL,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT (0),
    description TEXT, -- Optional
    category_id INTEGER, -- Optional

    CONSTRAINT sku_check UNIQUE (sku),
    CONSTRAINT active_check CHECK (active IN (0, 1)),
    CONSTRAINT price_check CHECK (price_cents > 0),
    CONSTRAINT quantity_check CHECK (quantity >= 0),
    CONSTRAINT category_id_check FOREIGN KEY (category_id) REFERENCES categories(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS index_sku ON products(sku);

--------------------
-- Inventory logs --
--------------------

CREATE TABLE IF NOT EXISTS inventory_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time INTEGER NOT NULL DEFAULT (unixepoch()),
    type TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    note TEXT, -- Optional

    CONSTRAINT type_check CHECK (type IN ('s', 'f', 'r', 'd', 'a', 'o')),
    -- `s`ale, re`f`ill (restock), `r`eturned, `d`amaged, `a`djustment, `o`ther
    CONSTRAINT product_id_check FOREIGN KEY (product_id) REFERENCES products(id)
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
    customer_id INTEGER, -- Optional due to deletion
    user_id INTEGER, -- Linking to the writer; optional due to deletion

    CONSTRAINT customer_id_check FOREIGN KEY (customer_id) REFERENCES customers(id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT user_id_check FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtotal_cents INTEGER NOT NULL,
    sale_id INTEGER NOT NULL,
    log_id INTEGER, -- Optional, linking to the product being bought
    note TEXT, -- Optional

    CONSTRAINT sale_id_check FOREIGN KEY (sale_id) REFERENCES sales(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT log_id_check_unique UNIQUE (log_id),
    CONSTRAINT log_id_check FOREIGN KEY (log_id) REFERENCES inventory_logs(id)
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
