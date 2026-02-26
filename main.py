import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os
import re
import datetime
import pytz
import ssl
import certifi
from dotenv import load_dotenv

# ────────────────────────────────────────
# LOAD .ENV
# ────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, 'a2m.env')
load_dotenv(dotenv_path=dotenv_path)

print(f"📁 Mencari .env di: {dotenv_path}")
print(f"📄 File .env ditemukan: {os.path.exists(dotenv_path)}")

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID_RAW = os.getenv('CHANNEL_ID')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN tidak ditemukan di file .env!")
if not CHANNEL_ID_RAW:
    raise ValueError("CHANNEL_ID tidak ditemukan di file .env!")

CHANNEL_ID = int(CHANNEL_ID_RAW)

# ────────────────────────────────────────
# SETUP BOT
# ────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ────────────────────────────────────────
# HELPER: SSL CONNECTOR
# ────────────────────────────────────────
def make_connector():
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    return aiohttp.TCPConnector(ssl=ssl_ctx)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; A2MBot/1.0)",
    "Accept": "application/json",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8"
}

# ────────────────────────────────────────
# FUNGSI: ON THIS DAY (Wikipedia ID)
# ────────────────────────────────────────
async def get_on_this_day():
    try:
        today = datetime.datetime.now()
        month = today.month
        day = today.day

        # Wikipedia ID tidak punya endpoint onthisday, langsung pakai EN
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"

        async with aiohttp.ClientSession(connector=make_connector()) as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers=HEADERS
            ) as res:
                print(f"[OnThisDay] Status: {res.status}, URL: {url}")
                if res.status != 200:
                    return f"Gagal mengambil data (status {res.status})."

                raw = await res.text()
                print(f"[OnThisDay] Response preview: {raw[:300]}")

                import json
                data = json.loads(raw)

        events = data.get("events", data.get("onthisday", []))
        print(f"[OnThisDay] Total events ditemukan: {len(events)}")

        if not events:
            return "Tidak ada data peristiwa hari ini."

        result = []
        for e in events[:3]:
            year = e.get("year", "????")
            text = re.sub(r'\[\d+\]', '', e.get("text", "")).strip()
            if len(text) > 100:
                text = text[:100] + "..."

            pages = e.get("pages", [])
            if pages:
                page_title = pages[0].get("title", "").replace(" ", "_")
                link = f"https://en.wikipedia.org/wiki/{page_title}"
                result.append(
                    f"**{year}** — {text}\n"
                    f"[Baca Selengkapnya...]({link})"
                )
            else:
                result.append(f"**{year}** — {text}")

        return "\n\n".join(result)

    except Exception as e:
        print(f"[OnThisDay] Exception: {e}")
        return f"Gagal mengambil data: {e}"



