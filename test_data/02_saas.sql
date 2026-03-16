-- SaaS Domain: users, subscriptions, invoices, plans, usage_events
CREATE SCHEMA IF NOT EXISTS saas;

CREATE TABLE saas.plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price_monthly DECIMAL(10,2) NOT NULL,
    features TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE saas.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    company VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE saas.subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES saas.users(id),
    plan_id INTEGER REFERENCES saas.plans(id),
    status VARCHAR(50) DEFAULT 'active',
    started_at TIMESTAMP DEFAULT NOW(),
    cancelled_at TIMESTAMP,
    trial_ends_at TIMESTAMP
);

CREATE TABLE saas.invoices (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES saas.subscriptions(id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'paid',
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE saas.usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES saas.users(id),
    event_type VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO saas.plans (name, price_monthly, features) VALUES
('Free', 0, ARRAY['5 projects', '1 user']),
('Starter', 29, ARRAY['25 projects', '5 users']),
('Pro', 99, ARRAY['Unlimited projects', '25 users', 'API access']),
('Enterprise', 299, ARRAY['Unlimited everything', 'SSO', 'SLA']);

INSERT INTO saas.users (email, name, company, role, created_at, last_login)
SELECT 'user' || i || '@company' || (i % 20 + 1) || '.com', 'User ' || i,
    'Company ' || (i % 20 + 1), CASE WHEN i % 10 = 0 THEN 'admin' ELSE 'user' END,
    NOW() - (random() * 365 || ' days')::interval, NOW() - (random() * 30 || ' days')::interval
FROM generate_series(1, 150) AS s(i);

INSERT INTO saas.subscriptions (user_id, plan_id, status, started_at, cancelled_at, trial_ends_at)
SELECT u.id,
    CASE WHEN random() < 0.3 THEN 1 WHEN random() < 0.6 THEN 2 WHEN random() < 0.85 THEN 3 ELSE 4 END,
    CASE WHEN random() > 0.12 THEN 'active' WHEN random() > 0.5 THEN 'cancelled' ELSE 'trial' END,
    u.created_at,
    CASE WHEN random() < 0.12 THEN NOW() - (random() * 30 || ' days')::interval ELSE NULL END,
    CASE WHEN random() < 0.15 THEN NOW() + (random() * 14 || ' days')::interval ELSE NULL END
FROM saas.users u;

INSERT INTO saas.invoices (subscription_id, amount, status, period_start, period_end, created_at)
SELECT s.id, p.price_monthly,
    CASE WHEN random() > 0.03 THEN 'paid' ELSE 'failed' END,
    (NOW() - (m || ' months')::interval)::date, (NOW() - ((m-1) || ' months')::interval)::date,
    NOW() - (m || ' months')::interval
FROM saas.subscriptions s JOIN saas.plans p ON s.plan_id = p.id
CROSS JOIN generate_series(1, 6) AS months(m)
WHERE s.status = 'active' AND p.price_monthly > 0;

INSERT INTO saas.usage_events (user_id, event_type, metadata, created_at)
SELECT (random() * 149 + 1)::int,
    CASE (random() * 5)::int WHEN 0 THEN 'page_view' WHEN 1 THEN 'api_call' WHEN 2 THEN 'file_upload'
        WHEN 3 THEN 'report_generated' WHEN 4 THEN 'export' ELSE 'login' END,
    jsonb_build_object('source', CASE WHEN random() > 0.5 THEN 'web' ELSE 'api' END),
    NOW() - (random() * 30 || ' days')::interval
FROM generate_series(1, 2000);
