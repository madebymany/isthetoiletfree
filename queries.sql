# Visit durations
SELECT toilet_id, recorded_at, duration FROM visits
ORDER BY recorded_at DESC;

# Average duration per toilet
SELECT toilet_id, avg(duration) AS duration_avg FROM visits
GROUP BY toilet_id;

# Total duration per toilet
SELECT toilet_id, sum(duration) AS duration_total FROM visits
GROUP BY toilet_id;

# Minimum time spent per toilet
SELECT toilet_id, min(duration) AS duration_min FROM visits
GROUP BY toilet_id;

# Maximum time spent per toilet
SELECT toilet_id, max(duration) AS duration_max FROM visits
GROUP BY toilet_id;

# Number of visits per toilet
SELECT toilet_id, count(*) AS num_visits FROM visits
GROUP BY toilet_id;
