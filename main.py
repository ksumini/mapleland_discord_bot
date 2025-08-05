import asyncio

import aiohttp
from aiohttp import web
import os
import discord
from discord.ext import commands

from supabase_storage import get_all_raids
from commands.register import setup_register_command
from commands.create_schedule import setup_create_raid_command
from commands.reaction_handler import setup_reaction_handler
from commands.edit_schedule import setup_edit_raid_command
from commands.show_schdule import setup_show_raids_command
from commands.delete_schedule import setup_delete_raid_command
from tasks import reminder

from views.raid_controls import RaidControlView

# 디스코드 API에서 접근 허용 범위(Intents) 설정
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)

# 명령어 파일에서 커맨드 등록
setup_register_command(bot)
setup_create_raid_command(bot)
setup_reaction_handler(bot)
setup_edit_raid_command(bot)
setup_show_raids_command(bot)
setup_delete_raid_command(bot)


# health check endpoint
async def health_check(request):
    return web.Response(text="OK")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("✅ Health check server started at /health")


async def ping_self():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as s:
                resp = await s.get(os.environ['KOYEB_URL'])
                print(f"[ping_self] Self-ping sent. Status: {resp.status}")
        except Exception as e:
            print(f"[ping_self] Error: {e}")
        await asyncio.sleep(180)


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced!")

    reminder.set_bot_instance(bot)
    reminder.check_upcoming_raids.start()
    # bot.loop.create_task(ping_self())

    # 기존 자쿰 일정에 대한 버튼 뷰 등록
    raids = get_all_raids()
    for raid in raids:
        raid_id = raid["id"]
        bot.add_view(RaidControlView(raid_id))
    print("✅ Raid views registered!")


async def main():
    await asyncio.gather(
        start_web_server(),                     # 웹서버 실행
        bot.start(os.getenv("DISCORD_TOKEN"))   # 디스코드 봇 실행
    )


if __name__ == "__main__":
    asyncio.run(main())
