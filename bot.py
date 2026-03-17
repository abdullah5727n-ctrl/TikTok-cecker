import logging, random, string, asyncio, threading, aiohttp, json, os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===============================
TOKEN = os.environ.get("TOKEN", "8723464858:AAEVoU_oBDP-6WXQYU6ZbcFajjoXD0lObWA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6890999007"))

USERS_FILE = "users.json"
AI_FILE = "ai.json"
HITS_FILE = "hits.txt"

USE_3 = True
ONLY_RARE = True

# ===============================
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin": os.environ.get("ADMIN_PASS", "1234")}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

users = load_users()

# ===============================
class AI:
    def __init__(self):
        self.data = {"repeat": 1, "sequence": 1, "pattern": 1, "mirror": 1, "random": 1}
        if os.path.exists(AI_FILE):
            with open(AI_FILE, "r") as f:
                self.data = json.load(f)

    def save(self):
        with open(AI_FILE, "w") as f:
            json.dump(self.data, f)

    def choose(self):
        total = sum(self.data.values())
        r = random.uniform(0, total)
        s = 0
        for k, v in self.data.items():
            if s + v >= r:
                return k
            s += v

    def reward(self, p):
        self.data[p] += 2
        self.save()

    def punish(self, p):
        self.data[p] = max(1, self.data[p] - 0.2)
        self.save()

ai = AI()

# ===============================
class Stats:
    def __init__(self):
        self.checked = 0
        self.found = 0
        self.running = False
        self.delay = 0.5
        self.workers = 5

stats = Stats()

# ===============================
def gen(p, length=None):
    L = length if length else (3 if USE_3 else 4)
    chars = string.ascii_lowercase + string.digits
    
    if p == "repeat":
        c = random.choice(chars)
        return c * L
    
    if p == "sequence":
        s = string.ascii_lowercase
        if L == 3:
            i = random.randint(0, len(s) - 3)
            return s[i:i + 3]
        else:
            i = random.randint(0, len(s) - 4)
            return s[i:i + 4]
    
    if p == "pattern":
        a = random.choice(string.ascii_lowercase)
        b = random.choice(string.digits)
        if L == 3:
            return a + b + a
        else:
            return a + b + a + b
    
    if p == "mirror":
        if L == 3:
            x = random.choice(string.ascii_lowercase)
            mid = random.choice(string.ascii_lowercase + string.digits)
            return x + mid + x
        else:
            x = ''.join(random.choices(string.ascii_lowercase, k=2))
            return x + x[::-1]
    
    if p == "random":
        return ''.join(random.choices(chars, k=L))
    
    return ''.join(random.choices(chars, k=L))

def rarity(u):
    L = len(u)
    unique_chars = len(set(u))
    
    if unique_chars == 1:
        return "🔥 نادر"
    
    if u == u[::-1]:
        return "🧬 متناظر"
    
    if L == 4 and u[0] == u[2] and u[1] == u[3]:
        return "🔄 تكرار"
    
    if L == 4 and all(ord(u[i]) + 1 == ord(u[i+1]) for i in range(3)):
        return "📈 تسلسل"
    
    return "⭐ عادي"

# ===============================
async def check(session, u):
    try:
        async with session.get(f"https://www.tiktok.com/@{u}", timeout=8) as r:
            return r.status == 404
    except:
        return None

# ===============================
async def worker():
    async with aiohttp.ClientSession() as session:
        while stats.running:
            try:
                p = ai.choose()
                L = 3 if USE_3 else 4
                u = gen(p, L)
                
                stats.checked += 1
                ok = await check(session, u)

                if ok:
                    r = rarity(u)
                    should_save = False
                    if not ONLY_RARE:
                        should_save = True
                    elif "🔥" in r or "🧬" in r:
                        should_save = True
                    elif L == 4 and ("🔄" in r or "📈" in r):
                        should_save = True
                    
                    if should_save:
                        stats.found += 1
                        ai.reward(p)
                        with open(HITS_FILE, "a") as f:
                            f.write(f"{u} | {r} | {p}\n")
                else:
                    ai.punish(p)
                    
            except Exception as e:
                logging.error(f"Worker error: {e}")
                
            await asyncio.sleep(stats.delay)

