from datetime import datetime, date, timedelta
import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from notion_client import Client
from notion_client.errors import APIResponseError
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DISTRIBUTION_DB_ID") or os.getenv("NOTION_SETTLEMENT_DB_ID")

if not NOTION_API_KEY or not NOTION_DB_ID:
    raise RuntimeError("Missing NOTION_API_KEY or NOTION_DB_ID")

notion = Client(auth=NOTION_API_KEY)


def _num(prop):
    if not isinstance(prop, dict):
        return None
    t = prop.get("type")

    # 기본 number
    if t == "number":
        return prop.get("number")

    # formula(number)
    if t == "formula":
        f = prop.get("formula") or {}
        if f.get("type") == "number":
            return f.get("number")

    # rollup(number)
    if t == "rollup":
        r = prop.get("rollup") or {}
        if r.get("type") == "number":
            return r.get("number")


def _d(prop):  # date -> datetime.date
    try:
        s = (prop or {}).get("date", {}).get("start")
        return datetime.fromisoformat(s).date() if s else None
    except Exception:
        return None


def _t(prop):  # title/rich_text -> str
    arr = (prop or {}).get("title") or (prop or {}).get("rich_text") or []
    return "".join(x.get("plain_text", "") for x in arr) if arr else ""


def _extract(page):
    props = page.get("properties", {}) if isinstance(page, dict) else {}
    status = (props.get("정산진행 여부", {}).get("status") or {}).get("name", "")
    total = _num(props.get("총 수익"))
    participants = _num(props.get("참여자 수"))
    per_person = _num(props.get("인당 분배금"))
    if per_person is None and (total is not None) and (participants and participants > 0):
        per_person = int(total / participants)

    return {
        "date": _d(props.get("날짜")),
        "title": _t(props.get("정산 세부 페이지")),
        "status": status,
        "participants": participants,
        "total": total,
        "per_person": per_person,
        "url": page.get("url"),
    }


def _d(prop):  # date -> datetime.date
    try:
        s = (prop or {}).get("date", {}).get("start")
        return datetime.fromisoformat(s).date() if s else None
    except Exception:
        return None


def _t(prop):  # title/rich_text -> str
    arr = (prop or {}).get("title") or (prop or {}).get("rich_text") or []
    return "".join(x.get("plain_text", "") for x in arr) if arr else ""


def _extract(page):
    props = page.get("properties", {}) if isinstance(page, dict) else {}
    status = (props.get("정산진행 여부", {}).get("status") or {}).get("name", "")
    total = _num(props.get("총 수익"))
    participants = _num(props.get("참여자 수"))
    per_person = _num(props.get("인당 분배금"))
    if per_person is None and (total is not None) and (participants and participants > 0):
        per_person = int(total / participants)

    return {
        "date": _d(props.get("날짜")),
        "title": _t(props.get("정산 세부 페이지")),
        "status": status,
        "participants": participants,
        "total": total,
        "per_person": per_person,
        "url": page.get("url"),
    }


# 동기 Notion 호출을 스레드로 오프로딩
def _query_by_date_blocking(target: date):
    start = datetime(target.year, target.month, target.day, tzinfo=KST)
    end = start + timedelta(days=1)
    res = notion.databases.query(
        database_id=NOTION_DB_ID,
        filter={
            "and": [
                {"property": "날짜", "date": {"on_or_after": start.isoformat()}},
                {"property": "날짜", "date": {"before": end.isoformat()}},
            ]
        },
        sorts=[{"property": "날짜", "direction": "descending"}],
        page_size=1,
    )
    return res.get("results", [])


async def _query_by_date(target: date):
    return await asyncio.to_thread(_query_by_date_blocking, target)


def setup_distribution_command(bot: commands.Bot):
    @bot.tree.command(name="분배금정산", description="노션 DB에서 정산 정보를 불러옵니다.")
    @app_commands.describe(날짜="YYYY-MM-DD 형식 (예: 2025-07-27)")
    async def distribution(interaction: discord.Interaction, 날짜: str):
        await interaction.response.defer(ephemeral=True)

        # 날짜 파싱
        try:
            y, m, d = map(int, 날짜.split("-"))
            target_date = date(y, m, d)
        except Exception:
            await interaction.followup.send("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)", ephemeral=True)
            return

        # Notion 호출(타임아웃/예외 처리)
        try:
            pages = await asyncio.wait_for(_query_by_date(target_date), timeout=12)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Notion 응답이 지연됩니다. 잠시 후 다시 시도해주세요.", ephemeral=True)
            return
        except APIResponseError as e:
            await interaction.followup.send(f"⚠️ Notion API 오류({e.status}). 통합 권한/DB ID를 확인해주세요.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"⚠️ 오류가 발생했어요: {e}", ephemeral=True)
            return

        if not pages:
            await interaction.followup.send("해당 날짜의 정산 정보를 찾지 못했어요.", ephemeral=True)
            return

        info = _extract(pages[0])

        embed = discord.Embed(
            title=f"정산 — {info['title'] or str(info['date'])}",
            url=info.get("url"),
            color=discord.Color.green()
        )
        embed.add_field(name="날짜", value=str(info["date"]), inline=True)
        embed.add_field(name="정산 상태", value=info["status"] or "—", inline=True)
        embed.add_field(name="참여자 수", value=str(info["participants"] or 0), inline=True)
        embed.add_field(name="총 수익", value=f"{(info['total'] or 0):,}원", inline=True)
        embed.add_field(name="인당 분배금", value=f"{(info['per_person'] or 0):,}원", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
