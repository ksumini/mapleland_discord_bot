from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from supabase_storage import get_all_raids  # Supabase 연동 함수 import


KST = ZoneInfo("Asia/Seoul")


def _parse_kst(dt_str: str) -> datetime:
    """ISO 문자열을 KST로 파싱 (naive면 KST tz 부여)"""
    dt = datetime.fromisoformat(dt_str)  # "YYYY-MM-DD HH:MM" or ISO8601
    return dt if dt.tzinfo else dt.replace(tzinfo=KST)


def setup_show_raids_command(bot: commands.Bot):
    @bot.tree.command(name="일정확인", description="현재 등록된 자쿰 일정들을 확인합니다.")
    async def show_raids(interaction: discord.Interaction):
        raids = get_all_raids()
        now = datetime.now(KST)

        upcoming = [r for r in raids if _parse_kst(r["datetime"]) >= now]

        if not upcoming:
            await interaction.response.send_message("📭 앞으로 예정된 일정이 없습니다.", ephemeral=True)
            return

        sorted_raids = sorted(upcoming, key=lambda r: _parse_kst(r["datetime"]))

        embed = discord.Embed(title="📋 자쿰 일정 목록", color=discord.Color.blurple())
        embed.description = ""

        for raid in sorted_raids:
            dt_obj = datetime.fromisoformat(raid["datetime"])
            formatted_dt = dt_obj.strftime("%Y-%m-%d (%a) %H:%M")

            embed.description += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 **{formatted_dt}**\n"
                f"- **참여**: {len(raid['participants'])} / {raid['max_participants']}\n"
                f"- **대기자**: {len(raid['waitlist'])}명\n"
                f"- **특이사항**:\n{raid.get('note', '없음') or '없음'}\n"
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
