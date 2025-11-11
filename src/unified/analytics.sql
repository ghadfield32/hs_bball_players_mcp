-- SQL Analytics Helpers for Unified Dataset
--
-- These queries demonstrate common analytics patterns using the unified schema.
-- Run against the unified.duckdb database created by materialize_unified.py

-- ============================================================================
-- PLAYER-SEASON ROLLUPS (Categorical columns preserved)
-- ============================================================================

CREATE OR REPLACE TABLE mart_player_season AS
SELECT
  b.player_uid,
  g.season,
  c.circuit,
  c.level,
  c.gender,
  t.team_uid,
  t.team_name,
  -- Aggregate stats
  SUM(b.pts) AS pts,
  SUM(b.fgm) AS fgm,
  SUM(b.fga) AS fga,
  SUM(b.fg3m) AS fg3m,
  SUM(b.fg3a) AS fg3a,
  SUM(b.ftm) AS ftm,
  SUM(b.fta) AS fta,
  SUM(b.reb) AS reb,
  SUM(b.ast) AS ast,
  SUM(b.stl) AS stl,
  SUM(b.blk) AS blk,
  SUM(b.tov) AS tov,
  SUM(b.pf) AS pf,
  -- Per-game averages
  ROUND(AVG(b.pts), 1) AS ppg,
  ROUND(AVG(b.reb), 1) AS rpg,
  ROUND(AVG(b.ast), 1) AS apg,
  -- Shooting percentages
  ROUND(100.0 * SUM(b.fgm) / NULLIF(SUM(b.fga), 0), 1) AS fg_pct,
  ROUND(100.0 * SUM(b.fg3m) / NULLIF(SUM(b.fg3a), 0), 1) AS fg3_pct,
  ROUND(100.0 * SUM(b.ftm) / NULLIF(SUM(b.fta), 0), 1) AS ft_pct,
  -- Games played
  COUNT(DISTINCT b.game_uid) AS gp
FROM fact_box b
JOIN fact_game g ON b.game_uid = g.game_uid
JOIN dim_competition c ON g.competition_uid = c.competition_uid
JOIN dim_team t ON b.team_uid = t.team_uid
GROUP BY 1,2,3,4,5,6,7;


-- ============================================================================
-- CATEGORICAL ENCODINGS (for ML)
-- ============================================================================

CREATE OR REPLACE TABLE dim_categorical_codes AS
WITH cats AS (
  SELECT 'circuit' AS kind, circuit AS val FROM dim_competition
  UNION SELECT 'level', level FROM dim_competition
  UNION SELECT 'gender', gender FROM dim_competition
  UNION SELECT 'source_type', source_type FROM dim_source
  UNION SELECT 'org_type', org_type FROM dim_team
  UNION SELECT 'country', country FROM dim_source
)
SELECT
  kind,
  val,
  ROW_NUMBER() OVER (PARTITION BY kind ORDER BY val) AS code
FROM (SELECT DISTINCT kind, val FROM cats WHERE val IS NOT NULL);


-- ============================================================================
-- CROSS-SOURCE PLAYER TRACKING
-- ============================================================================

-- Find players who appear in multiple sources
CREATE OR REPLACE VIEW vw_cross_source_players AS
SELECT
  p.player_uid,
  COUNT(DISTINCT s.source_key) AS num_sources,
  STRING_AGG(DISTINCT s.source_key, ', ' ORDER BY s.source_key) AS sources,
  SUM(b.pts) AS total_pts,
  COUNT(DISTINCT b.game_uid) AS total_games
FROM fact_box b
JOIN dim_source s ON b.source_id = s.source_id
LEFT JOIN (
  -- Placeholder for player dimension (not built yet)
  SELECT DISTINCT player_uid FROM fact_box
) p ON b.player_uid = p.player_uid
GROUP BY p.player_uid
HAVING COUNT(DISTINCT s.source_key) > 1
ORDER BY num_sources DESC, total_pts DESC;


-- ============================================================================
-- CIRCUIT COMPARISON (HS/Grassroots circuits)
-- ============================================================================

-- Compare player performance across different circuits
CREATE OR REPLACE VIEW vw_circuit_comparison AS
SELECT
  c.circuit,
  c.level,
  c.gender,
  COUNT(DISTINCT b.player_uid) AS num_players,
  COUNT(DISTINCT b.game_uid) AS num_games,
  ROUND(AVG(b.pts), 1) AS avg_ppg,
  ROUND(AVG(b.reb), 1) AS avg_rpg,
  ROUND(AVG(b.ast), 1) AS avg_apg,
  ROUND(100.0 * SUM(b.fgm) / NULLIF(SUM(b.fga), 0), 1) AS avg_fg_pct
FROM fact_box b
JOIN fact_game g ON b.game_uid = g.game_uid
JOIN dim_competition c ON g.competition_uid = c.competition_uid
GROUP BY 1,2,3
ORDER BY c.circuit, c.level, c.gender;


-- ============================================================================
-- STATE COVERAGE ANALYSIS
-- ============================================================================

-- Analyze data coverage by state
CREATE OR REPLACE VIEW vw_state_coverage AS
SELECT
  s.state,
  s.country,
  COUNT(DISTINCT s.source_key) AS num_sources,
  STRING_AGG(DISTINCT s.source_key, ', ' ORDER BY s.source_key) AS sources,
  COUNT(DISTINCT t.team_uid) AS num_teams,
  COUNT(DISTINCT g.game_uid) AS num_games,
  COUNT(DISTINCT b.player_uid) AS num_players_with_stats
