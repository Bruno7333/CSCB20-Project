from flask import Flask, request, redirect, url_for, render_template, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'lebron-james-king-of-basketball'
DB_FILE = "./SQLite/nba.db"
leagues = ()


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""INSERT OR IGNORE INTO PlayerAccount (username, email, password)
                        VALUES (?, ?, ?)""",
                   ("admin", "admin@nba.com", "secret123"))

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

# league load function
@app.route("/league/<int:league_id>")
def league(league_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """SELECT LID as id, leagueName, status, ownerAccount, draftType, current_day
            FROM PlayerLeague
            WHERE LID = ?""",
        (league_id,)
        )
    league_data = cursor.fetchone()
    cursor.execute(
        """SELECT pt.teamID, pt.teamName as team_name, pa.username as name
            FROM PlayerTeam pt
            JOIN PlayerAccount pa on pt.accountID = pa.accountID
            WHERE pt.LID = ?""",
        (league_id,)
        )
    members = cursor.fetchall()

    # Draft Turn Logic
    current_turn_team_id = None
    if league_data and league_data['status'] == 'started':
        current_turn_team_id = get_current_draft_turn(cursor, league_id)
        if current_turn_team_id is None and league_data['status'] != 'final':
            conn.commit() # Status was updated to final inside get_current_draft_turn

    # Get games for game phase
    games = []
    nba_games = []
    current_day = None
    viewed_day = None
    max_day = None
    if league_data and league_data['status'] == 'game':
        current_day = league_data['current_day']
        viewed_day = request.args.get('day', current_day, type=int)

        # Get max day available
        cursor.execute(
            "SELECT MAX(week) FROM PlayerSchedule WHERE LID = ?",
            (league_id,)
        )
        result = cursor.fetchone()
        max_day = result[0] if result[0] else current_day

        # Clamp viewed_day between 1 and max_day
        viewed_day = max(1, min(viewed_day, max_day))

        cursor.execute(
            """SELECT ps.matchupID, ps.week, ps.T1, ps.T2,
                      pt1.teamName as team1_name, pt2.teamName as team2_name,
                      pg1.Score as team1_score, pg2.Score as team2_score
               FROM PlayerSchedule ps
               LEFT JOIN PlayerTeam pt1 ON ps.T1 = pt1.teamID
               LEFT JOIN PlayerTeam pt2 ON ps.T2 = pt2.teamID
               LEFT JOIN PlayerGame pg1 ON ps.LID = pg1.LID AND ps.matchupID = pg1.matchupID AND ps.T1 = pg1.teamID
               LEFT JOIN PlayerGame pg2 ON ps.LID = pg2.LID AND ps.matchupID = pg2.matchupID AND ps.T2 = pg2.teamID
               WHERE ps.LID = ? AND ps.week = ?
               ORDER BY ps.matchupID""",
            (league_id, viewed_day)
        )
        games = cursor.fetchall()

        # Get NBA games for this day (based on day offset from first NBA game)
        cursor.execute("SELECT MIN(date) FROM NBASchedule")
        first_nba_date_result = cursor.fetchone()
        nba_games = []
        if first_nba_date_result and first_nba_date_result[0]:
            from datetime import datetime, timedelta
            date_str = first_nba_date_result[0].split()[0] if ' ' in first_nba_date_result[0] else first_nba_date_result[0]
            first_nba_date = datetime.strptime(date_str, '%Y-%m-%d')
            nba_date = first_nba_date + timedelta(days=viewed_day - 1)
            nba_date_str = nba_date.strftime('%Y-%m-%d')

            cursor.execute(
                """SELECT nt1.teamname as home_team, nt2.teamname as away_team
                   FROM NBASchedule ns
                   LEFT JOIN NBATeam nt1 ON ns.home = nt1.TID
                   LEFT JOIN NBATeam nt2 ON ns.away = nt2.TID
                   WHERE date(ns.date) = ?
                   ORDER BY ns.GID""",
                (nba_date_str,)
            )
            nba_games = cursor.fetchall()

    search = request.args.get('search', '')
    positions = request.args.getlist('position')

    query = "SELECT * FROM NBAPlayer WHERE playerName Like ?"
    search_parameter = '%' + search + '%'
    params = [search_parameter]

    if positions:
        position_clauses = "position LIKE ?"
        params.append('%' + positions[0] + '%')
        for p in positions[1:]:
            position_clauses += "Or position LIKE ?"
            params.append('%' + p + '%')
        query += " AND (" + position_clauses + ")"

    query += "ORDER BY prevPlayerScore DESC"

    cursor.execute(query, params)
    player_list = cursor.fetchall()[:10]

    conn.close()

    if league_data is None:
        return redirect(url_for('dashboard'))

    return render_template("league.html", league=league_data, members=members,
                           player_list=player_list, current_turn=current_turn_team_id, games=games,
                           current_day=current_day, viewed_day=viewed_day, max_day=max_day, nba_games=nba_games)

@app.route("/start_league/<int:league_id>", methods=['POST'])
def start_league(league_id):
    owner_id = session.get('user_id')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Verify ownership before starting
    cursor.execute(
        "SELECT 1 FROM PlayerLeague WHERE LID = ? AND ownerAccount = ?",
        (league_id, owner_id)
    )

    if cursor.fetchone():
        # get teams
        cursor.execute("SELECT teamID FROM PlayerTeam WHERE LID = ?", (league_id,))
        teams_data = cursor.fetchall()
        teams = []
        for team in teams_data:
            teams.append(team[0])

        # randomize
        random.shuffle(teams)

        # Save to table
        for index, team_id in enumerate(teams):
            cursor.execute(
                "INSERT INTO DraftOrder (LID, teamID, pickOrder) VALUES (?, ?, ?)",
                (league_id, team_id, index + 1)
            )

        cursor.execute(
            "UPDATE PlayerLeague SET status = 'started' WHERE LID = ?",
            (league_id,)
        )
        conn.commit()

    conn.close()
    return redirect(url_for('league', league_id=league_id))

@app.route("/advance_day/<int:league_id>", methods=['POST'])
def advance_day(league_id):
    owner_id = session.get('user_id')

    if not owner_id:
        return redirect(url_for('login_page'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Verify owner
    cursor.execute(
        "SELECT current_day FROM PlayerLeague WHERE LID = ? AND ownerAccount = ? AND status = 'game'",
        (league_id, owner_id)
    )
    result = cursor.fetchone()

    if result:
        current_day = result[0]

        # Calculate scores for current day before advancing
        calculate_day_scores(cursor, league_id, current_day)

        # Check if there are games on the next day
        cursor.execute(
            "SELECT COUNT(*) FROM PlayerSchedule WHERE LID = ? AND week = ?",
            (league_id, current_day + 1)
        )
        if cursor.fetchone()[0] > 0:
            cursor.execute(
                "UPDATE PlayerLeague SET current_day = ? WHERE LID = ?",
                (current_day + 1, league_id)
            )

        conn.commit()

    conn.close()
    return redirect(url_for('league', league_id=league_id))

# Dashboard load function
@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # select leagues
    cursor.execute(
        """SELECT pl.LID, pl.leagueName
            FROM PlayerLeague pl
            JOIN PlayerTeam pt ON pl.LID = pt.LID
            WHERE pt.accountID = ?""",
        (session.get('user_id'),)
        )
    leagues_data = cursor.fetchall()

    leagues = []
    for league in leagues_data:
        leagues.append({
            'id': league[0],
            'name': league[1]
        })

    conn.close()

    return render_template('dashboard.html', leagues=leagues)

# create league function
@app.route('/create_league', methods=['POST'])
def create_league():
    league_name = request.form['leagueName']
    draft_type = request.form['draftType']
    owner_id = session.get('user_id')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    while True:
        new_id = random.randint(10000000, 99999999)
        cursor.execute("""SELECT 1
                            FROM PlayerLeague
                            WHERE LID = ?""", (new_id,))
        if not cursor.fetchone():
            new_league_id = new_id
            break

    # check if user is in more than 6 leagues
    cursor.execute("""SELECT COUNT(*)
                        FROM Playerteam
                        WHERE accountID = ?""", (owner_id,))
    count = cursor.fetchone()[0]

    if count >= 6:
        conn.close()

        return redirect(url_for('dashboard'))

    cursor.execute(
        """INSERT INTO PlayerLeague (LID, leagueName, draftType, ownerAccount, status)
            VALUES (?, ?, ?, ?, 'initial')""",
        (new_league_id, league_name, draft_type, owner_id)
    )

    cursor.execute(
        """INSERT INTO PlayerTeam (LID, accountID, teamName)
            VALUES (?, ?, ?)""",
        (new_league_id, owner_id, "My Team")
    )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# Join league function
@app.route('/join_league', methods=['POST'])
def Join_league():
    league_id = request.form['leagueID']
    user_id = session.get('user_id')

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()


    cursor.execute(
        "INSERT INTO PlayerTeam (LID, accountID, teamName) VALUES (?, ?, ?)",
        (league_id, user_id, "My Team")
    )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# register function
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""INSERT INTO PlayerAccount (username, email, password)
                    VALUES (?, ?, ?)""",
                   (username, email, password))

    conn.commit()
    conn.close()
    return redirect('/')

