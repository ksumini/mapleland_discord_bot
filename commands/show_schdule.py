from datetime import datetime

import discord
from discord.ext import commands
from supabase_storage import get_all_raids  # Supabase 연동 함수 import


def setup_show_raids_command(bot: commands.Bot):
    @bot.tree.command(name="일정확인", description="현재 등록된 자쿰 일정들을 확인합니다.")
    async def show_raids(interaction: discord.Interaction):
        raids = get_all_raids()

        if not raids:
            await interaction.response.send_message("📭 등록된 일정이 없습니다.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 자쿰 일정 목록", color=discord.Color.blurple())
        sorted_raids = sorted(raids, key=lambda r: datetime.fromisoformat(r["datetime"]))

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
