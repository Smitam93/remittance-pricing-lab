-- SQLite syntax. One randomized quote per unique synthetic customer.
SELECT corridor, arm, split,
       COUNT(*) AS quotes,
       SUM(converted) AS transfers,
       AVG(converted * 1.0) AS conversion_rate,
       SUM(revenue_usd) AS revenue_usd,
       AVG(contribution_usd) AS contribution_per_quote_usd,
       AVG(price_pct) AS average_effective_price_pct
FROM quotes
GROUP BY corridor, arm, split
ORDER BY corridor, arm, split;
