import sqlite3
from datetime import datetime, timedelta
import random

def create_test_leagues():
    """Create test leagues with various configurations"""
    conn = sqlite3.connect('./SQLite/nba.db')
    cursor = conn.cursor()

    try:
        # Clean up existing test leagues
        cursor.execute("DELETE FROM PlayerLeague WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM PlayerTeam WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM PlayerAthlete WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM DraftOrder WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM PlayerSchedule WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM PlayerGame WHERE LID IN (88888888, 77777777, 66666666)")
        cursor.execute("DELETE FROM AthleteGame WHERE LID IN (88888888, 77777777, 66666666)")
        conn.commit()

        # Get or create test users
        cursor.execute("SELECT accountID FROM PlayerAccount WHERE username = 'admin'")
        admin_id = cursor.fetchone()[0]

        # Create additional test users
        for i in range(1, 5):
            username = f"user{i}"
            email = f"user{i}@test.com"
            cursor.execute(
                "INSERT OR IGNORE INTO PlayerAccount (username, email, password) VALUES (?, ?, ?)",
                (username, email, "password123")
            )
        conn.commit()

        # Get test user IDs
        cursor.execute("SELECT accountID FROM PlayerAccount WHERE username IN ('user1', 'user2', 'user3', 'user4')")
        user_ids = [row[0] for row in cursor.fetchall()]

        # Get available NBA players
        cursor.execute("SELECT PID FROM NBAPlayer LIMIT 100")
        nba_players = [row[0] for row in cursor.fetchall()]
        random.shuffle(nba_players)

        # ===== LEAGUE 1: Post-Draft (status='game', 5 teams, 10 players per team, no scores yet) =====
        create_post_draft_league(cursor, league_id=88888888, owner_id=admin_id,
                               team_owners=[admin_id] + user_ids[:3],
                               nba_players=nba_players[:40])

        # ===== LEAGUE 2: In-Game with Scores (status='game', current_day=2, scores calculated) =====
        create_in_game_league(cursor, league_id=77777777, owner_id=user_ids[0],
                            team_owners=[user_ids[0]] + user_ids[1:],
                            nba_players=nba_players[40:80])

        conn.commit()
        print("Test leagues created successfully!")

    except Exception as e:
        print(f"Error creating test leagues: {e}")
        conn.rollback()
    finally:
        conn.close()


def create_post_draft_league(cursor, league_id, owner_id, team_owners, nba_players):
    """Create a league that just finished draft with no games played"""
    # Create league
    cursor.execute(
        "INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status, current_day) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (league_id, "Post-Draft League", "snake", owner_id, "game", 1)
    )

    # Create teams and assign owners
    team_ids = []
    for i, owner_id_val in enumerate(team_owners):
        try:
            cursor.execute(
                "INSERT INTO PlayerTeam (LID, accountID, teamName) "
                "VALUES (?, ?, ?)",
                (league_id, owner_id_val, f"Team {i+1}")
            )
            # Use a different approach to get the inserted team ID
            cursor.execute(
                "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ? AND teamName = ?",
                (league_id, owner_id_val, f"Team {i+1}")
            )
            team_result = cursor.fetchone()
            if team_result:
                team_ids.append(team_result[0])
        except Exception as e:
            print(f"Error creating team {i+1}: {e}")

    # Assign draft order
    for i, team_id in enumerate(team_ids):
        cursor.execute(
            "INSERT INTO DraftOrder (LID, teamID, pickOrder) VALUES (?, ?, ?)",
            (league_id, team_id, i + 1)
        )

    # Assign 10 players per team (5 active, 5 bench)
    player_idx = 0
    for team_id in team_ids:
        for j in range(10):
            if player_idx < len(nba_players):
                active = 1 if j < 5 else 0
                cursor.execute(
                    "INSERT INTO PlayerAthlete (LID, PID, teamID, active) "
                    "VALUES (?, ?, ?, ?)",
                    (league_id, nba_players[player_idx], team_id, active)
                )
                player_idx += 1

    # Generate round-robin schedule
    generate_round_robin_schedule(cursor, league_id, team_ids)


