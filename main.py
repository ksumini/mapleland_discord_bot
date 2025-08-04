import discord
from discord.ext import commands
import os

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


@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced!")

    # 🔁 reminder.py의 bot에 현재 봇 인스턴스 연결
    reminder.set_bot_instance(bot)

    # 🔁 알림 루프 시작 (중복 방지)
    reminder.check_upcoming_raids.start()

    # 기존 자쿰 일정에 대한 버튼 뷰 등록
    raids = get_all_raids()
    for raid in raids:
        raid_id = raid["id"]
        bot.add_view(RaidControlView(raid_id))
    print("✅ Raid views registered!")


if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
