CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    toilet_id INTEGER NOT NULL,
    is_free BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW latest_events AS
SELECT DISTINCT ON (toilet_id) * FROM events
ORDER BY toilet_id, recorded_at DESC;

CREATE VIEW visits AS SELECT * FROM (
  SELECT toilet_id, is_free, recorded_at, lead(recorded_at)
  OVER (PARTITION BY toilet_id ORDER BY recorded_at) - recorded_at AS duration
  FROM events
  ORDER BY recorded_at
) e
WHERE NOT is_free;

DROP FUNCTION all_are_free
CREATE FUNCTION all_are_free(timestamp default current_timestamp) RETURNS BOOLEAN AS $$
DECLARE
    all_free BOOLEAN;
BEGIN
    SELECT INTO all_free NOT EXISTS (
        SELECT 1 FROM latest_events WHERE NOT is_free AND recorded_at < $1
    );
    RETURN all_free;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION any_are_free
CREATE FUNCTION any_are_free(timestamp default current_timestamp) RETURNS BOOLEAN AS $$
DECLARE
    any_free BOOLEAN;
BEGIN
    SELECT INTO any_free EXISTS (
        SELECT 1 FROM latest_events WHERE is_free AND recorded_at < $1
    );
    RETURN any_free;
END;
$$ LANGUAGE plpgsql;
