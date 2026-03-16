-- Olist Brazilian E-Commerce Dataset (real data from GitHub)
CREATE SCHEMA IF NOT EXISTS olist;

CREATE TABLE olist.customers (
    customer_id VARCHAR(64) PRIMARY KEY,
    customer_unique_id VARCHAR(64),
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state VARCHAR(10)
);

CREATE TABLE olist.orders (
    order_id VARCHAR(64) PRIMARY KEY,
    customer_id VARCHAR(64) REFERENCES olist.customers(customer_id),
    order_status VARCHAR(30),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE olist.products (
    product_id VARCHAR(64) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

CREATE TABLE olist.sellers (
    seller_id VARCHAR(64) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(100),
    seller_state VARCHAR(10)
);

CREATE TABLE olist.order_items (
    order_id VARCHAR(64) REFERENCES olist.orders(order_id),
    order_item_id INTEGER,
    product_id VARCHAR(64) REFERENCES olist.products(product_id),
    seller_id VARCHAR(64) REFERENCES olist.sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price DECIMAL(10,2),
    freight_value DECIMAL(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE olist.order_payments (
    order_id VARCHAR(64) REFERENCES olist.orders(order_id),
    payment_sequential INTEGER,
    payment_type VARCHAR(30),
    payment_installments INTEGER,
    payment_value DECIMAL(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE olist.order_reviews (
    review_id VARCHAR(64) PRIMARY KEY,
    order_id VARCHAR(64) REFERENCES olist.orders(order_id),
    review_score INTEGER,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

CREATE TABLE olist.product_category_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);