def create_in_game_league(cursor, league_id, owner_id, team_owners, nba_players):
    """Create a league in game phase with scores already calculated"""
    # Create league
    cursor.execute(
        "INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status, current_day) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (league_id, "In-Game League with Scores", "standard", owner_id, "game", 2)
    )

    # Create teams
    team_ids = []
    for i, owner_id_val in enumerate(team_owners):
        try:
            cursor.execute(
                "INSERT INTO PlayerTeam (LID, accountID, teamName) "
                "VALUES (?, ?, ?)",
                (league_id, owner_id_val, f"Squad {i+1}")
            )
            # Use a different approach to get the inserted team ID
            cursor.execute(
                "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ? AND teamName = ?",
                (league_id, owner_id_val, f"Squad {i+1}")
            )
            team_result = cursor.fetchone()
            if team_result:
                team_ids.append(team_result[0])
        except Exception as e:
            print(f"Error creating team {i+1}: {e}")

    # Assign draft order
    for i, team_id in enumerate(team_ids):
        cursor.execute(
            "INSERT INTO DraftOrder (LID, teamID, pickOrder) VALUES (?, ?, ?)",
            (league_id, team_id, i + 1)
        )

    # Assign 10 players per team
    player_idx = 0
    for team_id in team_ids:
        for j in range(10):
            if player_idx < len(nba_players):
                active = 1 if j < 5 else 0
                cursor.execute(
                    "INSERT INTO PlayerAthlete (LID, PID, teamID, active) "
                    "VALUES (?, ?, ?, ?)",
                    (league_id, nba_players[player_idx], team_id, active)
                )
                player_idx += 1

    # Generate round-robin schedule
    generate_round_robin_schedule(cursor, league_id, team_ids)

    # Add scores for day 1
    add_sample_scores(cursor, league_id, day=1)


