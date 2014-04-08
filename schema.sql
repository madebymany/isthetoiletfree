CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    toilet_id INTEGER NOT NULL,
    is_free BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP VIEW IF EXISTS latest_events;
CREATE VIEW latest_events AS
SELECT DISTINCT ON (toilet_id) * FROM events
ORDER BY toilet_id, recorded_at DESC;

DROP VIEW IF EXISTS visits_raw CASCADE;
CREATE VIEW visits_raw AS SELECT * FROM (
    SELECT toilet_id, is_free, recorded_at, lead(recorded_at)
    OVER (PARTITION BY toilet_id ORDER BY recorded_at) - recorded_at AS duration
    FROM events
    ORDER BY recorded_at
) e
WHERE NOT is_free;

DROP VIEW IF EXISTS visits;
CREATE VIEW visits AS SELECT toilet_id, is_free, recorded_at, duration FROM (
    SELECT *, percent_rank() OVER(ORDER BY duration) AS rank
    FROM visits_raw
) AS all_visits WHERE rank >= 0.02 AND rank <= 0.98
ORDER BY recorded_at;

DROP FUNCTION IF EXISTS all_are_free();
DROP FUNCTION IF EXISTS all_are_free(timestamp);
CREATE FUNCTION all_are_free(timestamp default current_timestamp)
RETURNS BOOLEAN AS $$
DECLARE
    all_free BOOLEAN;
BEGIN
    SELECT INTO all_free NOT EXISTS (
        SELECT 1 FROM latest_events WHERE NOT is_free AND recorded_at < $1
    );
    RETURN all_free;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS any_are_free();
DROP FUNCTION IF EXISTS any_are_free(timestamp);
CREATE FUNCTION any_are_free(timestamp default current_timestamp)
RETURNS BOOLEAN AS $$
DECLARE
    any_free BOOLEAN;
BEGIN
    SELECT INTO any_free EXISTS (
        SELECT 1 FROM latest_events WHERE is_free AND recorded_at < $1
    );
    RETURN any_free;
END;
$$ LANGUAGE plpgsql;
