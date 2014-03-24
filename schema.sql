CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    toilet_id INTEGER NOT NULL,
    is_free BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO events (toilet_id, is_free) VALUES
    (0, 'yes'),
    (1, 'yes'),
    (2, 'yes');
