import logging, random, string, asyncio, threading, aiohttp, json, os, time
from flask import Flask, request, jsonify, render_template_string, session, redirect
from collections import deque
from datetime import datetime

# ===============================
# CONFIGURATION
# ===============================
TOKEN = os.environ.get("TOKEN", "8682364291:AAEGU7nfBSVVjmvcWoejjm13fsiHKdQp7h8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6890999007"))

USERS_FILE = "users.json"
AI_FILE = "ai.json"
HITS_FILE = "hits.txt"
MEMORY_FILE = "memory.json"

# ===============================
# SETTINGS
# ===============================
class Settings:
    def __init__(self):
        self.mode = "all"
        self.use_underscore = True
        self.only_rare = True

    def set_mode(self, mode):
        self.mode = mode

    def toggle_underscore(self):
        self.use_underscore = not self.use_underscore

    def toggle_rare(self):
        self.only_rare = not self.only_rare

settings = Settings()

# ===============================
# AI SYSTEM
# ===============================
class AI:
    def __init__(self):
        self.patterns = {
            "3_normal": {"weight": 1.0, "success": 0, "fail": 0, "type": "3"},
            "3_strong": {"weight": 1.2, "success": 0, "fail": 0, "type": "3"},
            "3_ice": {"weight": 1.5, "success": 0, "fail": 0, "type": "3"},
            "4_normal": {"weight": 1.0, "success": 0, "fail": 0, "type": "4"},
            "4_strong": {"weight": 1.3, "success": 0, "fail": 0, "type": "4"},
            "34_mixed": {"weight": 1.1, "success": 0, "fail": 0, "type": "34"},
            "underscore": {"weight": 1.4, "success": 0, "fail": 0, "type": "under"}
        }
        self.load()

    def load(self):
        if os.path.exists(AI_FILE):
            try:
                with open(AI_FILE, "r") as f:
                    data = json.load(f)
                    for key in self.patterns:
                        if key in data and "type" in data[key]:
                            self.patterns[key].update(data[key])
            except:
                pass

    def save(self):
        with open(AI_FILE, "w") as f:
            json.dump(self.patterns, f)

    def choose(self):
        available = []

        if settings.mode == "3":
            available = ["3_normal", "3_strong", "3_ice"]
        elif settings.mode == "4":
            available = ["4_normal", "4_strong"]
        elif settings.mode == "34":
            available = ["3_normal", "3_strong", "4_normal", "4_strong", "34_mixed"]
        else:
            available = list(self.patterns.keys())

        if settings.use_underscore and "underscore" not in available:
            available.append("underscore")

        total = sum(self.patterns[p]["weight"] for p in available)
        r = random.uniform(0, total)
        s = 0
        for p in available:
            s += self.patterns[p]["weight"]
            if s >= r:
                return p
        return available[0]

    def reward(self, pattern):
        self.patterns[pattern]["success"] += 1
        self.patterns[pattern]["weight"] += 0.1
        self.save()

    def punish(self, pattern):
        self.patterns[pattern]["fail"] += 1
        self.patterns[pattern]["weight"] = max(0.1, self.patterns[pattern]["weight"] - 0.05)
        self.save()

    def get_stats(self):
        result = {}
        for p, d in self.patterns.items():
            result[p] = {
                "weight": round(d.get("weight", 1.0), 2),
                "success": d.get("success", 0),
                "fail": d.get("fail", 0),
                "type": d.get("type", "3")
            }
        return result

ai = AI()

