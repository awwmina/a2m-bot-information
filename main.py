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
import platform
import json
import random
import feedparser
from dotenv import load_dotenv

# ────────────────────────────────────────
# LOAD .ENV
# ────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, 'a2m.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("📄 Berjalan di local mode")
else:
    print("☁️ Berjalan di cloud mode (Railway)")

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID_RAW = os.getenv('CHANNEL_ID')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN tidak ditemukan!")
if not CHANNEL_ID_RAW:
    raise ValueError("CHANNEL_ID tidak ditemukan!")

CHANNEL_ID = int(CHANNEL_ID_RAW)

# ────────────────────────────────────────
# SETUP BOT
# ────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; A2MBot/1.0)",
    "Accept": "application/json, text/html, application/xhtml+xml",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8"
}

RSS_FEEDS = [
    ("https://www.antaranews.com/rss/top-news", "Antara Top News"),
    ("https://news.detik.com/berita/rss", "Detik News"),
    ("https://www.antaranews.com/rss/ekonomi", "Antara Ekonomi"),
]

# ────────────────────────────────────────
# HELPER: SSL CONNECTOR
# ────────────────────────────────────────
def make_connector():
    if platform.system() == "Darwin":
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        return aiohttp.TCPConnector(ssl=ssl_ctx)
    else:
        return aiohttp.TCPConnector()

# ────────────────────────────────────────
# DATA: FUN FACTS INDONESIA
# ────────────────────────────────────────
FUNFACTS_ID = [
    "Indonesia adalah negara kepulauan terbesar di dunia dengan lebih dari 17.000 pulau.",
    "Komodo, kadal terbesar di dunia, hanya ditemukan di Indonesia.",
    "Indonesia memiliki lebih dari 700 bahasa daerah dari 300 kelompok etnis.",
    "Borobudur adalah candi Buddha terbesar di dunia, terletak di Jawa Tengah.",
    "Rafflesia arnoldii, bunga terbesar di dunia, tumbuh di hutan Sumatera dan Kalimantan.",
    "Indonesia terletak di Ring of Fire dan memiliki sekitar 400 gunung berapi.",
    "Pulau Jawa adalah pulau dengan kepadatan penduduk tertinggi di dunia.",
    "Indonesia memiliki garis pantai sepanjang lebih dari 54.000 km, terpanjang kedua di dunia.",
    "Orang utan yang berarti 'manusia hutan' dalam bahasa Melayu hanya ditemukan di Sumatera dan Kalimantan.",
    "Batik Indonesia telah diakui UNESCO sebagai Warisan Budaya Takbenda sejak tahun 2009.",
    "Gunung Jayawijaya di Papua memiliki salju abadi meskipun berada tepat di garis khatulistiwa.",
    "Danau Toba di Sumatera adalah danau vulkanik terbesar di dunia.",
    "Indonesia adalah penghasil kopi terbesar ketiga di dunia.",
    "Indonesia adalah produsen kelapa sawit dan nikel terbesar di dunia.",
    "Keris, senjata tradisional Indonesia, telah diakui UNESCO sebagai warisan budaya dunia.",
    "Angklung, alat musik tradisional Sunda, telah diakui UNESCO sebagai warisan budaya.",
    "Wayang kulit Indonesia telah diakui sebagai Warisan Budaya Takbenda oleh UNESCO.",
    "Indonesia memiliki lebih dari 1.300 spesies burung, salah satu tertinggi di dunia.",
    "Nasi goreng dan rendang masuk dalam daftar makanan terlezat di dunia versi CNN.",
    "Indonesia adalah negara dengan populasi Muslim terbesar di dunia.",
    "Candi Prambanan adalah kompleks candi Hindu terbesar di Indonesia.",
    "Tari Saman dari Aceh telah diakui UNESCO sebagai warisan budaya tak benda.",
    "Indonesia menghasilkan sekitar 10% dari total spesies tanaman di seluruh dunia.",
    "Indonesia adalah negara demokrasi terbesar ketiga di dunia.",
    "Segitiga Terumbu Karang yang mencakup Indonesia memiliki keanekaragaman laut tertinggi di dunia.",
    "Indonesia adalah salah satu dari sedikit negara yang memiliki harimau, gajah, dan orangutan sekaligus.",
    "Bahasa Indonesia digunakan oleh lebih dari 270 juta penduduk sebagai bahasa persatuan.",
    "Indonesia adalah pengekspor timah terbesar di dunia.",
    "Gunung Krakatau yang meletus pada 1883 menghasilkan ledakan terkeras yang pernah tercatat dalam sejarah.",
    "Indonesia memiliki lebih dari 400 suku bangsa dengan tradisi dan budaya yang unik.",
]