# ===============================
async def loop():
    tasks = [asyncio.create_task(worker()) for _ in range(stats.workers)]
    await asyncio.gather(*tasks)

# ===============================
# 🌐 WEB PANEL - تصميم احترافي
# ===============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# ✅ CSS احترافي
STYLES = """
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.container {
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    padding: 40px;
    width: 100%;
    max-width: 500px;
}

h1 {
    color: #333;
    text-align: center;
    margin-bottom: 30px;
    font-size: 28px;
}

h2 {
    color: #555;
    text-align: center;
    margin-bottom: 25px;
}

.form-group {
    margin-bottom: 20px;
}

input {
    width: 100%;
    padding: 15px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 16px;
    transition: border-color 0.3s;
}

input:focus {
    outline: none;
    border-color: #667eea;
}

button {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 18px;
    font-weight: bold;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-bottom: 25px;
}

.stat-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #667eea;
}

.stat-label {
    color: #666;
    font-size: 14px;
    margin-top: 5px;
}

.status-badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: bold;
    margin-bottom: 20px;
}

.status-running {
    background: #d4edda;
    color: #155724;
}

.status-stopped {
    background: #f8d7da;
    color: #721c24;
}

.controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 15px;
}

.btn {
    padding: 12px;
    border-radius: 8px;
    text-decoration: none;
    text-align: center;
    font-weight: bold;
    transition: all 0.3s;
}

.btn-primary {
    background: #667eea;
    color: white;
}

.btn-success {
    background: #28a745;
    color: white;
}

.btn-danger {
    background: #dc3545;
    color: white;
}

.btn-warning {
    background: #ffc107;
    color: #212529;
}

.btn-info {
    background: #17a2b8;
    color: white;
}

.btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.mode-selector {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.mode-btn {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    text-decoration: none;
    font-weight: bold;
}

.mode-active {
    background: #667eea;
    color: white;
}

.mode-inactive {
    background: #e0e0e0;
    color: #666;
}

.footer {
    text-align: center;
    margin-top: 20px;
    color: #999;
    font-size: 12px;
}
</style>
"""

LOGIN_TEMPLATE = STYLES + """
<div class="container">
    <h1>🤖 TikTok Checker</h1>
    <h2>Login</h2>
    <form method="post">
        <div class="form-group">
            <input type="text" name="u" placeholder="Username" required>
        </div>
        <div class="form-group">
            <input type="password" name="p" placeholder="Password" required>
        </div>
        <button type="submit">Login</button>
    </form>
    <div class="footer">
        Default: admin / 1234
    </div>
</div>
"""

PANEL_TEMPLATE = STYLES + """
<div class="container">
    <h1>🤖 Dashboard</h1>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <span class="status-badge {{status_class}}">
            {{status_text}}
        </span>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{{c}}</div>
            <div class="stat-label">Checked</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{f}}</div>
            <div class="stat-label">Found</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{w}}</div>
            <div class="stat-label">Workers</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{d}}s</div>
            <div class="stat-label">Delay</div>
        </div>
    </div>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <strong>Mode:</strong> {{mode}} | 
        <strong>Rare Only:</strong> {{rare}}
    </div>
    
    <div class="controls">
        <a href="/start" class="btn btn-success">▶ Start</a>
        <a href="/stop" class="btn btn-danger">⏹ Stop</a>
    </div>
    
    <div class="controls">
        <a href="/fast" class="btn btn-warning">⚡ Fast (0.3s)</a>
        <a href="/slow" class="btn btn-info">🐌 Slow (1.2s)</a>
    </div>
    
    <div class="mode-selector">
        <a href="/mode3" class="mode-btn {{mode3_class}}">3 Letters</a>
        <a href="/mode4" class="mode-btn {{mode4_class}}">4 Letters</a>
    </div>
    
    <div class="controls">
        <a href="/rare" class="btn btn-primary">🎯 Toggle Rare Only</a>
    </div>
    
    <div class="footer">
        TikTok Username Checker Bot
    </div>
</div>
"""

