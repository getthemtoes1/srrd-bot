#!/usr/bin/env python3
"""
SRRD Bot - A Discord Bot
"""

import discord
from discord.ext import commands
import os

DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"SRRD Bot is online!")
    print(f"Logged in as: {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print(f"Connected to {len(bot.guilds)} server(s)")
    print("=" * 50)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

@bot.command(name='ping')
async def ping(ctx):
    """Check if the bot is responsive"""
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='hello')
async def hello(ctx):
    """Greet the user"""
    await ctx.send(f'Hello {ctx.author.mention}! I am SRRD Bot.')

@bot.command(name='info')
async def info(ctx):
    """Display bot information"""
    embed = discord.Embed(
        title="SRRD Bot Info",
        description="A simple Discord bot",
        color=discord.Color.blue()
    )
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Prefix", value="!", inline=True)
    await ctx.send(embed=embed)

def main():
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is not set!")
        print("Please add your Discord bot token to the Secrets.")
        return
    
    print("Starting SRRD Bot...")
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()
