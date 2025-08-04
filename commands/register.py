import discord
from discord import app_commands
from supabase_storage import register_user, get_all_users


def setup_register_command(bot):
    @bot.tree.command(name="공대원등록", description="공대원 등록 또는 정보 수정")
    @app_commands.rename(username="아이디", level="렙", job="직업")
    @app_commands.describe(username="메이플 아이디", level="레벨 (숫자)", job="직업")
    @app_commands.choices(
        job=[
            app_commands.Choice(name="다크나이트", value="다크나이트"),
            app_commands.Choice(name="나이트로드", value="나이트로드"),
            app_commands.Choice(name="보우마스터", value="보우마스터"),
            app_commands.Choice(name="비숍", value="비숍"),
            app_commands.Choice(name="신궁", value="신궁"),
            app_commands.Choice(name="섀도어", value="섀도어"),
            app_commands.Choice(name="팔라딘", value="팔라딘"),
            app_commands.Choice(name="히어로", value="히어로"),
        ]
    )
    async def register(
        interaction: discord.Interaction,
        username: str,
        level: int,
        job: app_commands.Choice[str],
    ):
        discord_id = str(interaction.user.id)
        nickname = f"{username}/{level}/{job.value}"

        # 1. 모든 사용자 불러오기
        registered_users = get_all_users()

        # 2. 동일 username을 다른 유저가 쓰고 있는지 확인
        for uid, info in registered_users.items():
            if info["nickname"] == username and uid != discord_id:
                await interaction.response.send_message(
                    f"⚠️ `{username}`는 이미 다른 유저가 등록한 아이디입니다.",
                    ephemeral=True
                )
                return

        # 3. 닉네임 설정
        if interaction.guild.owner_id == interaction.user.id:
            await interaction.response.send_message(
                f"👑 서버 소유자의 닉네임은 봇이 수정할 수 없어요.\n대신 수동으로 `{nickname}`으로 바꿔주세요!",
                ephemeral=True
            )
        else:
            member = interaction.guild.get_member(interaction.user.id)
            if not member:
                await interaction.response.send_message("❌ 멤버 정보를 불러오지 못했어요.", ephemeral=True)
                return

            try:
                await member.edit(nick=nickname)
            except discord.Forbidden:
                await interaction.response.send_message("⚠️ 닉네임을 수정할 권한이 없어요!", ephemeral=True)
                return

        # 4. Supabase에 등록/수정
        register_user(discord_id, username, level, job.value)

        action = "✅ 등록 완료" if discord_id not in registered_users else "🔄 정보 수정 완료"
        await interaction.response.send_message(f"{action}: `{nickname}`", ephemeral=True)