# login function
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Use PlayerAccount table SAFE :)
    query = """SELECT * FROM PlayerAccount
                WHERE username = ? AND password = ?"""

    cursor.execute(query, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user_id'] = user['accountID']
        return redirect(url_for('dashboard'))
    else:
        return "Login failed. Check your credentials."

@app.route('/team/<int:league_id>')
def team(league_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    user_id = session.get("user_id")

    query = """SELECT nba.playerName, nba.position, nba.PID, pa.active
            FROM NBAPlayer nba
            JOIN PlayerAthlete pa
            ON nba.PID = pa.PID
            WHERE pa.teamID = (
                SELECT teamID
                FROM PlayerTeam
                WHERE LID = ?
                AND accountID = ?
            )
            AND pa.LID = ?
                """
    cursor.execute(query, (league_id, user_id, league_id))
    players_data = cursor.fetchall()

    players = []
    for player in players_data:
        players.append({
            'playerName': player[0],
            'position': player[1],
            'PID': player[2]
        })

    conn.close()
    return render_template("team.html", players=players, league_id=league_id)

@app.route('/set_active/<int:league_id>', methods=['POST'])
def set_active(league_id):
    user_id = session.get('user_id')
    active_pids = request.form.getlist('active_pid')

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    single_pos = []
    multi_pos = []

    for pid in active_pids:
        query ="SELECT position FROM NBAPlayer WHERE PID = ?"
        cursor.execute(query, (pid,))
        position = cursor.fetchone()[0]
        if '/' in position:
            multi_pos.append((pid, position.split('/')))
        else:
            single_pos.append((pid, position))
    
    slots = {'F': 2, 'G': 2, 'C':1}
    for pid, pos in single_pos:
        if slots[pos] > 0:
            slots[pos] -= 1
        else:
            conn.close()
            return redirect(url_for('team', league_id=league_id))
    
    for pid, positions in multi_pos:
        assigned = False
        for pos in positions:
            if slots[pos] > 0:
                slots[pos] -= 1
                assigned = True
                break
        if not assigned:
            conn.close()
            return redirect(url_for('team', league_id=league_id))
        
    query = "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ?"
    cursor.execute(query, (league_id, user_id))
    my_team_id = cursor.fetchone()[0]
    
    query = "UPDATE PlayerAthlete SET active = 0 WHERE teamID = ? AND LID = ?"
    cursor.execute(query, (my_team_id, league_id))

    query = "UPDATE PlayerAthlete SET active = 1 WHERE PID = ? AND LID = ?"
    for pid in active_pids:
        cursor.execute(query, (pid, league_id))

    conn.commit()
    conn.close()
    return redirect(url_for('team', league_id=league_id))

        


@app.route("/player/<int:player_id>")
def player_details(player_id):
    league_id = request.args.get('league_id', type=int)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get player info
    cursor.execute("""
        SELECT p.playerName, p.position, t.teamname, p.prevPlayerScore, p.PID,
               pt.teamName, pl.leagueName
        FROM NBAPlayer p
        LEFT JOIN NBATeam t ON p.TID = t.TID
        LEFT JOIN PlayerAthlete pa ON p.PID = pa.PID
        LEFT JOIN PlayerTeam pt ON pa.teamID = pt.teamID
        LEFT JOIN PlayerLeague pl ON pa.LID = pl.LID
        WHERE p.PID = ?
    """, (player_id,))
    player_data = cursor.fetchone()

    # Get stats
    cursor.execute("SELECT * FROM NBAPlayerSeasonStats WHERE PID = ?", (player_id,))
    stats = cursor.fetchone()

    # Draft eligibility check
    can_draft = False
    cannot_draft_reason = None
    user_team_id = None

    if league_id:
        user_id = session.get('user_id')

        # Check if player is already drafted
        cursor.execute("SELECT teamID FROM PlayerAthlete WHERE PID = ? AND LID = ?", (player_id, league_id))
        if cursor.fetchone():
            cannot_draft_reason = "Player already drafted"
        else:
            # Check if user turn
            current_turn_team_id = get_current_draft_turn(cursor, league_id)

            if current_turn_team_id is None:
                cannot_draft_reason = "Draft is not active or has ended"
            else:
                # Get TID
                cursor.execute(
                    "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ?",
                    (league_id, user_id)
                )
                user_team = cursor.fetchone()
                if user_team:
                    user_team_id = user_team[0]
                    if user_team_id == current_turn_team_id:
                        can_draft = True
                    else:
                        cannot_draft_reason = "It's not your turn to draft"
                else:
                    cannot_draft_reason = "You are not in this league"

    conn.close()

    player = {
        'playerName': player_data[0] if player_data else None,
        'position': player_data[1] if player_data else None,
        'teamname': player_data[2] if player_data else None,
        'prevPlayerScore': player_data[3] if player_data else None,
        'PID': player_data[4] if player_data else None,
        'fantasy_team': player_data[5] if player_data else None,
        'leagueName': player_data[6] if player_data else None
    }

    return render_template("player_details.html", player=player, stats=stats,
                         league_id=league_id, can_draft=can_draft,
                         cannot_draft_reason=cannot_draft_reason, user_team_id=user_team_id)


@app.route('/trade/<int:league_id>', methods=['GET', 'POST'])
def trade(league_id):
    # choose either looking at trades you can make or the trades that you have which are pending
    # show a list of the players on your team on one side,
    # the players available for trade on the other side,
    # allow functionality for choosing which player you want to trade and trade for
    user_id = session['user_id']
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query1 = "SELECT teamID FROM PlayerTeam WHERE LID = ? AND accountID = ?"
    cursor.execute(query1, (league_id, user_id))
    my_team = cursor.fetchone()
    my_team_id = my_team['teamID']

    query2 ="""SELECT nba.PID, nba.playerName FROM NBAPlayer nba
            JOIN PlayerAthlete pa ON nba.PID = pa.PID
            WHERE pa.teamID = ? AND pa.LID = ?
            """
    cursor.execute(query2, (my_team_id, league_id))
    my_players = cursor.fetchall()

    query3 ="""SELECT pt.teamID, pt.teamName as team_name
            FROM PlayerTeam pt WHERE pt.LID = ? AND pt.teamID != ?
            """
    cursor.execute(query3, (league_id, my_team_id))
    members = cursor.fetchall()

    # do query for pending trades later, ts hard asl
    pending_trades = []

    #if palyer chose a team to trade with get the ppl on that team
    target_team_id = request.args.get('target_team_id')
    other_players = []
    if target_team_id:
        query5 =""" SELECT nba.PID, nba.playerName, pt.teamName as team_name
                FROM NBAPlayer nba
                JOIN PlayerAthlete pa ON nba.PID = pa.PID
                JOIN PlayerTeam pt ON pa.teamID = pt.teamID
                WHERE pa.teamID = ? AND pa.LID = ?
                """
        cursor.execute(query5, (target_team_id, league_id))
        other_players = cursor.fetchall()

    conn.close()

    return render_template("trade.html", my_players=my_players, members=members, pending_trades=pending_trades, other_players=other_players, target_team_id=target_team_id, league_id=league_id)


@app.route('/accept_trade/<int:league_id>/<int:trade_id>', methods=['POST'])
def accept_trade(league_id, trade_id):
    #accept an existing trade
    return "accpeted"

@app.route('/decline_trade/<int:league_id>/<int:trade_id>', methods=['POST'])
def decline_trade(league_id, trade_id):
    #decline an existing trade
    return "declined"

@app.route('/propose_trade/<int:league_id>', methods=['POST'])
def propose_trade(league_id):
    #propose a new trade
    return "proposed"


@app.route("/draft_player/<int:league_id>/<int:player_id>/<int:team_id>", methods=['POST'])
def draft_player(league_id, player_id, team_id):
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login_page'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # check team = player owns
    cursor.execute(
        "SELECT 1 FROM PlayerTeam WHERE teamID = ? AND LID = ? AND accountID = ?",
        (team_id, league_id, user_id)
    )
    if not cursor.fetchone():
        conn.close()
        return redirect(url_for('league', league_id=league_id))

    # Check  user turn
    current_turn_team_id = get_current_draft_turn(cursor, league_id)
    if current_turn_team_id != team_id:
        conn.close()
        return redirect(url_for('league', league_id=league_id))

    # Check if player already drafted
    cursor.execute("SELECT 1 FROM PlayerAthlete WHERE PID = ? AND LID = ?", (player_id, league_id))
    if cursor.fetchone():
        conn.close()
        return redirect(url_for('league', league_id=league_id))

    # Draft the player fn
    cursor.execute(
        "INSERT INTO PlayerAthlete (LID, PID, teamID) VALUES (?, ?, ?)",
        (league_id, player_id, team_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('league', league_id=league_id))


def calculate_day_scores(cursor, league_id, day):
    """Calculate scores for all games on a given day and update PlayerGame"""

    # Standard fantasy scoring (based on available columns in NBAGameStats)
    SCORING = {
        'pts': 1.0,
        'reb': 1.25,
        'ast': 1.5,
        'blk': 2.0,
        'tov': -1.0
    }

    # Get all games for this day
    cursor.execute(
        """SELECT matchupID, T1, T2 FROM PlayerSchedule
           WHERE LID = ? AND week = ?""",
        (league_id, day)
    )
    games = cursor.fetchall()

    for matchup_id, team1_id, team2_id in games:
        # Get the NBA date for this fantasy day
        cursor.execute("SELECT MIN(date) FROM NBASchedule")
        first_nba_date_result = cursor.fetchone()

        if first_nba_date_result and first_nba_date_result[0]:
            from datetime import datetime, timedelta
            date_str = first_nba_date_result[0].split()[0] if ' ' in first_nba_date_result[0] else first_nba_date_result[0]
            first_nba_date = datetime.strptime(date_str, '%Y-%m-%d')
            nba_date = first_nba_date + timedelta(days=day - 1)
            nba_date_str = nba_date.strftime('%Y-%m-%d')

            # Calculate scores for both teams
            for team_id in [team1_id, team2_id]:
                team_score = 0.0

                # Get all players on this team (regardless of active status - add all to AthleteGame)
                cursor.execute(
                    """SELECT pa.PID, pa.active, np.playerName
                       FROM PlayerAthlete pa
                       JOIN NBAPlayer np ON pa.PID = np.PID
                       WHERE pa.LID = ? AND pa.teamID = ?""",
                    (league_id, team_id)
                )
                players = cursor.fetchall()

                for player_id, active, player_name in players:
                    player_score = 0.0

                    # Get player's NBA stats for this date
                    cursor.execute(
                        """SELECT ngs.pts, ngs.rebounds, ngs.assists, ngs.blocks, ngs.turnovers
                           FROM NBAGameStats ngs
                           JOIN NBASchedule ns ON ngs.GID = ns.GID
                           WHERE ngs.PID = ? AND date(ns.date) = ?""",
                        (player_id, nba_date_str)
                    )
                    stats = cursor.fetchone()

                    if stats:
                        pts, reb, ast, blk, tov = stats
                        # Calculate fantasy score using standard scoring
                        player_score = (
                            (pts or 0) * SCORING['pts'] +
                            (reb or 0) * SCORING['reb'] +
                            (ast or 0) * SCORING['ast'] +
                            (blk or 0) * SCORING['blk'] +
                            (tov or 0) * SCORING['tov']
                        )

                    # Store individual player score in AthleteGame (only if they played or active)
                    cursor.execute(
                        """INSERT OR REPLACE INTO AthleteGame (LID, matchupID, day, PID, playerScore, status)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (league_id, matchup_id, str(day), player_id, player_score, 'active' if active else 'bench')
                    )

                    # Only count active players toward team score
                    if active:
                        team_score += player_score

                # Update or insert team score in PlayerGame
                cursor.execute(
                    """INSERT OR REPLACE INTO PlayerGame (LID, matchupID, day, teamID, Score)
                       VALUES (?, ?, ?, ?, ?)""",
                    (league_id, matchup_id, str(day), team_id, team_score)
                )


def generate_schedule(cursor, league_id):
    # Get all teams
    cursor.execute("SELECT teamID FROM PlayerTeam WHERE LID = ?", (league_id,))
    teams_data = cursor.fetchall()
    teams = []
    for team in teams_data:
        teams.append(team[0])

    num_teams = len(teams)

    if num_teams < 2:
        return

    matchup_id = 1
    day = 1

    # round robin
    if num_teams % 2 == 1:
        teams.append(None)
        num_teams = num_teams + 1

    # Generate matchups
    for round_num in range(num_teams - 1):
        # Create pairs for this round
        for i in range(num_teams // 2):
            team1 = teams[i]
            team2 = teams[num_teams - 1 - i]

            if team1 is not None and team2 is not None:
                cursor.execute(
                    "INSERT INTO PlayerSchedule (matchupID, LID, week, T1, T2) VALUES (?, ?, ?, ?, ?)",
                    (matchup_id, league_id, day, team1, team2)
                )
                matchup_id = matchup_id + 1

        day = day + 1

        # Rotate teams for next round
        if round_num < num_teams - 2:
            teams = [teams[0]] + teams[-1:] + teams[1:-1]


#helper function for draft
def get_current_draft_turn(cursor, league_id):
    # get players drafted
    cursor.execute("SELECT COUNT(*) FROM PlayerAthlete WHERE LID = ?", (league_id,))
    total_picks = cursor.fetchone()[0]

    # get number of teams
    cursor.execute("SELECT COUNT(*) FROM PlayerTeam WHERE LID = ?", (league_id,))
    num_teams = cursor.fetchone()[0]

    # check if still draft
    if total_picks >= (num_teams * 10):
        cursor.execute("UPDATE PlayerLeague SET status = 'game' WHERE LID = ?", (league_id,))
        generate_schedule(cursor, league_id)
        return None

    current_round = (total_picks // num_teams) + 1
    pick_in_round = (total_picks % num_teams) + 1

    # get draft type
    cursor.execute("SELECT draftType FROM PlayerLeague WHERE LID = ?", (league_id,))
    draft_type_result = cursor.fetchone()
    draft_type = draft_type_result[0]

    # snake draft: reverse order on even rounds
    if draft_type == 'snake' and current_round % 2 == 0:
        target_pick_order = num_teams - pick_in_round + 1
    else:
        target_pick_order = pick_in_round

    # get team with this pick order
    cursor.execute(
        "SELECT teamID FROM DraftOrder WHERE LID = ? AND pickOrder = ?",
        (league_id, target_pick_order)
    )
    pick = cursor.fetchone()
    return pick[0] if pick else None


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port = 8000)