import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
import threading

# ======================
# MINI WEBSERVER PARA RENDER FREE (mantener activo)
# ======================
app = Flask("")

@app.route("/")
def home():
    return "Bot activo!"

def run():
    app.run(host="0.0.0.0", port=8080)

# Ejecuta Flask en hilo aparte
threading.Thread(target=run).start()

# ======================
# CONFIGURACIÓN BOT DISCORD
# ======================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "scripts.json"
MENU_MESSAGES = {}  # Para guardar el mensaje del menú por servidor

# --- Cargar o crear JSON ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- EMOJIS ---
EMOJIS = [
    discord.PartialEmoji(name="1000114091", id=1441900967241973901),
    discord.PartialEmoji(name="1000114072", id=1441930629553066044),
    discord.PartialEmoji(name="1000114090", id=1441930773195132938),
    discord.PartialEmoji(name="1000114783", id=1441930880342949958),
    discord.PartialEmoji(name="1000114071", id=1441930971195637841),
    discord.PartialEmoji(name="1000114788", id=1443423856437235863),
    discord.PartialEmoji(name="1000114073", id=1443423899726647296),
    discord.PartialEmoji(name="1000114076", id=1443423959159672883)
]

# --- Check admin ---
def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# --- MENU DINÁMICO ---
class DynamicMenuSelect(discord.ui.Select):
    def __init__(self, scripts, descriptions):
        options = []
        for i, (name, desc) in enumerate(descriptions.items()):
            emoji = EMOJIS[i % len(EMOJIS)]
            options.append(discord.SelectOption(label=name, description=desc, emoji=emoji))
        super().__init__(placeholder="Selecciona un script...", options=options)
        self.scripts = scripts

    async def callback(self, interaction: discord.Interaction):
        script_name = self.values[0]
        code = self.scripts.get(script_name, "Script no encontrado")
        await interaction.response.send_message(f"```{code}```", ephemeral=True)
        self.values = []

class DynamicMenu(discord.ui.View):
    def __init__(self, guild_id: str):
        super().__init__(timeout=None)
        scripts = data.get(guild_id, {}).get("scripts", {})
        descriptions = data.get(guild_id, {}).get("descriptions", {})
        if scripts:
            self.add_item(DynamicMenuSelect(scripts, descriptions))

async def actualizar_menu(guild_id: str):
    """Actualiza el menú de scripts en el mensaje original si existe"""
    message_info = MENU_MESSAGES.get(guild_id)
    if not message_info:
        return
    channel_id, message_id = message_info
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    try:
        message = await channel.fetch_message(message_id)
    except:
        return
    embed = discord.Embed(
        title="Scripts Disponibles",
        description="🇪🇸Selecciona el script\n🇺🇸Select the script",
        color=discord.Color.red()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1398867717871767582/1441978459852378175/standard_3.gif")
    embed.set_footer(text="V1.02 | Script Bot")
    view = DynamicMenu(guild_id)
    await message.edit(embed=embed, view=view)

# ======================
# SLASH COMMANDS
# ======================
@tree.command(name="menu", description="Muestra el menú de scripts actualizado")
async def menu(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    embed = discord.Embed(
        title="Scripts Disponibles",
        description="🇪🇸Selecciona el script\n🇺🇸Select the script",
        color=discord.Color.red()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1398867717871767582/1441978459852378175/standard_3.gif")
    embed.set_footer(text="V1.02 | Script Bot")
    view = DynamicMenu(guild_id)
    msg = await interaction.response.send_message(embed=embed, view=view)
    sent_message = await interaction.original_response()
    MENU_MESSAGES[guild_id] = (interaction.channel.id, sent_message.id)

# --- Comandos para agregar, actualizar y eliminar scripts ---
# (Los agregas igual que en tu código anterior...)

# ======================
# EVENTOS BOT
# ======================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if any(word in message.content.lower() for word in ["script", "scripts"]):
        await message.reply(
            "Hola, soy Nova el mejor bot de scripts para administrar scripts en tu servidor de forma facil y rapida "
            "[Click Para Invitarlo a tu servidor](https://discord.com/oauth2/authorize?client_id=1401679000790630430&permissions=0&integration_type=0&scope=bot)"
        )
    await bot.process_commands(message)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot listo! Conectado como {bot.user}")

    for guild in bot.guilds:
        channel = None
        for c in guild.text_channels:
            if c.permissions_for(guild.me).send_messages:
                channel = c
                break
        if channel:
            try:
                await channel.send(
                    "🤖 El Bot Acaba de ser reiniciado, por favor usa /menu de nuevo de lo contrario "
                    "el menu actual solo dará error y no dará los scripts 🤖"
                )
            except:
                pass

# ======================
# RUN BOT
# ======================
bot.run(os.getenv("DISCORD_TOKEN"))
