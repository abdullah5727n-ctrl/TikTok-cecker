import logging, random, string, asyncio, threading, aiohttp, json, os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===============================
# ✅ قراءة المتغيرات من البيئة (Render Environment Variables)
TOKEN = os.environ.get("TOKEN", "8723464858:AAEVoU_oBDP-6WXQYU6ZbcFajjoXD0lObWA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6890999007"))

USERS_FILE = "users.json"
AI_FILE = "ai.json"
HITS_FILE = "hits.txt"

USE_3 = True
ONLY_RARE = True

# ===============================
# 👥 USERS SYSTEM
# ===============================
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"admin": os.environ.get("ADMIN_PASS", "1234")}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

users = load_users()

# ===============================
# 🧠 AI
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
# 🌐 WEB PANEL
# ===============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

LOGIN = """
<form method='post'>
<h2>Login</h2>
<input name='u' placeholder='user'><br>
<input name='p' type='password'><br>
<button>Login</button>
</form>
"""

PANEL = """
<h1>🤖 Dashboard</h1>
<p>Mode: {{mode}}</p>
<p>Checked: {{c}}</p>
<p>Found: {{f}}</p>
<p>Workers: {{w}}</p>
<p>Delay: {{d}}</p>
<p>Only Rare: {{rare}}</p>

<a href='/start'>Start</a> |
<a href='/stop'>Stop</a><br><br>

<a href='/fast'>Fast</a> |
<a href='/slow'>Slow</a><br><br>

<a href='/mode3'>3 Letters</a> |
<a href='/mode4'>4 Letters</a><br><br>

<a href='/rare'>Toggle Rare Only</a>
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
    return LOGIN

@app.route('/panel')
def panel():
    if not auth():
        return redirect("/")
    mode_str = "3 Letters" if USE_3 else "4 Letters"
    return render_template_string(PANEL,
                                  mode=mode_str,
                                  c=stats.checked, 
                                  f=stats.found,
                                  w=stats.workers, 
                                  d=stats.delay,
                                  rare="ON" if ONLY_RARE else "OFF")

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

# ✅ Render يحدد المنفذ تلقائياً
PORT = int(os.environ.get("PORT", 10000))

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# ✅ الحصول على رابط Render
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