# ────────────────────────────────────────
# FUNGSI: FUN FACT HARIAN
# ────────────────────────────────────────
async def get_fun_fact():
    today = datetime.datetime.now()
    index = today.timetuple().tm_yday % len(FUNFACTS_ID)
    return f"💡 {FUNFACTS_ID[index]}"

# ────────────────────────────────────────
# FUNGSI: ON THIS DAY
# ────────────────────────────────────────
async def get_on_this_day():
    try:
        today = datetime.datetime.now()
        url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{today.month}/{today.day}"

        async with aiohttp.ClientSession(connector=make_connector()) as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers=HEADERS
            ) as res:
                print(f"[OnThisDay] Status: {res.status}")
                if res.status != 200:
                    return f"Gagal mengambil data (status {res.status})."
                data = json.loads(await res.text())

        events = data.get("events", data.get("onthisday", []))[:5]
        if not events:
            return "Tidak ada data peristiwa hari ini."

        result = []
        for e in events:
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
# FUNGSI: BERITA TERBARU (RSS Feed)
# ────────────────────────────────────────
async def get_news():
    try:
        all_news = []

        async with aiohttp.ClientSession(connector=make_connector()) as session:
            for feed_url, source_name in RSS_FEEDS:
                try:
                    async with session.get(
                        feed_url,
                        timeout=aiohttp.ClientTimeout(total=10),
                        headers=HEADERS
                    ) as res:
                        print(f"[RSS {source_name}] Status: {res.status}")
                        if res.status != 200:
                            continue

                        content = await res.text()
                        feed = feedparser.parse(content)

                        if not feed.entries:
                            continue

                        for entry in feed.entries[:2]:
                            title = entry.get("title", "Tanpa Judul").strip()
                            if len(title) > 55:
                                title = title[:55] + "..."
                            link = entry.get("link", "#")
                            summary = entry.get("summary", entry.get("description", ""))
                            summary = re.sub(r'<.*?>', '', summary).strip()
                            if len(summary) > 55:
                                summary = summary[:55] + "..."

                            all_news.append((title, summary, link, source_name))

                            if len(all_news) >= 3:
                                break

                except Exception as feed_error:
                    print(f"[RSS {source_name}] Exception: {feed_error}")
                    continue

                if len(all_news) >= 3:
                    break

        print(f"[RSS] Total berita: {len(all_news)}")

        if not all_news:
            return "Tidak ada berita tersedia saat ini."

        result = []
        for title, summary, link, source in all_news:
            result.append(
                f"**{title}**\n"
                f"_{summary}_\n"
                f"🗞️ {source} • [Baca Selengkapnya...]({link})"
            )

        return "\n\n".join(result)

    except Exception as e:
        print(f"[RSS] Exception utama: {e}")
        return f"Gagal mengambil berita: {e}"

# ────────────────────────────────────────
# HELPER: BUILD EMBED
# ────────────────────────────────────────
async def build_embed(title_prefix="📆 Daily Update"):
    on_this_day, news, fun_fact = await asyncio.gather(
        get_on_this_day(),
        get_news(),
        get_fun_fact()
    )
    embed = discord.Embed(
        title=f"{title_prefix} — {datetime.datetime.now().strftime('%d %B %Y')}",
        description="Berikut informasi harian dari **A2M Information**!",
        color=0x5865F2
    )
    embed.add_field(name="🗓️ On This Day", value=on_this_day, inline=False)
    embed.add_field(name="🗞️ Berita Terbaru Hari Ini", value=news, inline=False)
    embed.add_field(name="💡 Fun Fact Hari Ini", value=fun_fact, inline=False)
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
        print("[Daily Update] Mengirim update harian...")
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
# COMMAND: !trivia
# ────────────────────────────────────────
@bot.command()
async def trivia(ctx):
    random.seed(datetime.datetime.now().timestamp())
    index = random.randint(0, len(FUNFACTS_ID) - 1)
    embed = discord.Embed(
        title="💡 Fun Fact Indonesia!",
        description=FUNFACTS_ID[index],
        color=0xF1C40F
    )
    embed.set_footer(text="DayBot • A2M Information")
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
