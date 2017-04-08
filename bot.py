
import pytz
import datetime
import configparser
import telegram
import sys
import redis
import requests
import time
import datetime

headers = {
    "authority": "wz4j065jwc.execute-api.ap-southeast-1.amazonaws.com",
    "origin": "http://fantasy.iplt20.com",
    "referer": "http://fantasy.iplt20.com/squad/"
}

indian = pytz.timezone('Asia/Calcutta')

def get_names(player_ids):
    return [r.hget("player:" + player_id, "name") for player_id in player_ids]

def get_refresh_token(access_token, user_id):
    success_code = 900
    refresh_token_url = "https://wz4j065jwc.execute-api.ap-southeast-1.amazonaws.com/production/users/refreshtoken"
    refresh_token = config.get('ipl', 'refresh_token')

    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id
    }

    resp = requests.post(refresh_token_url, json=payload, headers=headers)

    if resp.status_code == requests.codes.ok:
        response = resp.json()
        if response['code'] == success_code:
            return True, response['data']['access_token']
        else:
            return False, "Error fetching token"
    else:
        False, resp.text

def get_squad(user_id, match_id, name):
    url = "https://wz4j065jwc.execute-api.ap-southeast-1.amazonaws.com/production/users/squad"
    accesstoken = r.get('ipl_access_token') or "test-access-token"

    m_headers = {
        'accesstoken': accesstoken,
        'origin': 'http://fantasy.iplt20.com',
        'accept-encoding': 'gzip, deflate, sdch, br',
        'accept-language': 'en-US,en;q=0.8',
        'accept': 'application/json, text/plain, */*',
        'referer': 'http://fantasy.iplt20.com/squad/',
        'userid': config.get('ipl', 'user_id'),
        'authority': 'wz4j065jwc.execute-api.ap-southeast-1.amazonaws.com',
    }

    params = (
        ('matchId', match_id),
        ('userid', user_id),
    )

    resp = requests.get(url, headers=m_headers, params=params)

    message = ""

    if resp.status_code == requests.codes.ok:
        response = resp.json()
        power_player_redis_key = user_id + ":powerplayer"
        players = set(map(str, response['data']['players']))
        powerplayer = str(response['data']['powerPlayer'])
        prev_players = r.smembers(user_id)
        prev_power_player = r.get(power_player_redis_key)

        # Check for change in player
        if players - prev_players:
            now = str(datetime.datetime.now().astimezone(indian))
            added = get_names(players - prev_players)
            removed = get_names(prev_players - players)
            change_in_player = """
Time : {now}
Change in players by {name} , added : {added}
Change in players by {name} , removed : {removed}
""".format(now=now, name=name, added=added, removed=removed)
            print(change_in_player)
            message += change_in_player
            r.delete(user_id)
            r.sadd(user_id, *players)

        # Check for change in powerplayer
        if powerplayer != prev_power_player:
            change_in_power_player = """
Time : {now}
Change in powerplayer by {name}
Current powerplayer : {powerplayer}
""".format(now=now, name=name, powerplayer=powerplayer)
            print(change_in_power_player)
            message += change_in_power_player
            r.set(power_player_redis_key, powerplayer)
    else:
        success, access_token = get_refresh_token(access_token=m_headers['accesstoken'], user_id=m_headers['userid'])
        if success:
            r.set("ipl_access_token", access_token)
            m_headers.update({"accesstoken" : access_token})
        else:
            message += "Error " + access_token
            print("Got error ", access_token)

    if message:
        bot.sendMessage(chat_id=config.get('telegram', 'chat_id'), text=message)

def update_current_matches():
    resp = requests.get("https://s3-ap-southeast-1.amazonaws.com/images-fantasy-iplt20/match-data/livematchdev.json")
    live_urls = []

    if resp.status_code == requests.codes.ok:
        resp = resp.json()
        matches = resp.get('currentMatches', [])
        for match in matches:
            if resp.get(str(match), {}).get('liveUrl'):
                r.zadd('current_matches', resp[str(match)]['liveUrl'], match)

        r.expire('current_matches', 43200) # expire after 12 hours

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    r = redis.Redis(decode_responses=True)
    bot = telegram.Bot(token=config.get('telegram', 'token'))

    user_items = config.items("users")
    users = {}
    for name, user_id in user_items:
        users[user_id] = name

    while True:
        time.sleep(20)
        error = ""
        try:
            if not r.exists('current_matches'):
                update_current_matches()
            matches = r.zrange('current_matches', 0, -1, withscores=True) or []

            for _, match in matches:
                for user, name in users.items():
                    get_squad(user, match, name)
        except Exception as e:
            error = str(e)
            bot.sendMessage(chat_id=config.get('telegram', 'chat_id'), text=error)
            break
