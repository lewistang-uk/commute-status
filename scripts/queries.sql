-- query the headways and wait times for the last 5 observations
WITH fby AS (
    SELECT 
        device_query_time,
        time_to_station,
        LAG(time_to_station) OVER (PARTITION BY device_query_time ORDER BY time_to_station) AS prev_tts
    FROM arrivals
    WHERE station = "FBY"
    AND NOT COALESCE(direction, "N/A") = "inbound"
)
SELECT
    CASE 
        WHEN COUNT(*) = 1 THEN NULL 
        ELSE ROUND(SUM(COALESCE(time_to_station-prev_tts, 0)) / (COUNT(*)-1), 1) 
    END AS avg_headway,
    CASE 
        WHEN COUNT(*) = 1 THEN "N/A" 
        ELSE ROUND(SUM(COALESCE((time_to_station-prev_tts) * (time_to_station-prev_tts), 0)) / (2*(SUM(COALESCE(time_to_station-prev_tts, 0)))), 1)
    END AS avg_wait_time
FROM fby
GROUP BY device_query_time
ORDER BY device_query_time DESC
LIMIT 5
;

-- query the headways and wait times for the last 5 days
WITH fby AS (
    SELECT 
        device_query_time,
        time_to_station,
        LAG(time_to_station) OVER (PARTITION BY device_query_time ORDER BY time_to_station) AS prev_tts
    FROM arrivals
    WHERE station = "FBY"
    AND NOT COALESCE(direction, "N/A") = "inbound"
),
kpis AS (
    SELECT
        CASE 
            WHEN COUNT(*) = 1 THEN NULL 
            ELSE ROUND(SUM(COALESCE(time_to_station-prev_tts, 0)) / (COUNT(*)-1), 1) 
        END AS avg_headway,
        CASE 
            WHEN COUNT(*) = 1 THEN "N/A" 
            ELSE ROUND(SUM(COALESCE((time_to_station-prev_tts) * (time_to_station-prev_tts), 0)) / (2*(SUM(COALESCE(time_to_station-prev_tts, 0)))), 1)
        END AS avg_wait_time,
        device_query_time
    FROM fby
    GROUP BY device_query_time
    ORDER BY device_query_time
)
SELECT 
    AVG(avg_headway),
    AVG(avg_wait_time)
FROM kpis
GROUP BY DATE(device_query_time)
ORDER BY DATE(device_query_time) DESC
LIMIT 5
;

