CREATE TABLE NBATeam (
    TID INTEGER PRIMARY KEY,
    city TEXT,
    teamname TEXT,
    conference TEXT
);

CREATE TABLE PlayerAccount (
    accountID INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
);

-- NBA STATS TABLES

CREATE TABLE NBAPlayer (
    PID INTEGER PRIMARY KEY,
    TID INTEGER,
    playerName TEXT,
    prevPlayerScore REAL,
    position TEXT,
    FOREIGN KEY (TID) REFERENCES NBATeam(TID)
);

CREATE TABLE NBASchedule (
    GID INTEGER PRIMARY KEY,
    date TEXT,
    home INTEGER,
    away INTEGER,
    FOREIGN KEY (home) REFERENCES NBATeam(TID),
    FOREIGN KEY (away) REFERENCES NBATeam(TID)
);

CREATE TABLE NBAGameStats (
    GID INTEGER,
    PID INTEGER,
    pts INTEGER,
    shots INTEGER,
    blocks INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    turnovers INTEGER,
    PRIMARY KEY (GID, PID),
    FOREIGN KEY (GID) REFERENCES NBASchedule(GID),
    FOREIGN KEY (PID) REFERENCES NBAPlayer(PID)
);


-- APP TABLES

CREATE TABLE PlayerLeague (
    LID INTEGER PRIMARY KEY,
    draftType TEXT,
    leagueName TEXT,
    ownerAccount INTEGER,
    status TEXT DEFAULT 'initial', -- 'initial', 'draft', 'final'
    FOREIGN KEY (ownerAccount) REFERENCES PlayerAccount(accountID)
);

CREATE TABLE PlayerTeam (
    teamID INTEGER PRIMARY KEY,
    LID INTEGER,
    accountID INTEGER,
    teamName TEXT,
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (accountID) REFERENCES PlayerAccount(accountID)
);

CREATE TABLE PlayerAthlete (
    LID INTEGER,
    PID INTEGER,
    teamID INTEGER,
    PRIMARY KEY (LID, PID),
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (PID) REFERENCES NBAPlayer(PID),
    FOREIGN KEY (teamID) REFERENCES PlayerTeam(teamID)
);


-- GAME TABLES

CREATE TABLE PlayerSchedule (
    matchupID INTEGER,
    LID INTEGER,
    week INTEGER,
    T1 INTEGER,
    T2 INTEGER,
    PRIMARY KEY (LID, matchupID),
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (T1) REFERENCES PlayerTeam(teamID),
    FOREIGN KEY (T2) REFERENCES PlayerTeam(teamID)
);

CREATE TABLE PlayerGame (
    LID INTEGER,
    matchupID INTEGER,
    day TEXT,
    teamID INTEGER,
    Score REAL,
    PRIMARY KEY (LID, matchupID, teamID),
    FOREIGN KEY (LID, matchupID) REFERENCES PlayerSchedule(LID, matchupID),
    FOREIGN KEY (teamID) REFERENCES PlayerTeam(teamID)
);

CREATE TABLE AthleteGame (
    LID INTEGER,
    matchupID INTEGER,
    day TEXT,
    PID INTEGER,
    playerScore REAL,
    status TEXT,
    PRIMARY KEY (LID, matchupID, PID),
    FOREIGN KEY (LID, matchupID) REFERENCES PlayerSchedule(LID, matchupID),
    FOREIGN KEY (PID) REFERENCES NBAPlayer(PID)
);


-- TEAM TABLES

CREATE TABLE Leaderboard (
    LID INTEGER,
    rank INTEGER,
    teamID INTEGER,
    wins INTEGER,
    losses INTEGER,
    totalPointsFor REAL,
    totalPointsAgainst REAL,
    PRIMARY KEY (LID, teamID),
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (teamID) REFERENCES PlayerTeam(teamID)
);

CREATE TABLE Trade (
    tradeID INTEGER PRIMARY KEY ,
    LID INTEGER,
    proposingTeamID INTEGER,
    receivingTeamID INTEGER,
    offeredPID INTEGER,
    requestedPID INTEGER,
    status TEXT DEFAULT 'waiting', -- 'waiting', 'accepted', 'declined'
    date TEXT,
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (proposingTeamID) REFERENCES PlayerTeam(teamID),
    FOREIGN KEY (receivingTeamID) REFERENCES PlayerTeam(teamID),
    FOREIGN KEY (offeredPID) REFERENCES NBAPlayer(PID),
    FOREIGN KEY (requestedPID) REFERENCES NBAPlayer(PID)
);

CREATE TABLE DraftOrder (
    LID INTEGER,
    teamID INTEGER,
    pickOrder INTEGER,
    PRIMARY KEY (LID, pickOrder),
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (teamID) REFERENCES PlayerTeam(teamID)
);

CREATE TABLE Draft (
    LID INTEGER,
    PID INTEGER,
    teamID INTEGER,
    round INTEGER,
    PRIMARY KEY (LID, PID),
    FOREIGN KEY (LID) REFERENCES PlayerLeague(LID),
    FOREIGN KEY (PID) REFERENCES NBAPlayer(PID),
    FOREIGN KEY (teamID) REFERENCES PlayerTeam(teamID)
);