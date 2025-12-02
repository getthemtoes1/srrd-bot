import discord
from discord.ext import commands
from discord import app_commands
from discord import AuditLogAction
import logging
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime
from typing import Optional, Any, Iterable, cast
from flask import Flask
from threading import Thread
```

## Step 3: Restart Your Bot

1. Click **"Stop"** button
2. Click **"Run"** button
3. Wait for it to start
4. You should see: `✅ Web server started on port 8080`

## Step 4: Get Your URL

After it starts, your URL will be:
```
https://srrd-bot.hehepooppee000.repl.co

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s - %(message)s')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

PROMOTE_ROLE_ID = 1444700142434517123
INFRACTION_ROLE_ID = 1436251065963118716
HOST_ROLE_ID_1 = 1436251089195237447
HOST_ROLE_ID_2 = 1436250997423865856

PROMOTIONS_CHANNEL_ID = 1436251260125708310
INFRACTIONS_CHANNEL_ID = 1436251267088519210
REQUIREMENTS_CHANNEL_ID = 1436573068481794068
COMMAND_LOG_CHANNEL_ID = 1444937836095737957
AUDIT_LOG_CHANNEL_ID = 1444940684787454096


def _get_timestamp_label() -> str:
    """Return formatted timestamp for logging."""
    return datetime.utcnow().strftime("%B %d, %Y • %I:%M %p UTC")


async def fetch_text_channel(bot_instance: commands.Bot, channel_id: int) -> Optional[discord.TextChannel]:
    """Fetch a text channel safely."""
    channel = bot_instance.get_channel(channel_id)
    if channel is None:
        try:
            fetched = await bot_instance.fetch_channel(channel_id)
            if isinstance(fetched, discord.TextChannel):
                channel = fetched
        except (discord.NotFound, discord.Forbidden):
            logging.error(f"Channel {channel_id} not accessible.")
            return None
    return channel if isinstance(channel, discord.TextChannel) else None


def interaction_response(interaction: discord.Interaction) -> discord.InteractionResponse:
    """Return a typed interaction response to satisfy linters."""
    return cast(discord.InteractionResponse, interaction.response)


async def log_command_usage(bot_instance: commands.Bot,
                            interaction: discord.Interaction,
                            command_name: str,
                            parameters_text: str = "",
                            status: str = "Success",
                            extra_info: Optional[str] = None) -> None:
    """Send a human-readable log entry for slash command usage."""
    channel = await fetch_text_channel(bot_instance, COMMAND_LOG_CHANNEL_ID)
    if not channel:
        return

    command_line = f"/{command_name}".strip()
    if parameters_text:
        command_line = f"{command_line} {parameters_text}".strip()

    log_lines = [
        "1. Command Execution Log",
        "",
        "User",
        f"{interaction.user.mention} (`{interaction.user.id}`)",
        "",
        "Channel",
        getattr(interaction.channel, 'mention', 'N/A'),
        "",
        "Command",
        "```",
        f"/{command_name}",
        "```",
        "",
        "Message Content",
        "```",
        command_line,
        "```",
        "",
        "Status",
        status,
    ]

    if extra_info:
        log_lines.extend(["", "Details", extra_info])

    log_lines.extend(["", _get_timestamp_label()])

    await channel.send("\n".join(log_lines))


def render_value_for_logs(value: Any) -> str:
    """Return a readable representation for discord option values."""
    if value is None:
        return "None"
    mention = getattr(value, "mention", None)
    if mention:
        return str(mention)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(render_value_for_logs(v) for v in value) or "None"
    return str(value)


async def send_audit_log_entry(title: str,
                               lines: list[str],
                               footer: Optional[str] = None,
                               color: Optional[discord.Color] = None) -> None:
    """Send an audit log embed to the configured channel."""
    channel = await fetch_text_channel(bot, AUDIT_LOG_CHANNEL_ID)
    if not channel:
        return

    description = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple(),
        timestamp=datetime.utcnow()
    )
    footer_text = footer or ""
    timestamp_text = _get_timestamp_label()
    embed.set_footer(text=f"{footer_text} • {timestamp_text}".strip(" •"))
    await channel.send(embed=embed)


def build_audit_summary(entry: discord.AuditLogEntry, title: str) -> str:
    """Create a short summary sentence for an audit-log entry."""
    target_text = format_audit_value(entry.target) if entry.target else ""
    action = entry.action

    if action == AuditLogAction.member_update and target_text:
        return f"{target_text}'s profile was updated."
    if action == AuditLogAction.member_role_update and target_text:
        return f"{target_text}'s roles changed."
    if action == AuditLogAction.member_ban_add and target_text:
        return f"{target_text} was banned."
    if action == AuditLogAction.member_ban_remove and target_text:
        return f"{target_text} was unbanned."
    if action == AuditLogAction.kick and target_text:
        return f"{target_text} was kicked."
    if target_text:
        return f"{target_text} {title.lower()}."
    return ""


def build_change_sections(entry: discord.AuditLogEntry) -> list[str]:
    """Return formatted before/after sections for audit log changes."""
    if not entry.changes:
        return []

    sections: list[str] = []
    for change in entry.changes:
        attribute = getattr(change, "attribute", getattr(change, "key", "Value"))
        before = truncate_text(format_audit_value(getattr(change, "before", None)))
        after = truncate_text(format_audit_value(getattr(change, "after", None)))
        header = attribute.replace("_", " ").title()
        sections.extend([
            "",
            f"**{header}:**",
            f"• Before: {before}",
            f"• After: {after}",
        ])
    return sections


def ensure_column_exists(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Ensure a specific column exists on a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError as err:
            logging.error(f"Failed adding column {column} to {table}: {err}")


def format_option_details(options: Iterable[tuple[str, Any]]) -> str:
    """Format command options for logging."""
    parts = []
    for key, value in options:
        if value is None:
            continue
        parts.append(f"{key}: {render_value_for_logs(value)}")
    return " ".join(parts)


def truncate_text(text: str, limit: int = 1024) -> str:
    """Trim text to fit embed limits."""
    if text is None:
        return "None"
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


async def toggle_attendance_state(view_obj: Any, interaction: discord.Interaction) -> None:
    """Reusable logic for toggling attendee membership."""
    attendees: set[int] = getattr(view_obj, "attendees", set())
    if interaction.user.id in attendees:
        attendees.remove(interaction.user.id)
    else:
        attendees.add(interaction.user.id)
    setattr(view_obj, "attendees", attendees)
    await interaction_response(interaction).defer()
    message_reference = getattr(view_obj, "message_reference", None)
    if message_reference:
        await view_obj.update_embed(message_reference)


def format_audit_value(value: Any) -> str:
    """Convert audit change values into readable strings."""
    mention = getattr(value, "mention", None)
    if mention:
        identifier = getattr(value, "id", None)
        if identifier:
            return f"{mention} (`{identifier}`)"
        return str(mention)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (list, set, tuple)):
        return ", ".join(map(str, value)) or "None"
    if value is None:
        return "None"
    return str(value)


