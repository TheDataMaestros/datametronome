-- Social Media Engagement / CRM Domain: contacts, campaigns, leads, activities, deals
CREATE SCHEMA IF NOT EXISTS social;

CREATE TABLE social.contacts (
    id SERIAL PRIMARY KEY, email VARCHAR(255), name VARCHAR(255),
    source VARCHAR(100), segment VARCHAR(100), created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE social.campaigns (
    id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, channel VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active', budget DECIMAL(10,2),
    start_date DATE, end_date DATE, created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE social.leads (
    id SERIAL PRIMARY KEY, contact_id INTEGER REFERENCES social.contacts(id),
    campaign_id INTEGER REFERENCES social.campaigns(id),
    status VARCHAR(50) DEFAULT 'new', score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(), converted_at TIMESTAMP
);

CREATE TABLE social.activities (
    id SERIAL PRIMARY KEY, contact_id INTEGER REFERENCES social.contacts(id),
    campaign_id INTEGER REFERENCES social.campaigns(id),
    activity_type VARCHAR(100), channel VARCHAR(50),
    engagement_value DECIMAL(10,2) DEFAULT 0, created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE social.deals (
    id SERIAL PRIMARY KEY, lead_id INTEGER REFERENCES social.leads(id),
    value DECIMAL(10,2), stage VARCHAR(50) DEFAULT 'qualification',
    close_probability DECIMAL(3,2), expected_close_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO social.contacts (email, name, source, segment, created_at)
SELECT 'contact' || i || '@' || CASE (i%5) WHEN 0 THEN 'gmail.com' WHEN 1 THEN 'company.com'
    WHEN 2 THEN 'outlook.com' WHEN 3 THEN 'business.co' ELSE 'mail.com' END,
    'Contact ' || i, CASE (i%4) WHEN 0 THEN 'instagram' WHEN 1 THEN 'twitter' WHEN 2 THEN 'linkedin' ELSE 'facebook' END,
    CASE (i%3) WHEN 0 THEN 'enterprise' WHEN 1 THEN 'smb' ELSE 'consumer' END,
    NOW() - (random() * 180 || ' days')::interval
FROM generate_series(1, 300) AS s(i);

INSERT INTO social.campaigns (name, channel, status, budget, start_date, end_date) VALUES
('Summer Product Launch', 'instagram', 'completed', 5000, '2026-01-15', '2026-02-15'),
('LinkedIn Thought Leadership', 'linkedin', 'active', 3000, '2026-02-01', '2026-04-01'),
('Twitter Brand Awareness', 'twitter', 'active', 2000, '2026-02-15', '2026-03-31'),
('Facebook Retargeting', 'facebook', 'active', 4000, '2026-03-01', '2026-03-31'),
('Instagram Stories Q1', 'instagram', 'active', 2500, '2026-01-01', '2026-03-31'),
('Email Newsletter March', 'email', 'active', 500, '2026-03-01', '2026-03-31'),
('Webinar Series', 'linkedin', 'planned', 1500, '2026-04-01', '2026-04-30'),
('TikTok Experiment', 'tiktok', 'active', 1000, '2026-03-01', '2026-03-15');

INSERT INTO social.leads (contact_id, campaign_id, status, score, created_at, converted_at)
SELECT (random()*299+1)::int, (random()*7+1)::int,
    CASE (random()*5)::int WHEN 0 THEN 'new' WHEN 1 THEN 'contacted' WHEN 2 THEN 'qualified' WHEN 3 THEN 'converted' ELSE 'lost' END,
    (random()*100)::int, NOW()-(random()*90||' days')::interval,
    CASE WHEN random()<0.08 THEN NOW()-(random()*30||' days')::interval ELSE NULL END
FROM generate_series(1, 400);

INSERT INTO social.activities (contact_id, campaign_id, activity_type, channel, engagement_value, created_at)
SELECT (random()*299+1)::int, (random()*7+1)::int,
    CASE (random()*7)::int WHEN 0 THEN 'like' WHEN 1 THEN 'comment' WHEN 2 THEN 'share'
        WHEN 3 THEN 'click' WHEN 4 THEN 'impression' WHEN 5 THEN 'email_open' ELSE 'form_submit' END,
    CASE (random()*4)::int WHEN 0 THEN 'instagram' WHEN 1 THEN 'twitter' WHEN 2 THEN 'linkedin' ELSE 'facebook' END,
    (random()*10)::numeric(10,2), NOW()-(random()*60||' days')::interval
FROM generate_series(1, 5000);

INSERT INTO social.deals (lead_id, value, stage, close_probability, expected_close_date, created_at)
SELECT l.id, (random()*50000+1000)::numeric(10,2),
    CASE (random()*4)::int WHEN 0 THEN 'qualification' WHEN 1 THEN 'proposal' WHEN 2 THEN 'negotiation'
        WHEN 3 THEN 'closed_won' ELSE 'closed_lost' END,
    (random()*0.8+0.1)::numeric(3,2), (NOW()+(random()*60||' days')::interval)::date, l.created_at
FROM social.leads l WHERE l.status IN ('qualified', 'converted') LIMIT 80;