def generate_round_robin_schedule(cursor, league_id, team_ids):
    """Generate round-robin schedule"""
    teams = team_ids[:]
    num_teams = len(teams)

    if num_teams < 2:
        return

    matchup_id = 1
    week = 1

    # Add bye if odd number of teams
    if num_teams % 2 == 1:
        teams.append(None)
        num_teams = num_teams + 1

    # Generate matchups
    for round_num in range((num_teams - 1) * 2):  # Double round-robin: (n-1) * 2 rounds
        for i in range(num_teams // 2):
            team1 = teams[i]
            team2 = teams[num_teams - 1 - i]

            if team1 is not None and team2 is not None:
                cursor.execute(
                    "INSERT INTO PlayerSchedule (matchupID, LID, week, T1, T2) VALUES (?, ?, ?, ?, ?)",
                    (matchup_id, league_id, week, team1, team2)
                )
                matchup_id += 1

        week += 1

        # Rotate teams for next round
        if round_num < (num_teams - 1) * 2 - 1:
            teams = [teams[0]] + teams[-1:] + teams[1:-1]


def add_sample_scores(cursor, league_id, day):
    """Add sample fantasy scores for a given day"""
    # Get games for this day
    cursor.execute(
        "SELECT matchupID, T1, T2 FROM PlayerSchedule WHERE LID = ? AND week = ?",
        (league_id, day)
    )
    games = cursor.fetchall()

    for matchup_id, team1_id, team2_id in games:
        # Add sample scores for each team
        team1_score = round(random.uniform(80, 150), 2)
        team2_score = round(random.uniform(80, 150), 2)

        cursor.execute(
            "INSERT OR REPLACE INTO PlayerGame (LID, matchupID, day, teamID, Score) "
            "VALUES (?, ?, ?, ?, ?)",
            (league_id, matchup_id, str(day), team1_id, team1_score)
        )
        cursor.execute(
            "INSERT OR REPLACE INTO PlayerGame (LID, matchupID, day, teamID, Score) "
            "VALUES (?, ?, ?, ?, ?)",
            (league_id, matchup_id, str(day), team2_id, team2_score)
        )

        # Add sample player scores
        cursor.execute(
            "SELECT pa.PID, pa.active FROM PlayerAthlete pa WHERE pa.LID = ? AND pa.teamID = ?",
            (league_id, team1_id)
        )
        players_team1 = cursor.fetchall()

        for pid, active in players_team1:
            player_score = round(random.uniform(5, 50), 2)
            cursor.execute(
                "INSERT OR REPLACE INTO AthleteGame (LID, matchupID, day, PID, playerScore, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (league_id, matchup_id, str(day), pid, player_score, "active" if active else "bench")
            )

        cursor.execute(
            "SELECT pa.PID, pa.active FROM PlayerAthlete pa WHERE pa.LID = ? AND pa.teamID = ?",
            (league_id, team2_id)
        )
        players_team2 = cursor.fetchall()

        for pid, active in players_team2:
            player_score = round(random.uniform(5, 50), 2)
            cursor.execute(
                "INSERT OR REPLACE INTO AthleteGame (LID, matchupID, day, PID, playerScore, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (league_id, matchup_id, str(day), pid, player_score, "active" if active else "bench")
            )


def create_scenario_leagues():
    """Create 3 scenario leagues (10 teams each):
      11111111 – Hoops Dynasty      : pre-draft  (teams joined, draft not started)
      22222222 – Final Pick League  : mid-draft  (99/100 picks done, last team needs 1 more)
      33333333 – Season Opener      : day-1 game (all 100 picks done, season just started)
    """
    conn = sqlite3.connect('./SQLite/nba.db')
    cursor = conn.cursor()

    try:
        # ── Clean up any prior run ──────────────────────────────────────────────
        for lid in (11111111, 22222222, 33333333):
            cursor.execute("DELETE FROM AthleteGame    WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM PlayerGame     WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM PlayerSchedule WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM PlayerAthlete  WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM DraftOrder     WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM PlayerTeam     WHERE LID = ?", (lid,))
            cursor.execute("DELETE FROM PlayerLeague   WHERE LID = ?", (lid,))
        conn.commit()

        # ── 10 shared users across all 3 leagues ───────────────────────────────
        team_names = [
            ("team01_nba", "team01@nba.test", "password123", "Airball Avengers"),
            ("team02_nba", "team02@nba.test", "password123", "Bucket Brigade"),
            ("team03_nba", "team03@nba.test", "password123", "Court Jesters"),
            ("team04_nba", "team04@nba.test", "password123", "Dunk Dynasty"),
            ("team05_nba", "team05@nba.test", "password123", "Elbow Elites"),
            ("team06_nba", "team06@nba.test", "password123", "Fast Break FC"),
            ("team07_nba", "team07@nba.test", "password123", "Glass Eaters"),
            ("team08_nba", "team08@nba.test", "password123", "Hardwood Heroes"),
            ("team09_nba", "team09@nba.test", "password123", "Iso Kings"),
            ("team10_nba", "team10@nba.test", "password123", "Jump Ball Giants"),
        ]

        for username, email, password, _ in team_names:
            cursor.execute(
                "INSERT OR IGNORE INTO PlayerAccount (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
        conn.commit()

        def get_uid(username):
            cursor.execute("SELECT accountID FROM PlayerAccount WHERE username = ?", (username,))
            return cursor.fetchone()[0]

        user_ids = [get_uid(row[0]) for row in team_names]
        fantasy_team_names = [row[3] for row in team_names]

        # ── Grab NBA player pools (non-overlapping blocks of 100) ──────────────
        cursor.execute("SELECT PID FROM NBAPlayer ORDER BY PID")
        all_pids = [row[0] for row in cursor.fetchall()]
        pool_draft = all_pids[0:100]    # for league 2 (99 picks)
        pool_game  = all_pids[100:200]  # for league 3 (100 picks)

        # ─────────────────────────────────────────────────────────────────────
        # LEAGUE 1 : Pre-draft — teams joined, no draft order set
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute(
            "INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status, current_day) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (11111111, "Hoops Dynasty", "snake", user_ids[0], "initial", 0)
        )
        for i, uid in enumerate(user_ids):
            cursor.execute(
                "INSERT INTO PlayerTeam (LID, accountID, teamName) VALUES (?, ?, ?)",
                (11111111, uid, fantasy_team_names[i])
            )
        # No DraftOrder — owner hasn't pressed "Start Draft" yet

        # ─────────────────────────────────────────────────────────────────────
        # LEAGUE 2 : Mid-draft — 99 of 100 picks done (snake, 10 teams)
        #   Snake pick sequence with 10 teams:
        #     R1 (odd)  : po1..po10
        #     R2 (even) : po10..po1
        #     … 10 rounds total; last pick (#100) belongs to po1
        #   After 99 picks: po1 has 9 players, everyone else has 10.
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute(
            "INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status, current_day) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (22222222, "Final Pick League", "snake", user_ids[0], "started", 0)
        )

        l2_team_ids = []
        for i, uid in enumerate(user_ids):
            cursor.execute(
                "INSERT INTO PlayerTeam (LID, accountID, teamName) VALUES (?, ?, ?)",
                (22222222, uid, fantasy_team_names[i])
            )
            cursor.execute(
                "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ? AND teamName = ?",
                (22222222, uid, fantasy_team_names[i])
            )
            l2_team_ids.append(cursor.fetchone()[0])

        num_teams = len(l2_team_ids)
        # DraftOrder: team_ids[0] → pickOrder 1, …, team_ids[9] → pickOrder 10
        for i, tid in enumerate(l2_team_ids):
            cursor.execute(
                "INSERT INTO DraftOrder (LID, teamID, pickOrder) VALUES (?, ?, ?)",
                (22222222, tid, i + 1)
            )
        po_to_tid = {i + 1: l2_team_ids[i] for i in range(num_teams)}

        # Simulate 99 picks using the same logic as get_current_draft_turn
        for pick_num in range(99):
            current_round  = (pick_num // num_teams) + 1
            pick_in_round  = (pick_num % num_teams) + 1
            # Snake: reverse pick order on even rounds
            if current_round % 2 == 0:
                target_po = num_teams - pick_in_round + 1
            else:
                target_po = pick_in_round
            tid = po_to_tid[target_po]
            pid = pool_draft[pick_num]
            # active=0 during draft (set_active is called after draft completes)
            cursor.execute(
                "INSERT INTO PlayerAthlete (LID, PID, teamID, active) VALUES (?, ?, ?, ?)",
                (22222222, pid, tid, 0)
            )

        # ─────────────────────────────────────────────────────────────────────
        # LEAGUE 3 : Day-1 game — all 100 picks done, season just started
        # ─────────────────────────────────────────────────────────────────────
        cursor.execute(
            "INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status, current_day) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (33333333, "Season Opener", "standard", user_ids[0], "game", 1)
        )

        l3_team_ids = []
        for i, uid in enumerate(user_ids):
            cursor.execute(
                "INSERT INTO PlayerTeam (LID, accountID, teamName) VALUES (?, ?, ?)",
                (33333333, uid, fantasy_team_names[i])
            )
            cursor.execute(
                "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ? AND teamName = ?",
                (33333333, uid, fantasy_team_names[i])
            )
            l3_team_ids.append(cursor.fetchone()[0])

        for i, tid in enumerate(l3_team_ids):
            cursor.execute(
                "INSERT INTO DraftOrder (LID, teamID, pickOrder) VALUES (?, ?, ?)",
                (33333333, tid, i + 1)
            )

        # 10 players per team — first 5 active, last 5 bench
        player_idx = 0
        for tid in l3_team_ids:
            for j in range(10):
                active = 1 if j < 5 else 0
                cursor.execute(
                    "INSERT INTO PlayerAthlete (LID, PID, teamID, active) VALUES (?, ?, ?, ?)",
                    (33333333, pool_game[player_idx], tid, active)
                )
                player_idx += 1

        # Round-robin schedule (uses the same helper already in this file)
        generate_round_robin_schedule(cursor, 33333333, l3_team_ids)
        # No scores yet — day 1, no games advanced

        conn.commit()
        print("Scenario leagues created successfully!")
        print()
        print("  11111111 – Hoops Dynasty      (pre-draft, 10 teams joined)")
        print("  22222222 – Final Pick League   (draft: 99/100 picks done, po1 picks next)")
        print("  33333333 – Season Opener       (game phase, day 1, no scores yet)")
        print()
        print("Users (shared across all 3 leagues):")
        for row in team_names:
            print(f"  username: {row[0]:15s}  password: {row[2]}")

    except Exception as e:
        print(f"Error creating scenario leagues: {e}")
        import traceback; traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_test_leagues()
    create_scenario_leagues()