def describe_audit_action(action: AuditLogAction) -> str:
    """Provide a human-readable action label."""
    mapping = {
        AuditLogAction.member_update: "Nickname Updated",
        AuditLogAction.member_role_update: "Role Updated",
        AuditLogAction.member_prune: "Members Pruned",
        AuditLogAction.member_disconnect: "Member Disconnected",
        AuditLogAction.message_delete: "Message Deleted",
        AuditLogAction.message_bulk_delete: "Bulk Messages Deleted",
        AuditLogAction.channel_create: "Channel Created",
        AuditLogAction.channel_delete: "Channel Deleted",
        AuditLogAction.channel_update: "Channel Updated",
        AuditLogAction.role_create: "Role Created",
        AuditLogAction.role_delete: "Role Deleted",
        AuditLogAction.role_update: "Role Updated",
    }
    return mapping.get(action, action.name.replace("_", " ").title())


def audit_action_color(action: AuditLogAction) -> discord.Color:
    """Color coding for audit actions."""
    critical = {
        AuditLogAction.member_ban_add,
        AuditLogAction.member_ban_remove,
        AuditLogAction.integrations_delete,
        AuditLogAction.kick,
    }
    warning = {
        AuditLogAction.member_update,
        AuditLogAction.member_role_update,
        AuditLogAction.message_delete,
        AuditLogAction.message_bulk_delete,
        AuditLogAction.guild_update,
    }
    if action in critical:
        return discord.Color.red()
    if action in warning:
        return discord.Color.orange()
    return discord.Color.blurple()