def auth():
    return "user" in session

@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]
        if u in users and users[u] == p:
            session["user"] = u
            return redirect("/panel")
    return LOGIN_TEMPLATE

@app.route('/panel')
def panel():
    if not auth():
        return redirect("/")
    
    mode_str = "3 Letters" if USE_3 else "4 Letters"
    status_text = "🟢 Running" if        total = sum(self.data.values())
        r = random.uniform(0, total)
        s = 0
        for k, v in self.data.items():
            if s + v >= r:
                return k
            s += v

    def reward(self, p):
        self.data[p] += 2
        self.save()

    def punish(self, p):
        self.data[p] = max(1, self.data[p] - 0.2)
        self.save()

ai = AI()

# ===============================
class Stats:
    def __init__(self):
        self.checked = 0
        self.found = 0
        self.running = False
        self.delay = 0.5
        self.workers = 5

stats = Stats()

# ===============================
def gen(p, length=None):
    L = length if length else (3 if USE_3 else 4)
    chars = string.ascii_lowercase + string.digits
    
    if p == "repeat":
        c = random.choice(chars)
        return c * L
    
    if p == "sequence":
        s = string.ascii_lowercase
        if L == 3:
            i = random.randint(0, len(s) - 3)
            return s[i:i + 3]
        else:
            i = random.randint(0, len(s) - 4)
            return s[i:i + 4]
    
    if p == "pattern":
        a = random.choice(string.ascii_lowercase)
        b = random.choice(string.digits)
        if L == 3:
            return a + b + a
        else:
            return a + b + a + b
    
    if p == "mirror":
        if L == 3:
            x = random.choice(string.ascii_lowercase)
            mid = random.choice(string.ascii_lowercase + string.digits)
            return x + mid + x
        else:
            x = ''.join(random.choices(string.ascii_lowercase, k=2))
            return x + x[::-1]
    
    if p == "random":
        return ''.join(random.choices(chars, k=L))
    
    return ''.join(random.choices(chars, k=L))

def rarity(u):
    L = len(u)
    unique_chars = len(set(u))
    
    if unique_chars == 1:
        return "🔥 نادر"
    
    if u == u[::-1]:
        return "🧬 متناظر"
    
    if L == 4 and u[0] == u[2] and u[1] == u[3]:
        return "🔄 تكرار"
    
    if L == 4 and all(ord(u[i]) + 1 == ord(u[i+1]) for i in range(3)):
        return "📈 تسلسل"
    
    return "⭐ عادي"

# ===============================
async def check(session, u):
    try:
        async with session.get(f"https://www.tiktok.com/@{u}", timeout=8) as r:
            return r.status == 404
    except:
        return None

# ===============================
async def worker():
    async with aiohttp.ClientSession() as session:
        while stats.running:
            try:
                p = ai.choose()
                L = 3 if USE_3 else 4
                u = gen(p, L)
                
                stats.checked += 1
                ok = await check(session, u)

                if ok:
                    r = rarity(u)
                    should_save = False
                    if not ONLY_RARE:
                        should_save = True
                    elif "🔥" in r or "🧬" in r:
                        should_save = True
                    elif L == 4 and ("🔄" in r or "📈" in r):
                        should_save = True
                    
                    if should_save:
                        stats.found += 1
                        ai.reward(p)
                        with open(HITS_FILE, "a") as f:
                            f.write(f"{u} | {r} | {p}\n")
                else:
                    ai.punish(p)
                    
            except Exception as e:
                logging.error(f"Worker error: {e}")
                
            await asyncio.sleep(stats.delay)

