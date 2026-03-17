import logging, random, string, asyncio, threading, aiohttp, json, os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===============================
TOKEN = "8723464858:AAG3E5agxn_wYS8q_jTxiFA33ZRyES0WEUo"
ADMIN_ID = 6890999007

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
        json.dump({"admin":"1234"}, open(USERS_FILE,"w"))
    return json.load(open(USERS_FILE))

users = load_users()

# ===============================
# 🧠 AI
# ===============================
class AI:
    def __init__(self):
        self.data={"repeat":1,"sequence":1,"pattern":1,"mirror":1,"random":1}
        if os.path.exists(AI_FILE):
            self.data=json.load(open(AI_FILE))

    def save(self):
        json.dump(self.data, open(AI_FILE,"w"))

    def choose(self):
        total=sum(self.data.values())
        r=random.uniform(0,total)
        s=0
        for k,v in self.data.items():
            if s+v>=r: return k
            s+=v

    def reward(self,p):
        self.data[p]+=2; self.save()

    def punish(self,p):
        self.data[p]=max(1,self.data[p]-0.2)

ai = AI()

# ===============================
class Stats:
    def __init__(self):
        self.checked=0
        self.found=0
        self.running=False
        self.delay=0.5
        self.workers=5

stats = Stats()

# ===============================
def gen(p):
    L=3 if USE_3 else 4
    if p=="repeat":
        c=random.choice(string.ascii_lowercase+string.digits)
        return c*L
    if p=="sequence":
        s=string.ascii_lowercase
        i=random.randint(0,len(s)-L)
        return s[i:i+L]
    if p=="pattern":
        a=random.choice(string.ascii_lowercase)
        b=random.choice(string.digits)
        return (a+b)*(L//2)
    if p=="mirror":
        x=random.choice(string.ascii_lowercase)
        return x+x[::-1]+x if L==3 else x+x[::-1]+x+x[::-1]
    return ''.join(random.choices(string.ascii_lowercase+string.digits,k=L))

def rarity(u):
    if len(set(u))==1: return "🔥 نادر"
    if u==u[::-1]: return "🧬 متناظر"
    return "⭐ عادي"

# ===============================
async def check(session,u):
    try:
        async with session.get(f"https://www.tiktok.com/@{u}",timeout=8) as r:
            return r.status==404
    except: return None

# ===============================
async def worker():
    async with aiohttp.ClientSession() as session:
        while stats.running:
            try:
                p=ai.choose()
                u=gen(p)

                stats.checked+=1
                ok=await check(session,u)

                if ok:
                    r=rarity(u)
                    if (not ONLY_RARE) or "🔥" in r:
                        stats.found+=1
                        ai.reward(p)
                        open(HITS_FILE,"a").write(u+"\n")
                else:
                    ai.punish(p)

            except:
                pass

            await asyncio.sleep(stats.delay)

# ===============================
async def loop():
    while stats.running:
        tasks=[asyncio.create_task(worker()) for _ in range(stats.workers)]
        await asyncio.gather(*tasks)

# ===============================
# 🌐 WEB PANEL
# ===============================
app = Flask(__name__)
app.secret_key="secret123"

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
<p>Checked: {{c}}</p>
<p>Found: {{f}}</p>
<p>Workers: {{w}}</p>
<p>Delay: {{d}}</p>

<a href='/start'>Start</a> |
<a href='/stop'>Stop</a><br><br>

<a href='/fast'>Fast</a> |
<a href='/slow'>Slow</a><br><br>

<a href='/mode3'>3</a> |
<a href='/mode4'>4</a><br><br>

<a href='/rare'>Toggle Rare</a>
"""

def auth():
    return "user" in session

@app.route('/', methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["u"]
        p=request.form["p"]
        if u in users and users[u]==p:
            session["user"]=u
            return redirect("/panel")
    return LOGIN

@app.route('/panel')
def panel():
    if not auth(): return redirect("/")
    return render_template_string(PANEL,
        c=stats.checked,f=stats.found,
        w=stats.workers,d=stats.delay)

@app.route('/start')
def start():
    if not auth(): return redirect("/")
    if not stats.running:
        stats.running=True
        asyncio.run(loop())
    return redirect("/panel")

@app.route('/stop')
def stop():
    stats.running=False
    return redirect("/panel")

@app.route('/fast')
def fast():
    stats.delay=0.3; return redirect("/panel")

@app.route('/slow')
def slow():
    stats.delay=1.2; return redirect("/panel")

@app.route('/mode3')
def m3():
    global USE_3; USE_3=True
    return redirect("/panel")

@app.route('/mode4')
def m4():
    global USE_3; USE_3=False
    return redirect("/panel")

@app.route('/rare')
def rare():
    global ONLY_RARE; ONLY_RARE=not ONLY_RARE
    return redirect("/panel")

threading.Thread(target=lambda: app.run(host='0.0.0.0',port=8080),daemon=True).start()

# ===============================
# 🤖 TELEGRAM
# ===============================
async def start_bot(update,context):
    await update.message.reply_text("🤖 System Ready")

def main():
    bot=Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start",start_bot))
    bot.run_polling()

if __name__=="__main__":
    main()