def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()

    # noinspection SqlNoDataSourceInspection
    c.execute('''CREATE TABLE IF NOT EXISTS promotions
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     user_id
                     INTEGER
                     NOT
                     NULL,
                     promoted_by
                     INTEGER
                     NOT
                     NULL,
                     new_role
                     TEXT,
                     reason
                     TEXT,
                     note
                     TEXT,
                     timestamp
                     DATETIME
                     DEFAULT
                     CURRENT_TIMESTAMP,
                     guild_id
                     INTEGER
                     NOT
                     NULL
                 )''')

    # noinspection SqlNoDataSourceInspection
    c.execute('''CREATE TABLE IF NOT EXISTS infractions
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     user_id
                     INTEGER
                     NOT
                     NULL,
                     issued_by
                     INTEGER
                     NOT
                     NULL,
                     infraction_type
                     TEXT
                     NOT
                     NULL,
                     reason
                     TEXT,
                     severity
                     TEXT
                     DEFAULT
                     'medium',
                     appealable
                     INTEGER
                     DEFAULT
                     0,
                     note
                     TEXT,
                     timestamp
                     DATETIME
                     DEFAULT
                     CURRENT_TIMESTAMP,
                     voided
                     INTEGER
                     DEFAULT
                     0,
                     voided_by
                     INTEGER,
                     voided_reason
                     TEXT,
                     void_timestamp
                     DATETIME,
                     guild_id
                     INTEGER
                     NOT
                     NULL
                 )''')

    ensure_column_exists(c, "promotions", "note", "TEXT")
    ensure_column_exists(c, "infractions", "appealable", "INTEGER DEFAULT 0")
    ensure_column_exists(c, "infractions", "note", "TEXT")
    ensure_column_exists(c, "infractions", "log_channel_id", "INTEGER")
    ensure_column_exists(c, "infractions", "log_message_id", "INTEGER")

    # noinspection SqlNoDataSourceInspection
    c.execute('''CREATE TABLE IF NOT EXISTS tryouts
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     message_id
                     INTEGER,
                     host_id
                     INTEGER
                     NOT
                     NULL,
                     required_attendees
                     INTEGER,
                     guild_id
                     INTEGER
                     NOT
                     NULL,
                     channel_id
                     INTEGER
                     NOT
                     NULL,
                     status
                     TEXT
                     DEFAULT
                     'open',
                     attendees
                     TEXT
                     DEFAULT
                     '[]',
                     created_at
                     DATETIME
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')

    # noinspection SqlNoDataSourceInspection
    c.execute('''CREATE TABLE IF NOT EXISTS trainings
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     message_id
                     INTEGER,
                     host_id
                     INTEGER
                     NOT
                     NULL,
                     required_attendees
                     INTEGER,
                     guild_id
                     INTEGER
                     NOT
                     NULL,
                     channel_id
                     INTEGER
                     NOT
                     NULL,
                     status
                     TEXT
                     DEFAULT
                     'open',
                     attendees
                     TEXT
                     DEFAULT
                     '[]',
                     created_at
                     DATETIME
                     DEFAULT
                     CURRENT_TIMESTAMP
                 )''')

    conn.commit()
    conn.close()


def has_promote_role(interaction: discord.Interaction) -> bool:
    """Check if user has promotion role"""
    return any(role.id == PROMOTE_ROLE_ID for role in interaction.user.roles)


def has_infraction_role(interaction: discord.Interaction) -> bool:
    """Check if user has infraction role"""
    return any(role.id == INFRACTION_ROLE_ID for role in interaction.user.roles)


def has_host_role(interaction: discord.Interaction) -> bool:
    """Check if user has host role"""
    return any(role.id in [HOST_ROLE_ID_1, HOST_ROLE_ID_2] for role in interaction.user.roles)


class PromotionsCog(commands.Cog):
    """Cog for promotion commands"""

    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @app_commands.command(name="promote", description="Promote a user to a new rank")
    @app_commands.describe(user="User to promote", new_role="Role to promote to", reason="Reason for promotion",
                           note="Optional note for internal records")
    async def promote(self, interaction: discord.Interaction, user: discord.Member, new_role: discord.Role,
                      reason: str = "No reason provided", note: Optional[str] = None):
        """Promote a user to a new role"""
        params = format_option_details([
            ("user", user),
            ("new_role", new_role),
            ("reason", reason),
            ("note", note)
        ])
        if not has_promote_role(interaction):
            await interaction_response(interaction).send_message("❌ You don't have permission to promote members.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "promote", params,
                                    status="Denied: Missing promote role")
            return

        try:
            await user.add_roles(new_role)

            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            # noinspection SqlNoDataSourceInspection
            c.execute('''INSERT INTO promotions (user_id, promoted_by, new_role, reason, note, guild_id)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (user.id, interaction.user.id, new_role.name, reason, note, interaction.guild_id))
            conn.commit()
            conn.close()

            embed = discord.Embed(
                title="🎉 Promotion Successful",
                description=f"{user.mention} has been promoted!",
                color=discord.Color.from_rgb(255, 215, 0),
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.add_field(name="👤 Member", value=f"{user.mention}", inline=False)
            embed.add_field(name="⬆️ New Rank", value=f"**{new_role.name}**", inline=False)
            embed.add_field(name="💬 Reason", value=reason, inline=False)
            if note:
                embed.add_field(name="📝 Note", value=note, inline=False)
            embed.add_field(name="👮 Promoted By", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="🔖 Role", value=new_role.mention, inline=True)
            embed.set_footer(text=f"{interaction.guild.name} • {datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
                             icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

            await interaction_response(interaction).send_message(embed=embed, ephemeral=True)

            try:
                promo_channel = await self.bot.fetch_channel(PROMOTIONS_CHANNEL_ID)
                if promo_channel:
                    await promo_channel.send(f"{user.mention} {new_role.mention}", embed=embed)
            except Exception as err:
                logging.error(f"Error sending to promotion channel: {err}")

            try:
                dm_embed = discord.Embed(
                    title="🎉 You've Been Promoted!",
                    description=f"Congratulations on your promotion in **{interaction.guild.name}**!",
                    color=discord.Color.from_rgb(255, 215, 0),
                    timestamp=datetime.now()
                )
                dm_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                dm_embed.add_field(name="🎯 New Rank", value=f"**{new_role.name}**", inline=False)
                dm_embed.add_field(name="💬 Reason", value=reason, inline=False)
                if note:
                    dm_embed.add_field(name="📝 Note", value=note, inline=False)
                dm_embed.add_field(name="📍 Server", value=f"**{interaction.guild.name}**", inline=False)
                dm_embed.set_footer(text="Keep up the great work!",
                                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                logging.warning(f"Could not DM {user.name}")

            extra = f"Member: {user.mention} | New Role: {new_role.mention}"
            await log_command_usage(self.bot, interaction, "promote", params, extra_info=extra)

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"Promotion error: {err}")
            await log_command_usage(self.bot, interaction, "promote", params,
                                    status=f"Failed: {err}")


# noinspection SpellCheckingInspection
class InfractionsCog(commands.Cog):
    """Cog for infraction commands"""

    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    async def _reply_to_infraction_log(self,
                                       channel_id: Optional[int],
                                       message_id: Optional[int],
                                       embed: discord.Embed) -> None:
        """Reply to the stored infraction log message if present."""
        if not channel_id or not message_id:
            return
        channel = await fetch_text_channel(self.bot, channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return
        await message.reply(embed=embed)

    infraction_group = app_commands.Group(name="infraction", description="Manage user infractions")

    @infraction_group.command(name="issue", description="Issue an infraction to a user")
    @app_commands.describe(user="User", infraction_type="Type (Warning, Spam, etc)", reason="Reason",
                           severity="minor/medium/major", appealable="yes/no",
                           note="Optional internal note")
    async def issue_infraction(self, interaction: discord.Interaction, user: discord.Member, infraction_type: str,
                               reason: str, severity: str = "medium", appealable: str = "no",
                               note: Optional[str] = None):
        """Issue an infraction to a user"""
        params = format_option_details([
            ("user", user),
            ("type", infraction_type),
            ("reason", reason),
            ("severity", severity),
            ("appealable", appealable),
            ("note", note)
        ])
        if not has_infraction_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction issue", params,
                                    status="Denied: Missing infraction role")
            return

        if severity.lower() not in ["minor", "medium", "major"]:
            await interaction_response(interaction).send_message("❌ Invalid severity.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction issue", params,
                                    status="Failed: Invalid severity")
            return

        if appealable.lower() not in ["yes", "no"]:
            await interaction_response(interaction).send_message("❌ Invalid appealable value.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction issue", params,
                                    status="Failed: Invalid appealable value")
            return

        appealable_bool = 1 if appealable.lower() == "yes" else 0

        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        try:
            # noinspection SqlNoDataSourceInspection
            c.execute('''INSERT INTO infractions
                         (user_id, issued_by, infraction_type, reason, severity, appealable, note, guild_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (user.id, interaction.user.id, infraction_type, reason, severity.lower(), appealable_bool,
                       note, interaction.guild_id))

            infraction_id = c.lastrowid
            conn.commit()

            color_map = {"minor": discord.Color.from_rgb(255, 255, 0), "medium": discord.Color.from_rgb(255, 165, 0),
                         "major": discord.Color.from_rgb(255, 0, 0)}
            color = color_map.get(severity.lower(), discord.Color.orange())

            embed = discord.Embed(title="⚠️ Infraction Issued", description=f"Infraction issued to {user.mention}",
                                  color=color, timestamp=datetime.now())
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.add_field(name="🆔 ID", value=f"#{infraction_id}", inline=True)
            embed.add_field(name="🔴 Severity", value=f"**{severity.capitalize()}**", inline=True)
            embed.add_field(name="👤 Member", value=f"{user.mention}", inline=False)
            embed.add_field(name="📋 Type", value=f"**{infraction_type}**", inline=False)
            embed.add_field(name="💬 Reason", value=reason, inline=False)
            if note:
                embed.add_field(name="📝 Note", value=note, inline=False)
            embed.add_field(name="🔖 Appealable", value=f"**{'Yes' if appealable_bool else 'No'}**", inline=True)
            embed.add_field(name="👮 By", value=f"{interaction.user.mention}", inline=True)
            embed.set_footer(text=f"{interaction.guild.name} • {datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
                             icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

            await interaction_response(interaction).send_message(embed=embed, ephemeral=True)

            log_message: Optional[discord.Message] = None
            try:
                infraction_channel = await self.bot.fetch_channel(INFRACTIONS_CHANNEL_ID)
                if isinstance(infraction_channel, discord.TextChannel):
                    log_message = await infraction_channel.send(f"{user.mention}", embed=embed)
            except Exception as err:
                logging.error(f"Error sending to infraction channel: {err}")

            if log_message:
                # noinspection SqlNoDataSourceInspection
                c.execute('''UPDATE infractions
                             SET log_channel_id = ?,
                                 log_message_id = ?
                             WHERE id = ?''',
                          (log_message.channel.id, log_message.id, infraction_id))
                conn.commit()

            try:
                dm_embed = discord.Embed(title="⚠️ You've Received an Infraction",
                                         description=f"Infraction in **{interaction.guild.name}**", color=color,
                                         timestamp=datetime.now())
                dm_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                dm_embed.add_field(name="🆔 ID", value=f"#{infraction_id}", inline=True)
                dm_embed.add_field(name="🔴 Severity", value=f"**{severity.capitalize()}**", inline=True)
                dm_embed.add_field(name="📋 Type", value=f"**{infraction_type}**", inline=False)
                dm_embed.add_field(name="💬 Reason", value=reason, inline=False)
                if note:
                    dm_embed.add_field(name="📝 Note", value=note, inline=False)
                dm_embed.add_field(name="🔖 Appealable", value=f"**{'Yes' if appealable_bool else 'No'}**", inline=False)
                dm_embed.set_footer(text="Review server rules.",
                                    icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                logging.warning(f"Could not DM {user.name}")

            extra = f"Infraction #{infraction_id} for {user.mention}"
            await log_command_usage(self.bot, interaction, "infraction issue", params, extra_info=extra)

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"Infraction error: {err}")
            await log_command_usage(self.bot, interaction, "infraction issue", params,
                                    status=f"Failed: {err}")
        finally:
            conn.close()

    @infraction_group.command(name="void", description="Void an infraction")
    @app_commands.describe(infraction_id="Infraction ID", reason="Reason")
    async def void_infraction(self, interaction: discord.Interaction, infraction_id: int,
                              reason: str = "No reason provided"):
        """Void an infraction"""
        params = format_option_details([
            ("infraction_id", infraction_id),
            ("reason", reason)
        ])
        if not has_infraction_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction void", params,
                                    status="Denied: Missing infraction role")
            return

        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            # noinspection SqlNoDataSourceInspection
            c.execute('SELECT * FROM infractions WHERE id = ? AND guild_id = ?', (infraction_id, interaction.guild_id))
            infraction = c.fetchone()

            if not infraction:
                await interaction_response(interaction).send_message("❌ Not found.", ephemeral=True)
                await log_command_usage(self.bot, interaction, "infraction void", params,
                                        status="Failed: Infraction not found")
                return

            if infraction["voided"]:
                await interaction_response(interaction).send_message("❌ Already voided.", ephemeral=True)
                await log_command_usage(self.bot, interaction, "infraction void", params,
                                        status="Failed: Already voided")
                return

            # noinspection SqlNoDataSourceInspection
            c.execute('''UPDATE infractions
                         SET voided         = 1,
                             voided_by      = ?,
                             voided_reason  = ?,
                             void_timestamp = CURRENT_TIMESTAMP
                         WHERE id = ?''',
                      (interaction.user.id, reason, infraction_id))
            conn.commit()

            user = await self.bot.fetch_user(infraction["user_id"])

            embed = discord.Embed(title="✅ Infraction Voided", description=f"#{infraction_id} voided",
                                  color=discord.Color.from_rgb(0, 255, 0), timestamp=datetime.now())
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.add_field(name="🆔 ID", value=f"#{infraction_id}", inline=False)
            embed.add_field(name="👤 Member", value=f"{user.mention}", inline=False)
            embed.add_field(name="💬 Reason", value=reason, inline=False)
            embed.add_field(name="👮 By", value=f"{interaction.user.mention}", inline=True)
            embed.set_footer(text=f"{interaction.guild.name} • {datetime.now().strftime('%m/%d/%Y %I:%M %p')}",
                             icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

            await interaction_response(interaction).send_message(embed=embed, ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction void", params,
                                    extra_info=f"Voided #{infraction_id} for <@{infraction['user_id']}>")

            log_embed = discord.Embed(
                title=f"🚫 Infraction #{infraction_id} Voided",
                description=f"Voided by {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            log_embed.add_field(name="Reason", value=reason, inline=False)
            await self._reply_to_infraction_log(infraction["log_channel_id"], infraction["log_message_id"], log_embed)

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"Void error: {err}")
            await log_command_usage(self.bot, interaction, "infraction void", params,
                                    status=f"Failed: {err}")
        finally:
            conn.close()

    @infraction_group.command(name="edit", description="Edit an infraction")
    @app_commands.describe(infraction_id="ID", new_type="New type", new_reason="Reason", new_severity="Severity",
                           new_appealable="Appealable", new_note="New note")
    async def edit_infraction(self, interaction: discord.Interaction, infraction_id: int,
                              new_type: Optional[str] = None, new_reason: Optional[str] = None,
                              new_severity: Optional[str] = None, new_appealable: Optional[str] = None,
                              new_note: Optional[str] = None):
        """Edit an infraction"""
        params = format_option_details([
            ("infraction_id", infraction_id),
            ("new_type", new_type),
            ("new_reason", new_reason),
            ("new_severity", new_severity),
            ("new_appealable", new_appealable),
            ("new_note", new_note),
        ])
        if not has_infraction_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    status="Denied: Missing infraction role")
            return

        if new_severity and new_severity.lower() not in ["minor", "medium", "major"]:
            await interaction_response(interaction).send_message("❌ Invalid severity.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    status="Failed: Invalid severity")
            return

        if new_appealable and new_appealable.lower() not in ["yes", "no"]:
            await interaction_response(interaction).send_message("❌ Invalid appealable.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    status="Failed: Invalid appealable")
            return
        if not any([new_type, new_reason, new_severity, new_appealable, new_note is not None]):
            await interaction_response(interaction).send_message("⚠️ Provide at least one field to update.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    status="Failed: No fields provided")
            return

        conn = sqlite3.connect('bot_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            # noinspection SqlNoDataSourceInspection
            c.execute('SELECT * FROM infractions WHERE id = ? AND guild_id = ?', (infraction_id, interaction.guild_id))
            infraction = c.fetchone()

            if not infraction:
                await interaction_response(interaction).send_message("❌ Not found.", ephemeral=True)
                await log_command_usage(self.bot, interaction, "infraction edit", params,
                                        status="Failed: Infraction not found")
                return

            changes: list[tuple[str, Any, Any]] = []

            if new_type:
                # noinspection SqlNoDataSourceInspection
                c.execute('UPDATE infractions SET infraction_type = ? WHERE id = ?', (new_type, infraction_id))
                changes.append(("Type", infraction["infraction_type"], new_type))
            if new_reason:
                # noinspection SqlNoDataSourceInspection
                c.execute('UPDATE infractions SET reason = ? WHERE id = ?', (new_reason, infraction_id))
                changes.append(("Reason", infraction["reason"], new_reason))
            if new_severity:
                normalized = new_severity.lower()
                # noinspection SqlNoDataSourceInspection
                c.execute('UPDATE infractions SET severity = ? WHERE id = ?', (normalized, infraction_id))
                changes.append(("Severity", infraction["severity"], new_severity.capitalize()))
            if new_appealable:
                appealable_bool = 1 if new_appealable.lower() == "yes" else 0
                # noinspection SqlNoDataSourceInspection
                c.execute('UPDATE infractions SET appealable = ? WHERE id = ?', (appealable_bool, infraction_id))
                changes.append(("Appealable",
                                "Yes" if infraction["appealable"] else "No",
                                "Yes" if appealable_bool else "No"))
            if new_note is not None:
                # noinspection SqlNoDataSourceInspection
                c.execute('UPDATE infractions SET note = ? WHERE id = ?', (new_note, infraction_id))
                changes.append(("Note", infraction["note"] or "None", new_note or "None"))

            conn.commit()
            user = await self.bot.fetch_user(infraction["user_id"])

            if not changes:
                await interaction_response(interaction).send_message("⚠️ No changes were applied.", ephemeral=True)
                await log_command_usage(self.bot, interaction, "infraction edit", params,
                                        status="Failed: No changes applied")
                return

            embed = discord.Embed(title=f"✏️ Infraction #{infraction_id} Updated",
                                  description=f"Updated by {interaction.user.mention}",
                                  color=discord.Color.from_rgb(100, 149, 237),
                                  timestamp=datetime.utcnow())
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.add_field(name="Member", value=user.mention, inline=False)
            for field_name, old_value, new_value in changes:
                embed.add_field(
                    name=field_name,
                    value=f"**Before:** {old_value or 'None'}\n**After:** {new_value or 'None'}",
                    inline=False
                )

            await interaction_response(interaction).send_message(embed=embed, ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    extra_info=f"Edited #{infraction_id} ({len(changes)} changes)")

            log_embed = discord.Embed(
                title=f"✏️ Infraction #{infraction_id} Updated",
                description=f"Updated by {interaction.user.mention}",
                color=discord.Color.blurple(),
                timestamp=datetime.utcnow()
            )
            for field_name, old_value, new_value in changes:
                log_embed.add_field(
                    name=field_name,
                    value=f"**Before:** {old_value or 'None'}\n**After:** {new_value or 'None'}",
                    inline=False
                )
            await self._reply_to_infraction_log(infraction["log_channel_id"], infraction["log_message_id"], log_embed)

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"Edit error: {err}")
            await log_command_usage(self.bot, interaction, "infraction edit", params,
                                    status=f"Failed: {err}")
        finally:
            conn.close()

    @infraction_group.command(name="list", description="View infractions for a user")
    @app_commands.describe(user="User")
    async def list_infractions(self, interaction: discord.Interaction, user: discord.Member):
        """List all infractions for a user"""
        params = format_option_details([
            ("user", user)
        ])
        if not has_infraction_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction list", params,
                                    status="Denied: Missing infraction role")
            return

        try:
            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            # noinspection SqlNoDataSourceInspection
            c.execute('''SELECT id, infraction_type, reason, severity, timestamp, voided, voided_reason, appealable, note
                         FROM infractions
                         WHERE user_id = ? AND guild_id = ?
                         ORDER BY timestamp DESC''', (user.id, interaction.guild_id))
            infractions = c.fetchall()
            conn.close()

            if not infractions:
                embed = discord.Embed(title=f"📋 {user.name}", description="✅ No infractions",
                                      color=discord.Color.from_rgb(0, 255, 0), timestamp=datetime.now())
                embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                embed.set_footer(text=f"{interaction.guild.name}",
                                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                await interaction_response(interaction).send_message(embed=embed, ephemeral=False)
                await log_command_usage(self.bot, interaction, "infraction list", params,
                                        extra_info=f"No infractions for {user.mention}")
                return

            embed = discord.Embed(title=f"📋 {user.name}", color=discord.Color.from_rgb(100, 149, 237),
                                  timestamp=datetime.now())
            embed.set_thumbnail(url=user.avatar.url if user.avatar else None)

            active_count = 0
            voided_count = 0

            for inf in infractions:
                inf_id, inf_type, reason, severity, timestamp, is_voided, void_reason, appealable, note = inf
                sev_emoji = {"minor": "🟡", "medium": "🟠", "major": "🔴"}.get(severity, "⚪")

                if is_voided:
                    voided_count += 1
                    status = "❌ VOIDED"
                    value = (
                        f"**Type:** {inf_type}\n"
                        f"**Reason:** {reason}\n"
                        f"{sev_emoji} **Severity:** {severity.capitalize()}\n"
                        f"**Appealable:** {'Yes' if appealable else 'No'}\n"
                        f"**Note:** {note or 'None'}\n"
                        f"**Void Reason:** {void_reason}\n"
                        f"**Date:** <t:{int(datetime.fromisoformat(timestamp).timestamp())}:f>"
                    )
                else:
                    active_count += 1
                    status = "⚠️ ACTIVE"
                    value = (
                        f"**Type:** {inf_type}\n"
                        f"**Reason:** {reason}\n"
                        f"{sev_emoji} **Severity:** {severity.capitalize()}\n"
                        f"**Appealable:** {'Yes' if appealable else 'No'}\n"
                        f"**Note:** {note or 'None'}\n"
                        f"**Date:** <t:{int(datetime.fromisoformat(timestamp).timestamp())}:f>"
                    )

                embed.add_field(name=f"{status} #{inf_id}", value=value, inline=False)

            embed.add_field(name="📊 Summary",
                            value=f"**Active:** {active_count} | **Voided:** {voided_count} | **Total:** {len(infractions)}",
                            inline=False)
            embed.set_footer(text=f"{interaction.guild.name}",
                             icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

            await interaction_response(interaction).send_message(embed=embed, ephemeral=False)
            await log_command_usage(self.bot, interaction, "infraction list", params,
                                    extra_info=f"Listed infractions for {user.mention}: {len(infractions)} entries")

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"List error: {err}")
            await log_command_usage(self.bot, interaction, "infraction list", params,
                                    status=f"Failed: {err}")

    @infraction_group.command(name="admin", description="Administrative infraction tools")
    @app_commands.describe(user="User whose infractions to clear",
                           reason="Reason for clearing the infractions")
    async def admin_clear_infractions(self, interaction: discord.Interaction, user: discord.Member,
                                      reason: str = "Administrative clear"):
        """Clear every infraction for a user."""
        params = format_option_details([
            ("user", user),
            ("reason", reason),
        ])
        if not has_infraction_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction admin", params,
                                    status="Denied: Missing infraction role")
            return

        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        try:
            # noinspection SqlNoDataSourceInspection
            c.execute('SELECT COUNT(*) FROM infractions WHERE user_id = ? AND guild_id = ?',
                      (user.id, interaction.guild_id))
            count = c.fetchone()[0]

            if count == 0:
                await interaction_response(interaction).send_message("ℹ️ No infractions found to clear.",
                                                                     ephemeral=True)
                await log_command_usage(self.bot, interaction, "infraction admin", params,
                                        status="Failed: Nothing to clear")
                return

            # noinspection SqlNoDataSourceInspection
            c.execute('DELETE FROM infractions WHERE user_id = ? AND guild_id = ?',
                      (user.id, interaction.guild_id))
            conn.commit()

            embed = discord.Embed(
                title="🧹 Infractions Cleared",
                description=f"All infractions for {user.mention} have been cleared.",
                color=discord.Color.dark_teal(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Cleared By", value=interaction.user.mention, inline=False)
            embed.add_field(name="Total Removed", value=str(count), inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

            await interaction_response(interaction).send_message(embed=embed, ephemeral=True)
            await log_command_usage(self.bot, interaction, "infraction admin", params,
                                    extra_info=f"Cleared {count} infraction(s) for {user.mention}")

        except Exception as err:
            await interaction_response(interaction).send_message(f"❌ Error: {str(err)}", ephemeral=True)
            logging.error(f"Admin clear error: {err}")
            await log_command_usage(self.bot, interaction, "infraction admin", params,
                                    status=f"Failed: {err}")
        finally:
            conn.close()


class TryoutView(discord.ui.View):
    """View for tryout attendance buttons"""

    def __init__(self, bot_instance: commands.Bot, tryout_id: int, host_id: int, guild_id: int,
                 message_reference: Optional[discord.Message] = None):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.tryout_id = tryout_id
        self.host_id = host_id
        self.guild_id = guild_id
        self.attendees = set()
        self.message_reference = message_reference

    @discord.ui.button(label="Attending", style=discord.ButtonStyle.success, emoji="✅")
    async def attend_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Toggle attendance"""
        await toggle_attendance_state(self, interaction)

    @discord.ui.button(label="Host Panel", style=discord.ButtonStyle.primary, emoji="🎯")
    async def host_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open host control panel"""
        if interaction.user.id != self.host_id:
            await interaction_response(interaction).send_message("❌ Only host can use this.", ephemeral=True)
            return

        view = HostPanelView(self.bot, self.tryout_id, self.guild_id, self.message_reference, self.attendees, "tryout")
        embed = discord.Embed(title="🎯 Host Panel", description="Select action", color=discord.Color.blurple())
        embed.add_field(name="Options", value="• Start\n• Conclude\n• Cancel", inline=False)
        await interaction_response(interaction).send_message(embed=embed, view=view, ephemeral=True)

    async def update_embed(self, message: discord.Message) -> None:
        """Update the tryout embed with current attendees"""
        attendee_mentions = "\n".join([f"<@{uid}>" for uid in sorted(self.attendees)])
        if not attendee_mentions:
            attendee_mentions = "No attendees yet"

        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "**Current Attendees:**":
                embed.set_field_at(i, name="**Current Attendees:**", value=attendee_mentions, inline=False)
                break

        await message.edit(embed=embed)


# noinspection DuplicatedCode
class TrainingView(discord.ui.View):
    """View for training attendance buttons"""

    def __init__(self, bot_instance: commands.Bot, training_id: int, host_id: int, guild_id: int,
                 message_reference: Optional[discord.Message] = None):
        super().__init__(timeout=None)
        self.bot = bot_instance
        self.training_id = training_id
        self.host_id = host_id
        self.guild_id = guild_id
        self.attendees = set()
        self.message_reference = message_reference

    @discord.ui.button(label="Attending", style=discord.ButtonStyle.success, emoji="✅")
    async def attend_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Toggle attendance"""
        await toggle_attendance_state(self, interaction)

    @discord.ui.button(label="Host Panel", style=discord.ButtonStyle.primary, emoji="📚")
    async def host_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open host control panel"""
        if interaction.user.id != self.host_id:
            await interaction_response(interaction).send_message("❌ Only host can use this.", ephemeral=True)
            return

        view = HostPanelView(self.bot, self.training_id, self.guild_id, self.message_reference, self.attendees,
                             "training")
        embed = discord.Embed(title="📚 Host Panel", description="Select action", color=discord.Color.blurple())
        embed.add_field(name="Options", value="• Start\n• Conclude\n• Cancel", inline=False)
        await interaction_response(interaction).send_message(embed=embed, view=view, ephemeral=True)

    async def update_embed(self, message: discord.Message) -> None:
        """Update the training embed with current attendees"""
        attendee_mentions = "\n".join([f"<@{uid}>" for uid in sorted(self.attendees)])
        if not attendee_mentions:
            attendee_mentions = "No attendees yet"

        embed = message.embeds[0]
        for i, field in enumerate(embed.fields):
            if field.name == "**Current Attendees:**":
                embed.set_field_at(i, name="**Current Attendees:**", value=attendee_mentions, inline=False)
                break

        await message.edit(embed=embed)


class HostPanelView(discord.ui.View):
    """View for host control panel"""

    def __init__(self, bot_instance: commands.Bot, event_id: int, guild_id: int,
                 message_reference: Optional[discord.Message], attendees: set, event_type: str):
        super().__init__()
        self.bot = bot_instance
        self.event_id = event_id
        self.guild_id = guild_id
        self.message_reference = message_reference
        self.attendees = attendees
        self.event_type = event_type

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success)
    async def start_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Start the event"""
        await interaction_response(interaction).defer(ephemeral=True)

        if self.message_reference and self.event_type == "tryout":
            embed = self.message_reference.embeds[0]
            embed.title = "🎯 Tryout Started"
            for i, field in enumerate(embed.fields):
                if field.name == "**Status:**":
                    embed.set_field_at(i, name="**Status:**", value="Started - Fall in!", inline=False)
                    break
            await self.message_reference.edit(embed=embed)

        elif self.message_reference and self.event_type == "training":
            embed = self.message_reference.embeds[0]
            embed.title = "📚 Training Started"
            for i, field in enumerate(embed.fields):
                if field.name == "**Status:**":
                    embed.set_field_at(i, name="**Status:**", value="Started - Fall in!", inline=False)
                    break
            await self.message_reference.edit(embed=embed)

        await interaction.followup.send(f"✅ {self.event_type.capitalize()} started!", ephemeral=True)

    @discord.ui.button(label="Conclude", style=discord.ButtonStyle.primary)
    async def conclude_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Conclude the event"""
        await interaction_response(interaction).defer(ephemeral=True)

        if self.message_reference:
            embed = discord.Embed(
                title=f"✅ {self.event_type.capitalize()} Concluded",
                description=f"The {self.event_type} has been concluded.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Total Attendees", value=len(self.attendees), inline=False)
            await self.message_reference.reply(embed=embed)

        await interaction.followup.send(f"✅ {self.event_type.capitalize()} concluded!", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Cancel the event"""
        modal = CancelReasonModal(self.bot, self.event_type, self.message_reference)
        await interaction_response(interaction).send_modal(modal)


class CancelReasonModal(discord.ui.Modal):
    """Modal for cancellation reason"""

    def __init__(self, bot_instance: commands.Bot, event_type: str, message_reference: Optional[discord.Message]):
        super().__init__(title=f"Cancel {event_type.capitalize()}")
        self.bot = bot_instance
        self.event_type = event_type
        self.message_reference = message_reference

        self.reason_input = discord.ui.TextInput(
            label="Cancellation Reason",
            placeholder="Why is this event being cancelled?",
            required=True
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle cancellation"""
        await interaction_response(interaction).defer(ephemeral=True)

        reason = self.reason_input.value

        if self.message_reference:
            embed = discord.Embed(
                title=f"❌ {self.event_type.capitalize()} Cancelled",
                description=f"The {self.event_type} has been cancelled.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Cancellation Reason", value=reason, inline=False)
            await self.message_reference.reply(embed=embed)

        await interaction.followup.send(f"✅ {self.event_type.capitalize()} cancelled!", ephemeral=True)


class HostMenuView(discord.ui.View):
    """View for host menu selection"""

    def __init__(self, bot_instance: commands.Bot, host_user: discord.Member, guild: discord.Guild,
                 channel: discord.TextChannel):
        super().__init__()
        self.bot = bot_instance
        self.host_user = host_user
        self.guild = guild
        self.channel = channel

    @discord.ui.button(label="Tryout", style=discord.ButtonStyle.primary, emoji="🎯")
    async def tryout_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open tryout modal"""
        if interaction.user.id != self.host_user.id:
            await interaction_response(interaction).send_message("❌ Only host.", ephemeral=True)
            return

        modal = TryoutModal(self.bot, self.host_user, self.guild, self.channel)
        await interaction_response(interaction).send_modal(modal)

    @discord.ui.button(label="Training", style=discord.ButtonStyle.secondary, emoji="📚")
    async def training_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open training modal"""
        if interaction.user.id != self.host_user.id:
            await interaction_response(interaction).send_message("❌ Only host.", ephemeral=True)
            return

        modal = TrainingModal(self.bot, self.host_user, self.guild, self.channel)
        await interaction_response(interaction).send_modal(modal)


class TryoutModal(discord.ui.Modal):
    """Modal for tryout setup"""

    def __init__(self, bot_instance: commands.Bot, host_user: discord.Member, guild: discord.Guild,
                 channel: discord.TextChannel):
        super().__init__(title="Tryout Setup")
        self.bot = bot_instance
        self.host_user = host_user
        self.guild = guild
        self.channel = channel

        self.required_input = discord.ui.TextInput(label="Required Attendees", placeholder="Number", required=True)
        self.add_item(self.required_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle tryout setup"""
        try:
            required_attendees = int(self.required_input.value)
        except ValueError:
            await interaction_response(interaction).send_message("❌ Must be a number.", ephemeral=True)
            return

        view = TryoutConfirmView(self.bot, self.host_user, self.guild, self.channel, required_attendees)
        embed = discord.Embed(title="🎯 Confirm Tryout", description="Confirm to start", color=discord.Color.green())
        embed.add_field(name="Required", value=str(required_attendees), inline=False)
        embed.add_field(name="Host", value=self.host_user.mention, inline=False)

        await interaction_response(interaction).send_message(embed=embed, view=view, ephemeral=True)


# noinspection DuplicatedCode
class TrainingModal(discord.ui.Modal):
    """Modal for training setup"""

    def __init__(self, bot_instance: commands.Bot, host_user: discord.Member, guild: discord.Guild,
                 channel: discord.TextChannel):
        super().__init__(title="Training Setup")
        self.bot = bot_instance
        self.host_user = host_user
        self.guild = guild
        self.channel = channel

        self.required_input = discord.ui.TextInput(label="Required Attendees", placeholder="Number", required=True)
        self.add_item(self.required_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle training setup"""
        try:
            required_attendees = int(self.required_input.value)
        except ValueError:
            await interaction_response(interaction).send_message("❌ Must be a number.", ephemeral=True)
            return

        view = TrainingConfirmView(self.bot, self.host_user, self.guild, self.channel, required_attendees)
        embed = discord.Embed(title="📚 Confirm Training", description="Confirm to start", color=discord.Color.green())
        embed.add_field(name="Required", value=str(required_attendees), inline=False)
        embed.add_field(name="Host", value=self.host_user.mention, inline=False)

        await interaction_response(interaction).send_message(embed=embed, view=view, ephemeral=True)


class TryoutConfirmView(discord.ui.View):
    """View for tryout confirmation"""

    def __init__(self, bot_instance: commands.Bot, host_user: discord.Member, guild: discord.Guild,
                 channel: discord.TextChannel, required_attendees: int):
        super().__init__()
        self.bot = bot_instance
        self.host_user = host_user
        self.guild = guild
        self.channel = channel
        self.required_attendees = required_attendees

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Confirm tryout creation"""
        if interaction.user.id != self.host_user.id:
            await interaction_response(interaction).send_message("❌ Only host.", ephemeral=True)
            return

        await interaction_response(interaction).defer(ephemeral=True)

        tryout_embed = discord.Embed(
            title="🎯 Tryout Start",
            description="Click below to attend!",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        tryout_embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else None)
        tryout_embed.add_field(name="**Required Attendees:**", value=str(self.required_attendees), inline=False)
        tryout_embed.add_field(name="**Current Attendees:**", value="No attendees yet", inline=False)
        tryout_embed.add_field(name="Announced by", value=self.host_user.mention, inline=False)
        tryout_embed.add_field(name="ℹ️ Information", value="""Before attending you should:
- Complete the Interest form in <#1436573068481794068>
- Read <#1436573068481794068>

During this tryout, you will undergo extensive evaluation to prove that you are capable of withstanding future trainings. Only the best of the best will be selected to undergo further trainings and evaluation.

Those attending should:
- Wear the FBI casual uniform
- Equip all your gear and a M4A1
- Spawn a widebody charger with an undercover livery with any pistol in the trunk
- Report to the NYCSO meeting room

This tryout will take approximately 45 minutes to an hour.
Good Luck!

**Status: Open for Attendees**""", inline=False)
        tryout_embed.set_footer(text=f"{self.guild.name}", icon_url=self.guild.icon.url if self.guild.icon else None)

        view = TryoutView(self.bot, 0, self.host_user.id, self.guild.id)
        tryout_msg = await self.channel.send(embed=tryout_embed, view=view)
        view.message_reference = tryout_msg

        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        # noinspection SqlNoDataSourceInspection
        c.execute('''INSERT INTO tryouts (message_id, host_id, required_attendees, guild_id, channel_id, status)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (tryout_msg.id, self.host_user.id, self.required_attendees, self.guild.id, self.channel.id, 'open'))
        conn.commit()
        conn.close()

        await interaction.followup.send("✅ Tryout posted!", ephemeral=True)


# noinspection DuplicatedCode
class TrainingConfirmView(discord.ui.View):
    """View for training confirmation"""

    def __init__(self, bot_instance: commands.Bot, host_user: discord.Member, guild: discord.Guild,
                 channel: discord.TextChannel, required_attendees: int):
        super().__init__()
        self.bot = bot_instance
        self.host_user = host_user
        self.guild = guild
        self.channel = channel
        self.required_attendees = required_attendees

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Confirm training creation"""
        if interaction.user.id != self.host_user.id:
            await interaction_response(interaction).send_message("❌ Only host.", ephemeral=True)
            return

        await interaction_response(interaction).defer(ephemeral=True)

        training_embed = discord.Embed(
            title="📚 Training",
            description="Click below to attend!",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        training_embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else None)
        training_embed.add_field(name="**Required Attendees:**", value=str(self.required_attendees), inline=False)
        training_embed.add_field(name="**Current Attendees:**", value="No attendees yet", inline=False)
        training_embed.add_field(name="Announced by", value=self.host_user.mention, inline=False)
        training_embed.add_field(name="ℹ️ Information", value="""A training is being hosted. During this training, you can earn certifications!

Those attending should:
- Be in your tactical gear
- Equip all your gear and a M4A1
- Spawn a widebody charger with an undercover livery with any pistol in the trunk
- Report to FOB

**Status: Open for Attendees**""", inline=False)
        training_embed.set_footer(text=f"{self.guild.name}", icon_url=self.guild.icon.url if self.guild.icon else None)

        view = TrainingView(self.bot, 0, self.host_user.id, self.guild.id)
        training_msg = await self.channel.send(embed=training_embed, view=view)
        view.message_reference = training_msg

        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        # noinspection SqlNoDataSourceInspection
        c.execute('''INSERT INTO trainings (message_id, host_id, required_attendees, guild_id, channel_id, status)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (training_msg.id, self.host_user.id, self.required_attendees, self.guild.id, self.channel.id, 'open'))
        conn.commit()
        conn.close()

        await interaction.followup.send("✅ Training posted!", ephemeral=True)


class TryoutCog(commands.Cog):
    """Cog for host menu commands"""

    def __init__(self, bot_instance: commands.Bot):
        self.bot = bot_instance

    @app_commands.command(name="host", description="Host a tryout or training")
    async def host_menu(self, interaction: discord.Interaction) -> None:
        """Open host menu"""
        params = ""
        if not has_host_role(interaction):
            await interaction_response(interaction).send_message("❌ No permission.", ephemeral=True)
            await log_command_usage(self.bot, interaction, "host", params,
                                    status="Denied: Missing host role")
            return

        view = HostMenuView(self.bot, interaction.user, interaction.guild, interaction.channel)
        embed = discord.Embed(title="🎯 Host Menu", description="Select option:", color=discord.Color.blurple(),
                              timestamp=datetime.now())
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.add_field(name="Options", value="• Host a Tryout\n• Host a Training", inline=False)
        embed.set_footer(text=f"{interaction.guild.name}",
                         icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction_response(interaction).send_message(embed=embed, view=view, ephemeral=True)
        await log_command_usage(self.bot, interaction, "host", params,
                                extra_info=f"Opened host menu for {interaction.user.mention}")


@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry) -> None:
    """Relay audit log entries to the central log channel as rich text."""
    actor_line = f"{entry.user.mention} (`{entry.user.id}`)" if entry.user else "System"
    title = describe_audit_action(entry.action)
    summary = build_audit_summary(entry, title)
    lines = [f"**Actor:** {actor_line}"]
    if summary:
        lines.extend(["", summary])

    if entry.target:
        lines.extend(["**Target:**", format_audit_value(entry.target)])

    change_sections = build_change_sections(entry)
    if change_sections:
        lines.extend(change_sections)

    if entry.reason:
        lines.extend(["", "**Reason:**", entry.reason])

    if entry.extra:
        lines.extend(["", "**Additional Info:**", truncate_text(str(entry.extra), 512)])

    footer_parts = []
    target_id = getattr(entry.target, "id", None)
    if target_id:
        footer_parts.append(f"Target ID: {target_id}")
    if entry.user:
        footer_parts.append(f"Actor ID: {entry.user.id}")
    footer_parts.append(f"Entry ID: {entry.id}")
    footer = " | ".join(footer_parts)
    await send_audit_log_entry(title, lines, footer, color=audit_action_color(entry.action))


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    """Log message edits to the audit log channel."""
    if before.author.bot or before.guild is None:
        return
    if before.content == after.content:
        return

    lines = [
        f"**User:** {before.author.mention} (`{before.author.id}`)",
        f"**Channel:** {before.channel.mention}",
        "",
        "**Before:**",
        truncate_text(before.content or "[embed/attachment]"),
        "",
        "**After:**",
        truncate_text(after.content or "[embed/attachment]"),
    ]
    footer = f"Message ID: {before.id} | Channel ID: {before.channel.id}"
    await send_audit_log_entry("Message Edited", lines, footer, color=discord.Color.gold())


@bot.event
async def on_message_delete(message: discord.Message) -> None:
    """Log message deletions to the audit log channel."""
    if message.author.bot or message.guild is None:
        return

    attachments_text = ", ".join(attachment.url for attachment in message.attachments) or "None"
    lines = [
        f"**User:** {message.author.mention} (`{message.author.id}`)",
        f"**Channel:** {message.channel.mention}",
        "",
        "**Content:**",
        truncate_text(message.content or "[embed/attachment]"),
        "",
        "**Attachments:**",
        truncate_text(attachments_text, 512),
    ]
    footer = f"Message ID: {message.id} | Channel ID: {message.channel.id}"
    await send_audit_log_entry("Message Deleted", lines, footer, color=discord.Color.red())


@bot.event
async def on_ready() -> None:
    """Called when bot is ready"""
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} commands")
    except Exception as err:
        logging.error(f"Failed to sync: {err}")
    print(f"✅ Bot online: {bot.user.name}")


def main() -> None:
    """Main function to start the bot"""
    init_db()

    async def load_cogs() -> None:
        """Load all cogs"""
        await bot.add_cog(PromotionsCog(bot))
        await bot.add_cog(InfractionsCog(bot))
        await bot.add_cog(TryoutCog(bot))

    bot.setup_hook = load_cogs
    bot.run(token)


if __name__ == "__main__":
    main()
