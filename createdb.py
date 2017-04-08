import redis
import json
import sqlite3

with open("players.json") as f:
    db = sqlite3.connect('players.db')
    redis_conn = redis.Redis(decode_responses=True)
    cur = db.cursor()
    data = json.loads(f.read())
    players = data["data"]
    fields = set(players[1].keys())
    table_name = "players"
    print("creating table with fields : ", fields)
    cur.execute("create table players(id INTEGER PRIMARY KEY AUTOINCREMENT, rightArmBowl boolean, rightArmBat boolean, price real, dob integer, injured boolean, uncapped boolean, role text, teamId integer, nationality text, shortName text, fullName text, teamAbbreviation text, playerId integer)")
    print("Inserting values")
    for player in players:
        player['role'] = ":".join(player['role'])
        columns = ', '.join(player.keys())
        placeholders = ', '.join('?' * len(player.keys()))
        sql = 'INSERT INTO {} ({}) VALUES ({})'.format(table_name, columns, placeholders)
        cur.execute(sql, list(player.values()))
        redis_conn.hset("player:" + str(player['playerId']), "name", player['fullName'])

    db.commit()
    print("Inserted successfully")