# ===============================
# MEMORY
# ===============================
class Memory:
    def __init__(self):
        self.checked = set()
        self.load()

    def load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                    self.checked = set(data.get("checked", []))
            except:
                pass

    def save(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump({"checked": list(self.checked)[-5000:]}, f)

    def add(self, username):
        self.checked.add(username)
        if len(self.checked) % 100 == 0:
            self.save()

    def exists(self, username):
        return username in self.checked

    def get_unique(self, generator_func):
        for _ in range(50):
            username = generator_func()
            if not self.exists(username):
                self.add(username)
                return username
        return generator_func() + str(random.randint(1, 99))

memory = Memory()

# ===============================
# SPEED
# ===============================
class Speed:
    def __init__(self):
        self.delay = 0.5

    def get_delay(self):
        return self.delay

    def set_speed(self, mode):
        speeds = {"fast": 0.2, "normal": 0.5, "slow": 1.0}
        self.delay = speeds.get(mode, 0.5)

speed = Speed()

# ===============================
# STATS
# ===============================
class Stats:
    def __init__(self):
        self.checked = 0
        self.found = 0
        self.running = False
        self.workers = 5
        self.start_time = None
        self.hits = []
        self.rare_found = 0
        self.type_counts = {"3": 0, "4": 0, "34": 0, "under": 0}

    def start(self):
        self.running = True
        self.start_time = datetime.now()

    def stop(self):
        self.running = False

    def get_uptime(self):
        if not self.start_time:
            return "0:00:00"
        delta = datetime.now() - self.start_time
        return str(delta).split(".")[0]

    def get_rpm(self):
        if not self.start_time or not self.running:
            return 0
        minutes = (datetime.now() - self.start_time).total_seconds() / 60
        return round(self.checked / max(minutes, 1), 1)

stats = Stats()

# ===============================
# GENERATORS
# ===============================
def gen(pattern):
    chars = string.ascii_lowercase + string.digits

    if pattern == "3_normal":
        styles = [
            lambda: random.choice(chars) * 3,
            lambda: ''.join(random.choices(chars, k=3)),
            lambda: random.choice(chars) + random.choice(chars) + random.choice(chars)[::-1]
        ]
        return random.choice(styles)()

    elif pattern == "3_strong":
        styles = [
            lambda: random.choice(string.ascii_lowercase) + random.choice(string.digits) + random.choice(string.ascii_lowercase),
            lambda: random.choice(string.digits) + random.choice(string.ascii_lowercase) * 2,
            lambda: random.choice(string.ascii_lowercase) * 2 + random.choice(string.digits)
        ]
        return random.choice(styles)()

    elif pattern == "3_ice":
        return random.choice(string.ascii_lowercase) + random.choice(string.digits) + random.choice(string.digits)

    elif pattern == "4_normal":
        styles = [
            lambda: random.choice(chars) * 4,
            lambda: ''.join(random.choices(chars, k=4)),
            lambda: (random.choice(chars) + random.choice(chars)) * 2
        ]
        return random.choice(styles)()

    elif pattern == "4_strong":
        styles = [
            lambda: random.choice(string.ascii_lowercase) + random.choice(string.digits) + random.choice(string.ascii_lowercase) + random.choice(string.digits),
            lambda: random.choice(string.digits) + random.choice(string.ascii_lowercase) * 3,
            lambda: random.choice(string.ascii_lowercase) * 3 + random.choice(string.digits)
        ]
        return random.choice(styles)()

    elif pattern == "34_mixed":
        if random.random() > 0.5:
            return gen("3_strong")
        else:
            return gen("4_normal")

    elif pattern == "underscore":
        styles = [
            lambda: random.choice(chars) + "_" + random.choice(chars) + random.choice(chars),
            lambda: random.choice(chars) + random.choice(chars) + "_" + random.choice(chars),
            lambda: random.choice(chars) + "_" + random.choice(chars) + random.choice(string.digits),
            lambda: random.choice(chars) + random.choice(string.digits) + "_" + random.choice(chars),
            lambda: random.choice(chars) + "_" + random.choice(string.digits) + random.choice(chars),
            lambda: random.choice(string.digits) + "_" + random.choice(chars) + random.choice(chars)
        ]
        return random.choice(styles)()

    return ''.join(random.choices(chars, k=3))

def rarity(username):
    u = username.replace("_", "")
    unique = len(set(u))
    length = len(u)

    if "_" in username:
        parts = username.split("_")
        if len(parts[0]) == 1 and len(parts[1]) == 2:
            return "ثلاثي underscore نادر", 4, "under"
        if len(parts[0]) == 2 and len(parts[1]) == 1:
            return "ثلاثي underscore", 3, "under"
        return "underscore", 2.5, "under"

    if length == 3:
        if unique == 1:
            return "ثلاثي قوي جداً", 4, "3"
        if username[0] == username[2]:
            return "ثلاثي متناظر", 3, "3"
        if username.isalpha() and len(set(username)) == 3:
            return "ثلاثي عادي", 1, "3"
        if any(c.isdigit() for c in username):
            return "ثلاثي شبه نادر", 2, "3"
        return "ثلاثي", 1, "3"

    if length == 4:
        if unique == 1:
            return "رباعي قوي جداً", 5, "4"
        if username == username[::-1]:
            return "رباعي متناظر", 4, "4"
        if username[0] == username[2] and username[1] == username[3]:
            return "رباعي تكرار", 3, "4"
        if any(c.isdigit() for c in username):
            return "رباعي شبه نادر", 2, "4"
        return "رباعي عادي", 1, "4"

    return "عادي", 0.5, "3"

# ===============================
# CHECKER
# ===============================
async def check(session, username):
    try:
        async with session.get(f"https://www.tiktok.com/@{username}", timeout=10) as r:
            if r.status == 404:
                return True
            elif r.status == 200:
                return False
            else:
                return None
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        return None

# ===============================
# WORKER - المصلح
# ===============================
async def worker():
    async with aiohttp.ClientSession() as session:
        while stats.running:
            try:
                pattern = ai.choose()
                username = memory.get_unique(lambda: gen(pattern))

                stats.checked += 1

                is_available = await check(session, username)

                if is_available is True:
                    rare_type, score, t = rarity(username)
                    is_rare = score >= 2

                    ai.reward(pattern)
                    
                    if not settings.only_rare or is_rare:
                        if is_rare:
                            stats.rare_found += 1

                        stats.type_counts[t] += 1

                        hit = {
                            "username": username,
                            "pattern": pattern,
                            "rarity": rare_type,
                            "score": score,
                            "type": t,
                            "time": datetime.now().isoformat()
                        }
                        stats.hits.append(hit)

                        with open(HITS_FILE, "a") as f:
                            f.write(f"{username} | {rare_type} | {pattern} | {t}\n")

                        stats.found += 1
                        print(f"✅ FOUND: @{username} | {rare_type}")
                
                elif is_available is False:
                    ai.punish(pattern)
                
                else:
                    pass

                await asyncio.sleep(speed.get_delay())

            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(1)

async def main_loop():
    tasks = [asyncio.create_task(worker()) for _ in range(stats.workers)]
    await asyncio.gather(*tasks)

# ===============================
# WEB INTERFACE
# ===============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI TikTok Checker Pro</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700;900&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --black: #0a0a0a;
    --dark: #1a1a1a;
    --gray: #2a2a2a;
    --orange: #ff6b00;
    --orange-light: #ff8c00;
    --orange-dark: #cc5500;
    --gold: #ffd700;
    --red: #ff3333;
    --green: #00ff88;
}

