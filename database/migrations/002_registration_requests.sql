-- Registration requests table
CREATE TABLE IF NOT EXISTS registration_requests (
    telegram_id BIGINT PRIMARY KEY,
    nickname VARCHAR(50) NOT NULL,
    full_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_registration_requests_status ON registration_requests(status);
