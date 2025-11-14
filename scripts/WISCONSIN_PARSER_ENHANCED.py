"""
Wisconsin WIAA HTML Parser - ENHANCED VERSION (Phase 1 Complete)

This is the replacement for parse_halftime_html_to_games() in wisconsin_wiaa.py

IMPROVEMENTS (Session 10 - Phase 1):
1. ✅ Self-game detection & skip
2. ✅ Duplicate game detection with seen_games set
3. ✅ Reset pending_teams at sectional/round boundaries
4. ✅ Enhanced round detection patterns
5. ✅ Score range validation
6. ✅ Improved debugging output

COPY THIS FUNCTION to replace parse_halftime_html_to_games() at line 225
"""

def parse_halftime_html_to_games(
    html_content: str,
    year: int,
    gender: str,
    division: int,
    sections: list[int],
    html_url: str,
    adapter,  # WisconsinWIAADataSource instance
    logger
) -> list:
    """
    Parse a WIAA Halftime HTML bracket page into Game objects.

    Session 8 - Phase 24: HTML bracket parsing for Wisconsin (PRIMARY METHOD).
    Session 10 - Phase 1: Enhanced with accuracy & quality improvements.

    **Improvements (Session 10)**:
    - Self-game detection: Skips team-vs-itself games
    - Duplicate detection: Tracks seen games to avoid duplicates
    - pending_teams reset: Clears at sectional/round boundaries
    - Enhanced round patterns: More variations for better matching
    - Score validation: Flags suspicious scores

    **Why HTML Parsing**:
    - HTML contains extractable text (no OCR needed)
    - Proven pattern across multiple years (2020-2025)
    - More reliable than PDF OCR
    - Faster processing

    **Expected HTML Structure** (extracted text):
    ```
    Sectional #1
    Thu, Mar 6
    7:00 PM
    #1 Almond-Bancroft
    #16 Elcho
    @Some High School
    64-52

    #8 School C
    #9 School D
    70-63
    ```

    **Parsing Strategy**:
    1. Extract text from HTML using BeautifulSoup
    2. Parse line by line tracking context (date, time, location, sectional)
    3. Match seed/team patterns: `#N Team Name`
    4. Match score patterns: `NN-NN`
    5. Build games with accumulated context
    6. Skip self-games, duplicates, invalid scores

    Args:
        html_content: Raw HTML content
        year: Tournament year
        gender: "Boys" or "Girls"
        division: Division number (1-5)
        sections: List of section numbers (e.g., [1, 2])
        html_url: Source HTML URL
        adapter: WisconsinWIAADataSource instance for create_data_source_metadata()
        logger: Logger instance

    Returns:
        List of Game objects
    """
    import re
    from ...models.game import Game, GameStatus, GameType
    from ...models.source import DataQualityFlag
    from ...utils.brackets import canonical_team_id

    games = []

    # Session 10 - Phase 1: Data quality tracking
    seen_games: set[tuple] = set()  # Deduplication
    quality_stats = {
        "skipped_self_games": 0,
        "skipped_duplicates": 0,
        "skipped_invalid_scores": 0,
    }

    try:
        # Extract text from HTML
        from ...utils.html_parser import parse_html
        soup = parse_html(html_content)
        text = soup.get_text("\n", strip=True)
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        if not lines:
            logger.warning(f"HTML contains no text", url=html_url)
            return []

        # Session 8 - Phase 24: Line-based parsing with context tracking
        # Session 10 - Phase 1: Enhanced with accuracy improvements

        # Context tracking
        current_sectional = sections[0] if sections else 1
        current_round = "Unknown Round"
        round_order = 0
        current_date = None
        current_time = None
        current_location = None
        pending_teams = []  # List of (seed, team_name) tuples

        # Regex patterns
        sectional_pattern = re.compile(r'Sectional\s+#?(\d+)', re.IGNORECASE)

        # Session 10 - Phase 1: Enhanced round patterns with more variations
        round_patterns = [
            # First Round variations
            (r'First\s+Round|Regional\s+Quarterfinals?', 'Regional Quarterfinal', 1),
            # Regional rounds
            (r'Regional\s+Semifinals?', 'Regional Semifinal', 2),
            (r'Regional\s+Finals?', 'Regional Final', 3),
            # Sectional rounds
            (r'Sectional\s+Semifinals?', 'Sectional Semifinal', 4),
            (r'Sectional\s+Finals?|Sectional\s+Championship', 'Sectional Final', 5),
            # State rounds
            (r'State\s+Quarterfinals?', 'State Quarterfinal', 6),
            (r'State\s+Semifinals?', 'State Semifinal', 7),
            (r'State\s+Championship|State\s+Finals?|State\s+Title', 'State Championship', 8),
        ]

        # Patterns for parsing
        seed_team_pattern = re.compile(r'^#(\d+)\s+(.+)$')
        score_pattern = re.compile(r'^(\d{1,3})-(\d{1,3})(?:\s*\((OT|2OT|3OT)\))?$')
        location_pattern = re.compile(r'^@(.+)$')
        time_pattern = re.compile(r'^\d{1,2}:\d{2}\s*(AM|PM)$', re.IGNORECASE)
        date_pattern = re.compile(r'^([A-Z][a-z]{2}),\s+([A-Z][a-z]{2})\s+(\d{1,2})$')

        for line in lines:
            # Check for sectional header
            m = sectional_pattern.search(line)
            if m:
                current_sectional = int(m.group(1))
                # Session 10 - Phase 1: Reset pending teams at sectional boundary
                pending_teams = []
                print(f"  [HTML PARSE] Sectional: {current_sectional}")
                continue

            # Check for round headers
            round_found = False
            for pattern, round_name, order in round_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    current_round = round_name
                    round_order = order
                    # Session 10 - Phase 1: Reset pending teams at round boundary
                    pending_teams = []
                    print(f"  [HTML PARSE] Round: {current_round}")
                    round_found = True
                    break

            if round_found:
                continue

            # Check for date
            m = date_pattern.match(line)
            if m:
                current_date = line
                continue

            # Check for time
            m = time_pattern.match(line)
            if m:
                current_time = line
                continue

            # Check for location
            m = location_pattern.match(line)
            if m:
                current_location = m.group(1).strip()
                continue

            # Check for seed + team
            m = seed_team_pattern.match(line)
            if m:
                seed = int(m.group(1))
                team_name = m.group(2).strip()
                pending_teams.append((seed, team_name))
                continue

            # Check for score
            m = score_pattern.match(line)
            if m and len(pending_teams) >= 2:
                # We have a score and at least 2 teams - create a game
                score_a = int(m.group(1))
                score_b = int(m.group(2))
                overtime = m.group(3) if m.group(3) else None

                # Get last two teams
                seed_a, team_a = pending_teams[-2]
                seed_b, team_b = pending_teams[-1]

                # Session 10 - Phase 1: Skip self-vs-self games
                if team_a == team_b:
                    logger.debug(
                        f"Skipping self-vs-self game",
                        team=team_a,
                        division=division,
                        sectional=current_sectional,
                        round=current_round,
                        score=f"{score_a}-{score_b}",
                    )
                    quality_stats["skipped_self_games"] += 1
                    pending_teams = []
                    continue

                # Session 10 - Phase 1: Validate score ranges
                if score_a > 150 or score_b > 150 or score_a < 0 or score_b < 0:
                    logger.warning(
                        f"Suspicious score range",
                        team_a=team_a,
                        team_b=team_b,
                        score=f"{score_a}-{score_b}",
                        division=division,
                        sectional=current_sectional,
                    )
                    quality_stats["skipped_invalid_scores"] += 1
                    pending_teams = []
                    continue

                # Create canonical team IDs
                team_a_id = canonical_team_id("wiaa", team_a)
                team_b_id = canonical_team_id("wiaa", team_b)

                # Session 10 - Phase 1: Duplicate detection
                game_key = (
                    division,
                    current_sectional,
                    round_order,
                    team_a_id,
                    team_b_id,
                    score_a,
                    score_b,
                )

                if game_key in seen_games:
                    logger.debug(
                        f"Skipping duplicate game",
                        division=division,
                        sectional=current_sectional,
                        round=current_round,
                        home=team_a,
                        away=team_b,
                        score=f"{score_a}-{score_b}",
                    )
                    quality_stats["skipped_duplicates"] += 1
                    pending_teams = []
                    continue

                seen_games.add(game_key)

                # Create game ID
                season_str = f"{year-1}-{str(year)[2:]}"
                game_id = f"wiaa_{year}_div{division}_sec{current_sectional}_{team_a_id.split('_', 1)[1]}_vs_{team_b_id.split('_', 1)[1]}"

                # Create Game object
                notes = f"Div{division} Sec{current_sectional} {current_round} | Seeds: #{seed_a} vs #{seed_b}"
                if overtime:
                    notes += f" | OT: {overtime}"
                if current_location:
                    notes += f" | @{current_location}"

                game = Game(
                    game_id=game_id,
                    home_team_id=team_a_id,
                    home_team_name=team_a,
                    away_team_id=team_b_id,
                    away_team_name=team_b,
                    home_score=score_a,
                    away_score=score_b,
                    status=GameStatus.FINAL,
                    game_type=GameType.PLAYOFF,
                    league=f"WIAA Division {division} {current_round}",
                    season=season_str,
                    round=current_round,
                    data_source=adapter.create_data_source_metadata(
                        url=html_url,
                        quality_flag=DataQualityFlag.VERIFIED,
                        notes=notes,
                    ),
                )
                games.append(game)

                print(f"    [GAME] #{seed_a} {team_a} {score_a} vs #{seed_b} {team_b} {score_b} ({current_round})")

                # Clear pending teams after creating game
                pending_teams = []

        # Session 10 - Phase 1: Enhanced logging with quality stats
        logger.info(
            f"Parsed Halftime HTML",
            games=len(games),
            division=division,
            sections=sections,
            skipped_self_games=quality_stats["skipped_self_games"],
            skipped_duplicates=quality_stats["skipped_duplicates"],
            skipped_invalid_scores=quality_stats["skipped_invalid_scores"],
        )

        if quality_stats["skipped_self_games"] > 0:
            logger.info(
                f"Quality: Prevented {quality_stats['skipped_self_games']} self-vs-self games"
            )
        if quality_stats["skipped_duplicates"] > 0:
            logger.info(
                f"Quality: Prevented {quality_stats['skipped_duplicates']} duplicate games"
            )

    except Exception as e:
        logger.error(f"Failed to parse HTML", url=html_url, error=str(e))
        import traceback
        traceback.print_exc()
        return []

    return games
