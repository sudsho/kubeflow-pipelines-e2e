-- label.sql
-- generate horizon-h forecast labels (units sold in the next h days per sku/store).
-- default horizon is 7 days.

DECLARE horizon_days INT64 DEFAULT 7;

SELECT
  store_id,
  sku_id,
  ds,
  SUM(units) OVER (
    PARTITION BY store_id, sku_id
    ORDER BY ds
    ROWS BETWEEN 1 FOLLOWING AND horizon_days FOLLOWING
  ) AS y_units_h7
FROM `{project}.retail_features.features_daily`;