# ===============================
async def loop():
    tasks = [asyncio.create_task(worker()) for _ in range(stats.workers)]
    await asyncio.gather(*tasks)

# ===============================
# 🌐 WEB PANEL - تصميم احترافي
# ===============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# ✅ CSS احترافي
STYLES = """
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.container {
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    padding: 40px;
    width: 100%;
    max-width: 500px;
}

h1 {
    color: #333;
    text-align: center;
    margin-bottom: 30px;
    font-size: 28px;
}

h2 {
    color: #555;
    text-align: center;
    margin-bottom: 25px;
}

.form-group {
    margin-bottom: 20px;
}

input {
    width: 100%;
    padding: 15px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 16px;
    transition: border-color 0.3s;
}

input:focus {
    outline: none;
    border-color: #667eea;
}

button {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 18px;
    font-weight: bold;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}

.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-bottom: 25px;
}

.stat-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
}

.stat-value {
    font-size: 32px;
    font-weight: bold;
    color: #667eea;
}

.stat-label {
    color: #666;
    font-size: 14px;
    margin-top: 5px;
}

.status-badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 20px;
    font-weight: bold;
    margin-bottom: 20px;
}

.status-running {
    background: #d4edda;
    color: #155724;
}

.status-stopped {
    background: #f8d7da;
    color: #721c24;
}

.controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 15px;
}

.btn {
    padding: 12px;
    border-radius: 8px;
    text-decoration: none;
    text-align: center;
    font-weight: bold;
    transition: all 0.3s;
}

.btn-primary {
    background: #667eea;
    color: white;
}

.btn-success {
    background: #28a745;
    color: white;
}

.btn-danger {
    background: #dc3545;
    color: white;
}

.btn-warning {
    background: #ffc107;
    color: #212529;
}

.btn-info {
    background: #17a2b8;
    color: white;
}

.btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

.mode-selector {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.mode-btn {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    text-decoration: none;
    font-weight: bold;
}

.mode-active {
    background: #667eea;
    color: white;
}

.mode-inactive {
    background: #e0e0e0;
    color: #666;
}

.footer {
    text-align: center;
    margin-top: 20px;
    color: #999;
    font-size: 12px;
}
</style>
"""

LOGIN_TEMPLATE = STYLES + """
<div class="container">
    <h1>🤖 TikTok Checker</h1>
    <h2>Login</h2>
    <form method="post">
        <div class="form-group">
            <input type="text" name="u" placeholder="Username" required>
        </div>
        <div class="form-group">
            <input type="password" name="p" placeholder="Password" required>
        </div>
        <button type="submit">Login</button>
    </form>
    <div class="footer">
        Default: admin / 1234
    </div>
</div>
"""

PANEL_TEMPLATE = STYLES + """
<div class="container">
    <h1>🤖 Dashboard</h1>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <span class="status-badge {{status_class}}">
            {{status_text}}
        </span>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{{c}}</div>
            <div class="stat-label">Checked</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{f}}</div>
            <div class="stat-label">Found</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{w}}</div>
            <div class="stat-label">Workers</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{d}}s</div>
            <div class="stat-label">Delay</div>
        </div>
    </div>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <strong>Mode:</strong> {{mode}} | 
        <strong>Rare Only:</strong> {{rare}}
    </div>
    
    <div class="controls">
        <a href="/start" class="btn btn-success">▶ Start</a>
        <a href="/stop" class="btn btn-danger">⏹ Stop</a>
    </div>
    
    <div class="controls">
        <a href="/fast" class="btn btn-warning">⚡ Fast (0.3s)</a>
        <a href="/slow" class="btn btn-info">🐌 Slow (1.2s)</a>
    </div>
    
    <div class="mode-selector">
        <a href="/mode3" class="mode-btn {{mode3_class}}">3 Letters</a>
        <a href="/mode4" class="mode-btn {{mode4_class}}">4 Letters</a>
    </div>
    
    <div class="controls">
        <a href="/rare" class="btn btn-primary">🎯 Toggle Rare Only</a>
    </div>
    
    <div class="footer">
        TikTok Username Checker Bot
    </div>
</div>
"""

