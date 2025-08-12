import os
import discord
from discord.ext import commands
from supabase_storage import create_raid, get_all_raids
from datetime import datetime
import asyncio

from views.raid_controls import RaidControlView

RAID_ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("RAID_ANNOUNCEMENT_CHANNEL_ID"))


class CreateRaidModal(discord.ui.Modal, title="자쿰 공대 일정 생성"):
    date = discord.ui.TextInput(label="📅 날짜 (예: 2025-08-10)", placeholder="YYYY-MM-DD")
    time = discord.ui.TextInput(label="⏰ 시간 (예: 21:00)", placeholder="HH:MM")
    max_participants = discord.ui.TextInput(label="👥 최대 인원", placeholder="숫자만 입력", max_length=2)
    note = discord.ui.TextInput(label="📝 특이사항 (예: 듀블 우대, 연습 공대 등)", required=False, style=discord.TextStyle.paragraph)

    def __init__(self, interaction: discord.Interaction):
        super().__init__()
        self.interaction = interaction

    async def on_submit(self, interaction: discord.Interaction):
        # 3초 타임아웃 방지
        await interaction.response.defer(ephemeral=True)

        # 관리자 체크
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ 이 명령어는 관리자만 사용할 수 있어요.", ephemeral=True)
            return

        # 날짜와 시간 파싱/검증
        try:
            raid_datetime = datetime.strptime(f"{self.date.value} {self.time.value}", "%Y-%m-%d %H:%M")
            max_participants = int(self.max_participants.value)
        except ValueError:
            await interaction.response.send_message("❌ 날짜, 시간 또는 인원 형식이 잘못되었습니다.", ephemeral=True)
            return

        if raid_datetime < datetime.now():
            await interaction.response.send_message("❌ 과거 시점의 일정은 생성할 수 없습니다.", ephemeral=True)
            return

        if max_participants < 6:
            await interaction.response.send_message("❌ 최소 인원은 6명 이상이어야 합니다.", ephemeral=True)
            return

        key = raid_datetime.strftime("%Y-%m-%d %H:%M")

        # 기존 일정 중복 확인 (블로킹 I/O는 스레드로)
        try:
            raids = await asyncio.to_thread(get_all_raids)
        except Exception as e:
            await interaction.followup.send(f"⚠️ 일정 조회 중 오류: {e}", ephemeral=True)
            return
        if any(r["datetime"] == key for r in raids):
            await interaction.response.send_message(f"⚠️ 이미 `{key}` 일정이 존재합니다.", ephemeral=True)
            return

        # 공대 일정 메시지를 공지 채널로 전송
        channel = interaction.client.get_channel(RAID_ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(RAID_ANNOUNCEMENT_CHANNEL_ID)
            except Exception:
                channel = interaction.channel

        # 안내 메시지 + View 전송
        try:
            pretty_when = datetime.strptime(key, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d (%a) %H:%M")
            embed = discord.Embed(
                title="🔔 New 자쿰 공대 일정 생성!",
                description=(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 **일시:** {pretty_when}\n"
                    f"👥 **최대 인원:** {max_participants}명\n\n"
                    "📝 **특이사항:**\n"
                    f"{(self.note.value or '').strip() or '지금부터 참여 신청 받습니다!'}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ 눌러 참여 신청하세요!"
                ),
                color=discord.Color.orange()
            )
            view = RaidControlView(raid_key=key)
            msg = await channel.send(embed=embed, view=view)
            await msg.add_reaction("✅")
        except Exception as e:
            await interaction.followup.send(f"⚠️ 공지 채널로 메시지 전송 실패: {e}", ephemeral=True)
            return

        # Supabase에 일정 저장
        try:
            raid_id = await asyncio.to_thread(
                create_raid,
                datetime_str=key,
                max_participants=max_participants,
                note=(self.note.value or "").strip()
            )
            # message_id 업데이트
            from supabase_client import supabase
            await asyncio.to_thread(
                lambda: supabase.table("raids").update({"message_id": msg.id}).eq("id", raid_id).execute()
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 일정 저장 중 오류: {e}", ephemeral=True)
            return

        await interaction.followup.send("✅ 공대 일정이 생성되었고, 공지 채널에 안내 메시지를 보냈어요!", ephemeral=True)


def setup_create_raid_command(bot: commands.Bot):
    @bot.tree.command(name="일정생성", description="자쿰 공대 일정을 생성합니다. (관리자 전용)")
    async def create_raid(interaction: discord.Interaction):
        modal = CreateRaidModal(interaction)
        await interaction.response.send_modal(modal)
