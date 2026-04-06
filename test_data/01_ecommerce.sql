-- E-Commerce Domain: orders, products, customers, payments
CREATE SCHEMA IF NOT EXISTS ecommerce;

CREATE TABLE ecommerce.customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ecommerce.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    stock_qty INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ecommerce.orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES ecommerce.customers(id),
    total DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ecommerce.payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES ecommerce.orders(id),
    amount DECIMAL(10,2) NOT NULL,
    method VARCHAR(50),
    status VARCHAR(50) DEFAULT 'completed',
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ecommerce.reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES ecommerce.products(id),
    customer_id INTEGER REFERENCES ecommerce.customers(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed customers
INSERT INTO ecommerce.customers (email, name, country) VALUES
('alice@example.com', 'Alice Johnson', 'US'),
('bob@shop.de', 'Bob Mueller', 'DE'),
('carlos@tienda.es', 'Carlos Garcia', 'ES'),
('diana@store.co.uk', 'Diana Smith', 'UK'),
('emma@boutique.fr', 'Emma Dupont', 'FR'),
('frank@mail.com', 'Frank Lee', 'US'),
('grace@email.jp', 'Grace Tanaka', 'JP'),
('henry@online.ca', 'Henry Brown', 'CA'),
('iris@shop.nl', 'Iris Van Der Berg', 'NL'),
('jack@store.au', 'Jack Wilson', 'AU');

-- Seed products
INSERT INTO ecommerce.products (name, category, price, stock_qty) VALUES
('Wireless Headphones', 'Electronics', 79.99, 150),
('Running Shoes', 'Footwear', 129.99, 85),
('Coffee Maker', 'Kitchen', 49.99, 200),
('Yoga Mat', 'Fitness', 29.99, 300),
('Laptop Stand', 'Office', 39.99, 120),
('Bluetooth Speaker', 'Electronics', 59.99, 95),
('Water Bottle', 'Fitness', 19.99, 500),
('Desk Lamp', 'Office', 34.99, 180),
('Backpack', 'Travel', 89.99, 70),
('Phone Case', 'Electronics', 14.99, 400);

-- Seed orders (last 30 days)
INSERT INTO ecommerce.orders (customer_id, total, status, created_at)
SELECT
    (random() * 9 + 1)::int,
    (random() * 200 + 15)::numeric(10,2),
    CASE WHEN random() > 0.05 THEN 'completed' ELSE 'cancelled' END,
    NOW() - (random() * 30 || ' days')::interval
FROM generate_series(1, 500);

-- Seed payments (with ~4% failure rate)
INSERT INTO ecommerce.payments (order_id, amount, method, status, failure_reason, created_at)
SELECT
    o.id, o.total,
    CASE (random() * 3)::int WHEN 0 THEN 'credit_card' WHEN 1 THEN 'paypal' ELSE 'bank_transfer' END,
    CASE WHEN random() > 0.04 THEN 'completed' ELSE 'failed' END,
    CASE WHEN random() <= 0.04 THEN 'Gateway timeout' ELSE NULL END,
    o.created_at
FROM ecommerce.orders o;

-- Seed reviews
INSERT INTO ecommerce.reviews (product_id, customer_id, rating, comment, created_at)
SELECT (random() * 9 + 1)::int, (random() * 9 + 1)::int, (random() * 4 + 1)::int,
    CASE (random() * 3)::int WHEN 0 THEN 'Great product!' WHEN 1 THEN 'Good value.' ELSE 'Decent.' END,
    NOW() - (random() * 60 || ' days')::interval
FROM generate_series(1, 200);