FROM dim_source s
LEFT JOIN dim_team t ON s.state = t.state
LEFT JOIN fact_game g ON s.source_id = g.source_id
LEFT JOIN fact_box b ON b.source_id = s.source_id
WHERE s.state IS NOT NULL
GROUP BY 1,2
ORDER BY num_games DESC;


-- ============================================================================
-- SEASON TRENDS
-- ============================================================================

-- Track metrics across seasons
CREATE OR REPLACE VIEW vw_season_trends AS
SELECT
  g.season,
  COUNT(DISTINCT g.game_uid) AS num_games,
  COUNT(DISTINCT b.player_uid) AS num_players,
  COUNT(DISTINCT t.team_uid) AS num_teams,
  ROUND(AVG(b.pts), 1) AS avg_ppg,
  ROUND(AVG(b.reb), 1) AS avg_rpg,
  ROUND(AVG(b.ast), 1) AS avg_apg,
  ROUND(100.0 * SUM(b.fg3m) / NULLIF(SUM(b.fg3a), 0), 1) AS three_pt_pct
FROM fact_game g
LEFT JOIN fact_box b ON g.game_uid = b.game_uid
LEFT JOIN dim_team t ON g.home_team_uid = t.team_uid OR g.away_team_uid = t.team_uid
GROUP BY 1
ORDER BY g.season DESC;


-- ============================================================================
-- TOP PERFORMERS (Multi-Circuit Leaderboard)
-- ============================================================================

-- Find top scorers across all circuits and levels
CREATE OR REPLACE VIEW vw_top_scorers AS
SELECT
  b.player_uid,
  c.circuit,
  c.level,
  c.gender,
  g.season,
  SUM(b.pts) AS total_pts,
  COUNT(DISTINCT b.game_uid) AS gp,
  ROUND(AVG(b.pts), 1) AS ppg
FROM fact_box b
JOIN fact_game g ON b.game_uid = g.game_uid
JOIN dim_competition c ON g.competition_uid = c.competition_uid
GROUP BY 1,2,3,4,5
HAVING gp >= 5  -- Minimum 5 games
ORDER BY ppg DESC
LIMIT 100;


-- ============================================================================
-- DATA QUALITY METRICS
-- ============================================================================

-- Check completeness of box score data
CREATE OR REPLACE VIEW vw_data_quality AS
SELECT
  s.source_key,
  s.source_type,
  COUNT(DISTINCT b.game_uid) AS games_with_boxes,
  COUNT(DISTINCT g.game_uid) AS total_games,
  ROUND(100.0 * COUNT(DISTINCT b.game_uid) / NULLIF(COUNT(DISTINCT g.game_uid), 0), 1) AS box_score_coverage_pct,
  -- Field completeness
  ROUND(100.0 * SUM(CASE WHEN b.pts IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS pts_completeness,
  ROUND(100.0 * SUM(CASE WHEN b.reb IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS reb_completeness,
  ROUND(100.0 * SUM(CASE WHEN b.ast IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS ast_completeness,
  ROUND(100.0 * SUM(CASE WHEN b.fgm IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS fg_completeness
FROM dim_source s
LEFT JOIN fact_game g ON s.source_id = g.source_id
LEFT JOIN fact_box b ON g.game_uid = b.game_uid
GROUP BY 1,2
ORDER BY games_with_boxes DESC;


-- ============================================================================
-- EXPORT QUERIES FOR ML PIPELINES
-- ============================================================================

-- Export feature matrix for player performance prediction
CREATE OR REPLACE VIEW vw_ml_features AS
SELECT
  ps.player_uid,
  ps.season,
  -- Categorical features (use dim_categorical_codes for encoding)
  ps.circuit,
  ps.level,
  ps.gender,
  -- Numeric features
  ps.gp,
  ps.ppg,
  ps.rpg,
  ps.apg,
  ps.fg_pct,
  ps.fg3_pct,
  ps.ft_pct,
  -- Team context
  t.org_type,
  t.country,
  t.state
FROM mart_player_season ps
JOIN dim_team t ON ps.team_uid = t.team_uid
WHERE ps.gp >= 5;  -- Filter for meaningful sample size


-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Find all EYBL players from 2024 season
-- SELECT * FROM mart_player_season WHERE circuit = 'EYBL' AND season = '2024';

-- Example 2: Compare girls vs boys performance in UAA
-- SELECT gender, AVG(ppg), AVG(rpg), AVG(apg)
-- FROM mart_player_season
-- WHERE circuit = 'UAA'
-- GROUP BY gender;

-- Example 3: Find players who played in multiple states
-- SELECT player_uid, COUNT(DISTINCT state) as num_states, STRING_AGG(DISTINCT state, ', ') as states
-- FROM mart_player_season ps
-- JOIN dim_team t ON ps.team_uid = t.team_uid
-- GROUP BY player_uid
-- HAVING COUNT(DISTINCT state) > 1;

-- Example 4: Export data for ML model training
-- COPY (SELECT * FROM vw_ml_features) TO 'data/exports/ml_features.parquet' (FORMAT PARQUET);
