import requests
import time
import sqlite3
import threading
import random
import logging
import asyncio
from telethon import TelegramClient, events

# ============================================================
# ATACHER SELF-BOT - COMPLETE (NO GIF/VOICE ATTACK)
# ============================================================
SELF_OWNER_ID = 7557475320
DB_FILE = "infinity.db"
DEFAULT_DELAY = 4.0
SPAM_DELAY = 5.0
DEFAULT_TAG = "Enemy"

API_ID = 33209823
API_HASH = "4ee678e1e9a93a6c50b366424bed8773"
PHONE = "+989201548900"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

db_lock = threading.Lock()

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        self._lock = db_lock
        self._initialize_database()

    def _get_connection(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _initialize_database(self):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS targets(user_id INTEGER PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS insults(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS enemies(user_id INTEGER PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
            """)
            conn.commit()
            conn.close()

    def get_setting(self, key, default=None):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = c.fetchone()
            conn.close()
            return row[0] if row else default

    def set_setting(self, key, value):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))
            conn.commit()
            conn.close()

    def execute_query(self, sql, params=None):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            if params: c.execute(sql, params)
            else: c.execute(sql)
            conn.commit()
            conn.close()

    def fetch_all(self, sql):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            c.execute(sql)
            result = c.fetchall()
            conn.close()
            return result

    def fetch_one(self, sql, params=None):
        with self._lock:
            conn = self._get_connection()
            c = conn.cursor()
            if params: c.execute(sql, params)
            else: c.execute(sql)
            result = c.fetchone()
            conn.close()
            return result

db = DatabaseManager(DB_FILE)

class TargetManager:
    @staticmethod
    def add_target(user_id): db.execute_query("INSERT OR IGNORE INTO targets VALUES (?)", (user_id,))
    @staticmethod
    def remove_target(user_id): db.execute_query("DELETE FROM targets WHERE user_id = ?", (user_id,))
    @staticmethod
    def clear_targets(): db.execute_query("DELETE FROM targets")
    @staticmethod
    def get_targets(): return [row[0] for row in db.fetch_all("SELECT user_id FROM targets")]
    @staticmethod
    def get_count():
        row = db.fetch_one("SELECT COUNT(*) FROM targets")
        return row[0] if row else 0

class InsultManager:
    @staticmethod
    def add_insult(text): db.execute_query("INSERT OR IGNORE INTO insults (text) VALUES (?)", (text.strip(),))
    @staticmethod
    def add_bulk(texts):
        count = 0
        for text in texts:
            text = text.strip()
            if text:
                try: db.execute_query("INSERT OR IGNORE INTO insults (text) VALUES (?)", (text,)); count += 1
                except: pass
        return count
    @staticmethod
    def get_insults(): return [row[0] for row in db.fetch_all("SELECT text FROM insults ORDER BY RANDOM()")]
    @staticmethod
    def get_all_insults(): return [row[0] for row in db.fetch_all("SELECT text FROM insults")]
    @staticmethod
    def get_count():
        row = db.fetch_one("SELECT COUNT(*) FROM insults")
        return row[0] if row else 0
    @staticmethod
    def clear_insults(): db.execute_query("DELETE FROM insults")

class EnemyManager:
    @staticmethod
    def add_enemy(user_id): db.execute_query("INSERT OR IGNORE INTO enemies VALUES (?)", (user_id,))
    @staticmethod
    def remove_enemy(user_id): db.execute_query("DELETE FROM enemies WHERE user_id = ?", (user_id,))
    @staticmethod
    def get_enemies(): return [row[0] for row in db.fetch_all("SELECT user_id FROM enemies")]
    @staticmethod
    def is_enemy(user_id): return db.fetch_one("SELECT 1 FROM enemies WHERE user_id = ?", (user_id,)) is not None
    @staticmethod
    def get_count():
        row = db.fetch_one("SELECT COUNT(*) FROM enemies")
        return row[0] if row else 0

class AdminManager:
    @staticmethod
    def add_admin(user_id): db.execute_query("INSERT OR IGNORE INTO admins VALUES (?)", (user_id,))
    @staticmethod
    def remove_admin(user_id): db.execute_query("DELETE FROM admins WHERE user_id = ?", (user_id,))
    @staticmethod
    def get_admins(): return [row[0] for row in db.fetch_all("SELECT user_id FROM admins")]
    @staticmethod
    def is_admin(user_id): return db.fetch_one("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) is not None

class SettingsManager:
    @staticmethod
    def get_tag(): return db.get_setting("tag", DEFAULT_TAG)
    @staticmethod
    def set_tag(tag): db.set_setting("tag", tag)
    @staticmethod
    def get_delay(): return float(db.get_setting("delay", DEFAULT_DELAY))
    @staticmethod
    def set_delay(delay): db.set_setting("delay", str(delay))

# ============================================================
# HELP PANELS
# ============================================================
class HelpPanelManager:
    @staticmethod
    def get_panel(panel_number):
        panels = {
            "0": """<b>ATACHER SELF-BOT - HELP MENU</b>

<code>help 1</code>  --  Bot Commands
<code>help 2</code>  --  Target and Mention
<code>help 3</code>  --  Enemy and Admin
<code>help 4</code>  --  Insult Management
<code>help 5</code>  --  Attack Settings
<code>help 6</code>  --  Spam and Forward
<code>help 7</code>  --  System and Profile
<code>help 8</code>  --  Full Command List""",

            "1": """<b>HELP 1/8 -- BOT COMMANDS</b>

<code>ping</code>  --  Check response time
<code>bot</code>  --  Display bot status
<code>help</code>  --  Show main help menu
<code>help 1</code> to <code>help 8</code>  --  Navigate panels

<b>NEXT:</b> <code>help 2</code>""",

            "2": """<b>HELP 2/8 -- TARGET AND MENTION</b>

<code>setid</code>  --  Reply to add target
<code>delid</code>  --  Reply to remove target
<code>delallid</code>  --  Clear all targets
<code>taglist</code>  --  View target list
<code>settag [word]</code>  --  Set mention tag
<code>start</code>  --  Launch attack
<code>stop</code>  --  Stop attack

<b>NEXT:</b> <code>help 3</code>""",

            "3": """<b>HELP 3/8 -- ENEMY AND ADMIN</b>

<b>ENEMY:</b>
<code>setenemy</code>  --  Reply to set as enemy
<code>delenemy</code>  --  Reply to remove enemy
<code>enemylist</code>  --  View enemy list

<b>ADMIN:</b>
<code>setadmin</code>  --  Reply to add admin
<code>deladmin</code>  --  Reply to remove admin
<code>adminlist</code>  --  View admin list

<b>NEXT:</b> <code>help 4</code>""",

            "4": """<b>HELP 4/8 -- INSULT MANAGEMENT</b>

<code>addinsult [text]</code>  --  Add new insult
<code>upload</code>  --  Reply to .txt file
<code>insults</code>  --  View insult list
<code>clearinsults</code>  --  Clear all insults

<b>NEXT:</b> <code>help 5</code>""",

            "5": """<b>HELP 5/8 -- ATTACK SETTINGS</b>

<code>settag [word]</code>  --  Set mention tag
<code>settime [seconds]</code>  --  Set delay
<code>start</code>  --  Launch attack
<code>stop</code>  --  Stop attack immediately

<b>NEXT:</b> <code>help 6</code>""",

            "6": """<b>HELP 6/8 -- SPAM AND FORWARD</b>

<b>SPAM:</b>
<code>spam [count] [text]</code>  --  Spam message

<b>FORWARD:</b>
<code>savefwd</code>  --  Reply to save message
<code>fwdlist</code>  --  View forwards count
<code>clearfwd</code>  --  Clear all forwards
<code>startfwd</code>  --  Start forward spam
<code>stopfwd</code>  --  Stop forward spam

<b>NEXT:</b> <code>help 7</code>""",

            "7": """<b>HELP 7/8 -- SYSTEM AND PROFILE</b>

<code>ping</code>  --  Check response speed
<code>bot</code>  --  Display bot status
<code>settag [word]</code>  --  Set mention tag
<code>settime [sec]</code>  --  Set attack delay
<code>help</code>  --  Show help menu

<b>NEXT:</b> <code>help 8</code>""",

            "8": """<b>HELP 8/8 -- FULL COMMAND LIST</b>

<b>TARGET:</b>  <code>setid</code> <code>delid</code> <code>delallid</code> <code>taglist</code>
<b>ENEMY:</b>   <code>setenemy</code> <code>delenemy</code> <code>enemylist</code>
<b>ADMIN:</b>   <code>setadmin</code> <code>deladmin</code> <code>adminlist</code>
<b>INSULT:</b>  <code>addinsult</code> <code>upload</code> <code>insults</code> <code>clearinsults</code>
<b>SPAM:</b>    <code>spam [count] [text]</code>
<b>FORWARD:</b> <code>savefwd</code> <code>fwdlist</code> <code>clearfwd</code> <code>startfwd</code> <code>stopfwd</code>
<b>ATTACK:</b>  <code>settag</code> <code>settime</code> <code>start</code> <code>stop</code>
<b>SYSTEM:</b>  <code>ping</code> <code>bot</code> <code>help</code>

<b>BACK:</b> <code>help</code>"""
        }
        return panels.get(str(panel_number), panels["0"])

# ============================================================
# SELF-BOT
# ============================================================
class SelfBot:
    def __init__(self):
        self.client = None
        self.tag = SettingsManager.get_tag()
        self.delay = SettingsManager.get_delay()
        self.is_attacking = False
        self.is_fwd_attacking = False
        self.reply_id = None
        self.forward_messages = []
        # Anti-flood system
        self.message_count = 0
        self.last_reset = time.time()
        self.flood_lock = threading.Lock()

    def check_flood(self):
        """Anti-flood: max 20 messages per minute"""
        with self.flood_lock:
            now = time.time()
            if now - self.last_reset > 60:
                self.message_count = 0
                self.last_reset = now
            self.message_count += 1
            if self.message_count > 20:
                wait = 60 - (now - self.last_reset)
                if wait > 0:
                    log.info(f"Anti-flood: waiting {wait:.0f}s")
                    return wait
            return 0

    async def safe_send(self, chat_id, text, reply_id=None):
        """Send with anti-flood delay"""
        wait = self.check_flood()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            if reply_id:
                await self.client.send_message(chat_id, text, reply_to=reply_id, parse_mode="html")
            else:
                await self.client.send_message(chat_id, text, parse_mode="html")
        except: pass

    async def attack_loop(self, chat_id):
        while self.is_attacking:
            targets = TargetManager.get_targets()
            insults = InsultManager.get_insults()
            if not targets or not insults:
                await asyncio.sleep(0.5)
                continue
            msg = f"{random.choice(insults)}\n" + " ".join([f'<a href="tg://user?id={u}">{self.tag}</a>' for u in targets])
            await self.safe_send(chat_id, msg, reply_id=self.reply_id)
            await asyncio.sleep(self.delay)

    async def fwd_attack_loop(self, chat_id):
        while self.is_fwd_attacking:
            if not self.forward_messages:
                await asyncio.sleep(0.5)
                continue
            msg_data = random.choice(self.forward_messages)
            try:
                await self.client.forward_messages(chat_id, msg_data["message_id"], msg_data["chat_id"])
            except: pass
            await asyncio.sleep(self.delay)

    async def handle_message(self, event):
        chat_id = event.chat_id
        sender = event.sender_id
        txt = event.raw_text.strip() if event.raw_text else ""
        reply = await event.get_reply_message()
        reply_id = reply.id if reply else None
        reply_sender = reply.sender_id if reply else None
        document = event.document

        if sender != SELF_OWNER_ID and not AdminManager.is_admin(sender):
            if EnemyManager.is_enemy(sender):
                ins = InsultManager.get_insults()
                if ins:
                    await event.reply(random.choice(ins))
            return

        cmd = txt.lower()

        if cmd == "help":
            await event.edit(HelpPanelManager.get_panel("0"), parse_mode="html")
        elif cmd.startswith("help "):
            await event.edit(HelpPanelManager.get_panel(cmd[5:]), parse_mode="html")

        elif cmd == "ping":
            t = time.time()
            await self.safe_send(chat_id, f"<b>PONG: {int((time.time()-t)*1000)}ms</b>")
        elif cmd == "bot":
            await self.safe_send(chat_id, "<b>ONLINE</b>", reply_id)

        elif cmd == "setid" and reply_sender:
            TargetManager.add_target(reply_sender)
            await self.safe_send(chat_id, f"<b>Target added:</b> <code>{reply_sender}</code>")
        elif cmd == "delid" and reply_sender:
            TargetManager.remove_target(reply_sender)
            await self.safe_send(chat_id, f"<b>Target removed:</b> <code>{reply_sender}</code>")
        elif cmd == "delallid":
            TargetManager.clear_targets()
            await self.safe_send(chat_id, "<b>All targets cleared</b>")
        elif cmd == "taglist":
            t = TargetManager.get_targets()
            if t:
                txt = f"<b>Target List ({len(t)})</b>\n"
                for uid in t:
                    txt += f'<a href="tg://user?id={uid}">{self.tag}</a> <code>{uid}</code>\n'
                await self.safe_send(chat_id, txt)
            else:
                await self.safe_send(chat_id, "<b>No targets</b>")

        elif cmd == "setenemy" and reply_sender:
            EnemyManager.add_enemy(reply_sender)
            await self.safe_send(chat_id, f"<b>Enemy added:</b> <code>{reply_sender}</code>")
        elif cmd == "delenemy" and reply_sender:
            EnemyManager.remove_enemy(reply_sender)
            await self.safe_send(chat_id, f"<b>Enemy removed:</b> <code>{reply_sender}</code>")
        elif cmd == "enemylist":
            e = EnemyManager.get_enemies()
            if e:
                txt = f"<b>Enemy List ({len(e)})</b>\n"
                for uid in e:
                    txt += f'<a href="tg://user?id={uid}">{self.tag}</a> <code>{uid}</code>\n'
                await self.safe_send(chat_id, txt)
            else:
                await self.safe_send(chat_id, "<b>No enemies</b>")

        elif cmd == "setadmin" and reply_sender:
            AdminManager.add_admin(reply_sender)
            await self.safe_send(chat_id, f"<b>Admin added:</b> <code>{reply_sender}</code>")
        elif cmd == "deladmin" and reply_sender:
            AdminManager.remove_admin(reply_sender)
            await self.safe_send(chat_id, f"<b>Admin removed:</b> <code>{reply_sender}</code>")
        elif cmd == "adminlist":
            admins = AdminManager.get_admins()
            if admins:
                txt = "<b>Admin List</b>\n"
                for a in admins: txt += f"<code>{a}</code>\n"
                await self.safe_send(chat_id, txt)
            else:
                await self.safe_send(chat_id, "<b>No admins</b>")

        elif cmd.startswith("addinsult "):
            InsultManager.add_insult(txt[10:])
            await self.safe_send(chat_id, "<b>Insult added</b>")
        elif cmd == "upload":
            fd = document or (reply.document if reply else None)
            if fd:
                path = await self.client.download_media(fd)
                try:
                    with open(path, 'r') as f:
                        lines = [l.strip() for l in f.readlines() if l.strip()]
                    InsultManager.add_bulk(lines)
                    await self.safe_send(chat_id, f"<b>{len(lines)} insults uploaded</b>")
                except: pass
        elif cmd == "insults":
            ins = InsultManager.get_all_insults()
            if ins:
                txt = f"<b>Insult List ({len(ins)})</b>\n"
                for i, text in enumerate(ins, 1): txt += f"{i}. {text}\n"
                await self.safe_send(chat_id, txt)
            else:
                await self.safe_send(chat_id, "<b>No insults</b>")
        elif cmd == "clearinsults":
            InsultManager.clear_insults()
            await self.safe_send(chat_id, "<b>Insults cleared</b>")

        elif cmd == "savefwd" and reply:
            self.forward_messages.append({"chat_id": reply.chat_id, "message_id": reply.id})
            await self.safe_send(chat_id, "<b>Forward message saved</b>")
        elif cmd == "fwdlist":
            await self.safe_send(chat_id, f"<b>Saved Forwards: {len(self.forward_messages)}</b>")
        elif cmd == "clearfwd":
            self.forward_messages = []; await self.safe_send(chat_id, "<b>Forwards cleared</b>")
        elif cmd == "startfwd":
            if not self.is_fwd_attacking and self.forward_messages:
                self.is_fwd_attacking = True
                asyncio.create_task(self.fwd_attack_loop(chat_id))
                await self.safe_send(chat_id, "<b>Forward spam started</b>")
        elif cmd == "stopfwd":
            self.is_fwd_attacking = False
            await self.safe_send(chat_id, "<b>Forward spam stopped</b>")

        elif cmd.startswith("settag "):
            self.tag = txt[7:]; SettingsManager.set_tag(txt[7:])
            await self.safe_send(chat_id, f"<b>Tag set to: {txt[7:]}</b>")
        elif cmd.startswith("settime "):
            try:
                d = float(txt[8:])
                if d > 0: self.delay = d; SettingsManager.set_delay(d); await self.safe_send(chat_id, f"<b>Delay set to: {d}s</b>")
            except: pass

        elif cmd == "start":
            if not self.is_attacking and TargetManager.get_targets() and InsultManager.get_insults():
                self.is_attacking = True
                if reply_id: self.reply_id = reply_id
                asyncio.create_task(self.attack_loop(chat_id))
        elif cmd == "stop":
            self.is_attacking = False; self.reply_id = None

        elif cmd.startswith("spam "):
            parts = cmd[5:].split(" ", 1)
            try:
                count = int(parts[0]); sp = parts[1] if len(parts) > 1 else "SPAM"
                for _ in range(count):
                    if reply_id: await self.safe_send(chat_id, sp, reply_id)
                    else: await self.safe_send(chat_id, sp)
                    await asyncio.sleep(SPAM_DELAY)
            except: pass

    async def start(self):
        self.client = TelegramClient(
            "session_self",
            API_ID,
            API_HASH,
            flood_sleep_threshold=60,
            connection_retries=5,
            retry_delay=5,
            auto_reconnect=True
        )
        await self.client.start(phone=PHONE)
        log.info("Self-bot online!")

        @self.client.on(events.NewMessage)
        async def handler(event):
            await self.handle_message(event)

        await self.client.run_until_disconnected()

async def main():
    sb = SelfBot()
    await sb.start()

if __name__ == "__main__":
    log.info("ATACHER SELF-BOT STARTING...")
    asyncio.run(main())