body {
    font-family: 'Tajawal', sans-serif;
    background: var(--black);
    color: #fff;
    min-height: 100vh;
    padding: 20px;
}

.container { max-width: 1200px; margin: 0 auto; }

.header {
    text-align: center;
    padding: 30px 0;
    border-bottom: 3px solid var(--orange);
    margin-bottom: 30px;
}

.logo {
    font-size: 3em;
    font-weight: 900;
    background: linear-gradient(135deg, var(--orange), var(--gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.tagline {
    color: #888;
    margin-top: 10px;
    font-size: 1.1em;
}

.status-bar {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-bottom: 30px;
    flex-wrap: wrap;
}

.status-pill {
    padding: 12px 30px;
    border-radius: 50px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
}

.status-running {
    background: linear-gradient(135deg, var(--orange), var(--orange-dark));
    color: #fff;
    box-shadow: 0 0 20px rgba(255,107,0,0.4);
    animation: pulse 2s infinite;
}

.status-stopped {
    background: var(--gray);
    color: #666;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(255,107,0,0.4); }
    50% { box-shadow: 0 0 40px rgba(255,107,0,0.6); }
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: linear-gradient(145deg, var(--dark), var(--gray));
    border-radius: 20px;
    padding: 25px;
    text-align: center;
    border: 1px solid rgba(255,107,0,0.2);
    position: relative;
    overflow: hidden;
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--orange), var(--gold));
}

.stat-value {
    font-size: 2.8em;
    font-weight: 900;
    background: linear-gradient(135deg, var(--orange), var(--gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.stat-label {
    color: #888;
    margin-top: 8px;
    font-size: 0.95em;
}

.settings-panel {
    background: linear-gradient(145deg, var(--dark), var(--gray));
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 30px;
    border: 1px solid rgba(255,107,0,0.3);
}

.panel-title {
    color: var(--orange);
    font-size: 1.3em;
    font-weight: 700;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.setting-group {
    margin-bottom: 20px;
}

.setting-label {
    color: #aaa;
    margin-bottom: 12px;
    font-size: 0.9em;
}

.setting-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.setting-btn {
    padding: 12px 24px;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 700;
    transition: all 0.3s;
    border: 2px solid transparent;
}

.setting-btn.active {
    background: linear-gradient(135deg, var(--orange), var(--orange-dark));
    color: #fff;
    box-shadow: 0 4px 15px rgba(255,107,0,0.3);
}

.setting-btn.inactive {
    background: var(--gray);
    color: #888;
    border-color: rgba(255,107,0,0.2);
}

.setting-btn.inactive:hover {
    border-color: var(--orange);
    color: var(--orange);
}

.controls {
    display: flex;
    gap: 15px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 30px;
}

.control-btn {
    padding: 15px 30px;
    border: none;
    border-radius: 15px;
    font-weight: 700;
    font-size: 1em;
    cursor: pointer;
    transition: all 0.3s;
    display: flex;
    align-items: center;
    gap: 8px;
}

.btn-start {
    background: linear-gradient(135deg, var(--green), #00cc6a);
    color: #000;
    box-shadow: 0 4px 20px rgba(0,255,136,0.3);
}

.btn-stop {
    background: linear-gradient(135deg, var(--red), #cc0000);
    color: #fff;
    box-shadow: 0 4px 20px rgba(255,51,51,0.3);
}

.btn-speed {
    background: linear-gradient(135deg, var(--orange), var(--orange-dark));
    color: #fff;
}

.control-btn:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(255,107,0,0.4);
}

.ai-panel {
    background: linear-gradient(145deg, var(--dark), var(--gray));
    border-radius: 20px;
    padding: 25px;
    margin-bottom: 30px;
    border: 1px solid rgba(255,107,0,0.2);
}

.ai-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
}

.ai-item {
    background: rgba(0,0,0,0.3);
    padding: 15px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 15px;
}

.ai-type {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 0.8em;
}

.type-3 { background: linear-gradient(135deg
