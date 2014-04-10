CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    toilet_id INTEGER NOT NULL,
    is_free BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE OR REPLACE FUNCTION latest_events(timestamp DEFAULT NULL)
RETURNS SETOF events AS $$
BEGIN
  IF $1 IS NULL THEN
      RETURN QUERY SELECT DISTINCT ON (toilet_id) * FROM events
      ORDER BY toilet_id, recorded_at DESC;
  ELSE
      RETURN QUERY SELECT DISTINCT ON (toilet_id) * FROM events
      WHERE recorded_at <= $1 ORDER BY toilet_id, recorded_at DESC;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION all_are_free(timestamp DEFAULT NULL)
RETURNS BOOLEAN AS $$
    SELECT TRUE = ALL (SELECT is_free FROM latest_events($1));
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION any_are_free(timestamp DEFAULT NULL)
RETURNS BOOLEAN AS $$
    SELECT TRUE = ANY (SELECT is_free FROM latest_events($1));
$$ LANGUAGE sql;