def auth():
    return "user" in session

@app.route('/', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]
        if u in users and users[u] == p:
            session["user"] = u
            return redirect("/panel")
    return LOGIN_TEMPLATE

@app.route('/panel')
def panel():
    if not auth():
        return redirect("/")
    
    mode_str = "3 Letters" if USE_3 else "4 Letters"
    status_text = "🟢 Running" if stats.running else "🔴 Stopped"
    status_class = "status-running" if stats.running else "status-stopped"
    mode3_class = "mode-active" if USE_3 else "mode-inactive"
    mode4_class = "mode-active" if not USE_3 else "mode-inactive"
    
    return render_template_string(PANEL_TEMPLATE,
                                  mode=mode_str,
                                  c=stats.checked,
                                  f=stats.found,
                                  w=stats.workers,
                                  d=stats.delay,
                                  rare="ON" if ONLY_RARE else "OFF",
                                  status_text=status_text,
                                  status_class=status_class,
                                  mode3_class=mode3_class,
                                  mode4_class=mode4_class)

def run_async_loop():
    asyncio.run(loop())

@app.route('/start')
def start():
    if not auth():
        return redirect("/")
    if not stats.running:
        stats.running = True
        threading.Thread(target=run_async_loop, daemon=True).start()
    return redirect("/panel")

@app.route('/stop')
def stop():
    if not auth():
        return redirect("/")
    stats.running = False
    return redirect("/panel")

@app.route('/fast')
def fast():
    if not auth():
        return redirect("/")
    stats.delay = 0.3
    return redirect("/panel")

@app.route('/slow')
def slow():
    if not auth():
        return redirect("/")
    stats.delay = 1.2
    return redirect("/panel")

@app.route('/mode3')
def m3():
    global USE_3
    if not auth():
        return redirect("/")
    USE_3 = True
    return redirect("/panel")

@app.route('/mode4')
def m4():
    global USE_3
    if not auth():
        return redirect("/")
    USE_3 = False
    return redirect("/panel")

@app.route('/rare')
def rare():
    global ONLY_RARE
    if not auth():
        return redirect("/")
    ONLY_RARE = not ONLY_RARE
    return redirect("/panel")

PORT = int(os.environ.get("PORT", 10000))

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")

# ===============================
# 🤖 TELEGRAM
# ===============================
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 System Ready\n\n"
        f"🌐 Web Panel:\n{RENDER_URL}\n\n"
        f"Commands:\n"
        f"/status - Show stats\n"
        f"/mode3 - 3 letters\n"
        f"/mode4 - 4 letters\n"
        f"/url - Get web panel URL"
    )

async def url_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🌐 Web Panel:\n{RENDER_URL}")

async def status_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = "3 Letters" if USE_3 else "4 Letters"
    await update.message.reply_text(
        f"📊 Status:\n"
        f"Mode: {mode}\n"
        f"Checked: {stats.checked}\n"
        f"Found: {stats.found}\n"
        f"Running: {'Yes' if stats.running else 'No'}"
    )

async def mode3_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USE_3
    USE_3 = True
    await update.message.reply_text("✅ Switched to 3 Letters mode")

async def mode4_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USE_3
    USE_3 = False
    await update.message.reply_text("✅ Switched to 4 Letters mode")

def main():
    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start_bot))
    bot.add_handler(CommandHandler("url", url_bot))
    bot.add_handler(CommandHandler("status", status_bot))
    bot.add_handler(CommandHandler("mode3", mode3_bot))
    bot.add_handler(CommandHandler("mode4", mode4_bot))
    bot.run_polling()

if __name__ == "__main__":
    main()