# ────────────────────────────────────────
# FUNGSI: WIKIPEDIA TRENDING
# ────────────────────────────────────────
async def get_news():
    try:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
            f"id.wikipedia/all-access/"
            f"{yesterday.year}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}"
        )

        skip = {
            "Halaman_Utama", "Main_Page", "Special:Search", "-",
            "Wikipedia:Featured_pictures", "Special:Random",
            "Portal:Current_events", "Wikipedia", ".xxx",
            "Special:Book", "Help:Contents", "Istimewa:Pencarian"
        }

        async with aiohttp.ClientSession(connector=make_connector()) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=HEADERS) as res:
                print(f"[Wikipedia Trending ID] Status: {res.status}")

                # Fallback ke Wikipedia English jika ID tidak ada data
                if res.status != 200:
                    url_en = (
                        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
                        f"en.wikipedia/all-access/"
                        f"{yesterday.year}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}"
                    )
                    async with session.get(url_en, timeout=aiohttp.ClientTimeout(total=15), headers=HEADERS) as res_en:
                        print(f"[Wikipedia Trending EN] Status: {res_en.status}")
                        if res_en.status != 200:
                            return f"API tidak merespons."
                        data = await res_en.json(content_type=None)
                        wiki_base = "https://en.wikipedia.org/wiki/"
                        summary_base = "https://en.wikipedia.org/api/rest_v1/page/summary/"
                else:
                    data = await res.json(content_type=None)
                    wiki_base = "https://id.wikipedia.org/wiki/"
                    summary_base = "https://id.wikipedia.org/api/rest_v1/page/summary/"

            articles = data.get("items", [{}])[0].get("articles", [])
            filtered = [a for a in articles if a.get("article") not in skip][:3]

            if not filtered:
                return "Tidak ada data Wikipedia tersedia."

            async def fetch_summary(article):
                raw_title = article.get("article", "")
                title = raw_title.replace("_", " ")
                views = f"{article.get('views', 0):,}"
                link = f"{wiki_base}{raw_title}"

                async with session.get(
                    f"{summary_base}{raw_title}",
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers=HEADERS
                ) as r:
                    s = await r.json(content_type=None)
                    summary = s.get("extract", "Tidak ada ringkasan.")
                    if len(summary) > 120:
                        summary = summary[:120] + "..."

                return (
                    f"**{title}**\n"
                    f"_{summary}_\n"
                    f"👁️ {views} views kemarin\n"
                    f"[Baca Selengkapnya...]({link})"
                )

            results = await asyncio.gather(*[fetch_summary(a) for a in filtered])

        return "\n\n".join(results)

    except Exception as e:
        print(f"[Wikipedia] Exception: {e}")
        return f"Gagal mengambil data Wikipedia: {e}"


# ────────────────────────────────────────
# HELPER: BUILD EMBED
# ────────────────────────────────────────
async def build_embed(title_prefix="📆 Daily Update"):
    on_this_day, news = await asyncio.gather(
        get_on_this_day(),
        get_news()
    )
    embed = discord.Embed(
        title=f"{title_prefix} — {datetime.datetime.now().strftime('%d %B %Y')}",
        description="Berikut informasi harian dari **A2M Information**!",
        color=0x5865F2
    )
    embed.add_field(name="🗓️ On This Day", value=on_this_day, inline=False)
    embed.add_field(name="📖 Artikel Wikipedia Trending Hari Ini", value=news, inline=False)
    embed.set_footer(text="DayBot • A2M Information")
    return embed


# ────────────────────────────────────────
# TASK: KIRIM OTOMATIS JAM 07.00 WIB
# ────────────────────────────────────────
@tasks.loop(time=datetime.time(
    hour=7, minute=0, second=0,
    tzinfo=pytz.timezone("Asia/Jakarta")
))
async def daily_update():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print(f"[Daily Update] Mengirim update harian...")
        embed = await build_embed("📆 Daily Update")
        await channel.send(embed=embed)
    else:
        print(f"⚠️ Channel ID {CHANNEL_ID} tidak ditemukan!")


# ────────────────────────────────────────
# EVENT: BOT SIAP
# ────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai: {bot.user}")
    print(f"📡 Terhubung ke {len(bot.guilds)} server")
    print(f"📢 Channel target ID: {CHANNEL_ID}")
    print(f"⏰ Daily update dijadwalkan jam 07.00 WIB")
    if not daily_update.is_running():
        daily_update.start()


# ────────────────────────────────────────
# COMMAND: !today
# ────────────────────────────────────────
@bot.command()
async def today(ctx):
    await ctx.send("⏳ Mengambil data, mohon tunggu...")
    embed = await build_embed("📆 Info Hari Ini")
    await ctx.send(embed=embed)


# ────────────────────────────────────────
# COMMAND: !ping
# ────────────────────────────────────────
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Bot aktif. Latency: {round(bot.latency * 1000)}ms")


# ────────────────────────────────────────
# JALANKAN BOT
# ────────────────────────────────────────
bot.run(TOKEN)
