"""
Anti-Bot Discord bot (GODS edition)
-----------------------------------
- Members with the role "GODS" (and the server owner) CAN add bots.
- Anyone else who adds a bot -> the bot gets kicked (or banned).
- Bots on the whitelist are always allowed.
"""

import asyncio
import json
import os

import discord # pyright: ignore[reportMissingImports]
from discord.ext import commands # pyright: ignore[reportMissingImports]

# ---------------- CONFIG ----------------
TOKEN = "MTQ3Njk4MTc5MjYwNjI2MTM2OQ.GOXPQm.nR6Toq5kxE5XhBqnegWr_N7cLfzpHT_50TdlpE"   # <-- put your NEW bot token between the quotes
ALLOWED_ROLE_NAME = "GODS"       # role that is allowed to add bots
ACTION = "kick"                  # "kick" or "ban"
LOG_CHANNEL_ID = None            # optional: channel ID for log messages
WHITELIST_FILE = "whitelist.json"
# ----------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def load_whitelist() -> set[int]:
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE) as f:
            return set(json.load(f))
    return set()


def save_whitelist(ids: set[int]) -> None:
    with open(WHITELIST_FILE, "w") as f:
        json.dump(sorted(ids), f)


whitelist = load_whitelist()


async def log(guild: discord.Guild, text: str) -> None:
    print(text)
    if LOG_CHANNEL_ID:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(text)


async def find_adder(guild: discord.Guild, bot_member: discord.Member):
    """Look in the audit log for who added this bot. Returns a Member or None."""
    for _ in range(3):  # audit log can be a moment late, so retry
        try:
            async for entry in guild.audit_logs(
                limit=10, action=discord.AuditLogAction.bot_add
            ):
                if entry.target and entry.target.id == bot_member.id:
                    return guild.get_member(entry.user.id) or entry.user
        except discord.Forbidden:
            return None
        await asyncio.sleep(1.5)
    return None


def is_allowed_adder(guild: discord.Guild, adder) -> bool:
    if adder is None:
        return False
    if adder.id == guild.owner_id:
        return True
    if isinstance(adder, discord.Member):
        return any(r.name == ALLOWED_ROLE_NAME for r in adder.roles)
    return False


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_member_join(member: discord.Member):
    if not member.bot or member.id == bot.user.id or member.id in whitelist:
        return

    guild = member.guild
    adder = await find_adder(guild, member)

    if is_allowed_adder(guild, adder):
        await log(guild, f"✅ Bot **{member}** was added by **{adder}** ({ALLOWED_ROLE_NAME}/owner). Allowed.")
        return

    who = f"{adder} ({adder.id})" if adder else "unknown (couldn't read audit log)"
    reason = f"Bot added by someone without the {ALLOWED_ROLE_NAME} role"
    try:
        if ACTION == "ban":
            await member.ban(reason=reason)
        else:
            await member.kick(reason=reason)
        await log(guild, f"🛡️ {ACTION.capitalize()}ed bot **{member}** (ID {member.id}). Added by: {who}")
    except discord.Forbidden:
        await log(
            guild,
            f"⚠️ Couldn't {ACTION} **{member}**. Move my role ABOVE that bot's role "
            f"and give me Kick/Ban Members + View Audit Log permissions.",
        )


# ---------- Whitelist commands (admins only) ----------
@bot.command(name="allowbot")
@commands.has_permissions(administrator=True)
async def allowbot(ctx: commands.Context, bot_id: int):
    """!allowbot <bot_id> - always allow this bot."""
    whitelist.add(bot_id)
    save_whitelist(whitelist)
    await ctx.send(f"✅ Bot `{bot_id}` whitelisted.")


@bot.command(name="disallowbot")
@commands.has_permissions(administrator=True)
async def disallowbot(ctx: commands.Context, bot_id: int):
    """!disallowbot <bot_id> - remove from whitelist."""
    whitelist.discard(bot_id)
    save_whitelist(whitelist)
    await ctx.send(f"🗑️ Bot `{bot_id}` removed from whitelist.")


@bot.command(name="botlist")
@commands.has_permissions(administrator=True)
async def botlist(ctx: commands.Context):
    """!botlist - show whitelisted bot IDs."""
    ids = ", ".join(f"`{i}`" for i in sorted(whitelist)) or "None"
    await ctx.send(f"Whitelisted bots: {ids}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permission for that.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Please give a valid bot ID (numbers only).")


bot.run(TOKEN)