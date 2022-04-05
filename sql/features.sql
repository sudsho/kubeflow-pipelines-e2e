-- features.sql
-- daily feature build for demand forecasting.
-- input: retail_raw.pos_daily (transactional daily rollup)
-- output: features table with lag / rolling window / calendar features.

WITH base AS (
  SELECT
    store_id,
    sku_id,
    DATE(sale_date) AS ds,
    SUM(units_sold) AS units,
    AVG(unit_price) AS avg_price,
    SUM(promo_flag)  AS promo_touches
  FROM `{project}.retail_raw.pos_daily`
  WHERE sale_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 730 DAY) AND CURRENT_DATE()
  GROUP BY store_id, sku_id, ds
),
lagged AS (
  SELECT
    b.*,
    LAG(units, 1) OVER w  AS units_lag_1,
    LAG(units, 7) OVER w  AS units_lag_7,
    LAG(units, 14) OVER w AS units_lag_14,
    LAG(units, 28) OVER w AS units_lag_28,
    AVG(units) OVER (
      PARTITION BY store_id, sku_id
      ORDER BY ds
      ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING
    ) AS units_ma_7,
    AVG(units) OVER (
      PARTITION BY store_id, sku_id
      ORDER BY ds
      ROWS BETWEEN 27 PRECEDING AND 1 PRECEDING
    ) AS units_ma_28
  FROM base b
  WINDOW w AS (PARTITION BY store_id, sku_id ORDER BY ds)
),
calendar AS (
  SELECT
    l.*,
    EXTRACT(DAYOFWEEK FROM ds) AS dow,
    EXTRACT(WEEK      FROM ds) AS week_of_year,
    EXTRACT(MONTH     FROM ds) AS month_of_year,
    CASE WHEN EXTRACT(DAYOFWEEK FROM ds) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend
  FROM lagged l
)
SELECT * FROM calendar
WHERE units_lag_28 IS NOT NULL;
