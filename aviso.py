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

@tree.command(name="addscripts", description="Agrega un script al menú (solo admins)")
@is_admin()
@app_commands.describe(name="Nombre del script", desc="Descripción", code="Código del script (debe iniciar con loadstring)")
async def addscripts(interaction: discord.Interaction, name: str, desc: str, code: str):
    if not code.strip().startswith("loadstring"):
        await interaction.response.send_message(
            "<a:emoji_105:1442298312408567930> Error script no agregado. El código debe iniciar con loadstring.",
            ephemeral=True
        )
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in data:
        data[guild_id] = {"scripts": {}, "descriptions": {}}
    scripts = data[guild_id]["scripts"]
    descriptions = data[guild_id]["descriptions"]
    if name in scripts:
        await interaction.response.send_message("<a:emoji_105:1442298312408567930> Error script no agregado. Ya existe.", ephemeral=True)
        return

    scripts[name] = code
    descriptions[name] = desc
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    await interaction.response.send_message(f"<a:emoji_104:1442298298378617043> Script **{name}** agregado correctamente.", ephemeral=True)
    await actualizar_menu(guild_id)

@tree.command(name="actuscripts", description="Actualiza un script existente (solo admins)")
@is_admin()
@app_commands.describe(name="Nombre del script", code="Nuevo código", desc="Nueva descripción (opcional)")
async def actuscripts(interaction: discord.Interaction, name: str, code: str, desc: str = None):
    guild_id = str(interaction.guild.id)
    if guild_id not in data or name not in data[guild_id]["scripts"]:
        await interaction.response.send_message("<a:emoji_105:1442298312408567930> Ese script no existe.", ephemeral=True)
        return
    data[guild_id]["scripts"][name] = code
    if desc:
        data[guild_id]["descriptions"][name] = desc
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    await interaction.response.send_message(f"<a:emoji_104:1442298298378617043> Script **{name}** actualizado correctamente.", ephemeral=True)
    await actualizar_menu(guild_id)

@tree.command(name="deletescripts", description="Elimina un script del menú (solo admins)")
@is_admin()
@app_commands.describe(name="Nombre del script")
async def deletescripts(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    if guild_id not in data or name not in data[guild_id]["scripts"]:
        await interaction.response.send_message("<a:emoji_105:1442298312408567930> Error script no eliminado. No existe.", ephemeral=True)
        return
    data[guild_id]["scripts"].pop(name)
    data[guild_id]["descriptions"].pop(name)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    await interaction.response.send_message(f"<a:emoji_104:1442298298378617043> Script **{name}** eliminado correctamente.", ephemeral=True)
    await actualizar_menu(guild_id)

@tree.command(name="help", description="Muestra los comandos disponibles y cómo usar el bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="# <:emoji_109:1443424810553311232> Help Menu:",
        description=(
            "<a:emoji_68:1420097757959426188> /menu - Muestra el menú de scripts.\n"
            "<a:emoji_68:1420097757959426188> /addscripts - Agrega un script (solo admins).\n"
            "<a:emoji_68:1420097757959426188> /actuscripts - Actualiza un script existente (solo admins).\n"
            "<a:emoji_68:1420097757959426188> /deletescripts - Elimina un script (solo admins).\n"
            "<a:emoji_68:1420097757959426188> /desofuscar - Desofusca un archivo de script."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="<a:emoji_107:1442318076787032186> Fast Bot")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="desofuscar", description="Desofusca un archivo de script")
@app_commands.describe(archivo="Archivo a desofuscar")
async def desofuscar(interaction: discord.Interaction, archivo: discord.Attachment):
    await interaction.response.send_message("<a:emoji_51:1419806050210807808> Desofuscando...", ephemeral=True)
    try:
        contenido = await archivo.read()
        # Aquí puedes agregar lógica de desofuscación
    except Exception as e:
        await interaction.followup.send(f"<a:emoji_105:1442298312408567930> Error al leer el archivo: {e}", ephemeral=True)
        return
    await interaction.followup.send(
        "<a:emoji_105:1442298312408567930> Créditos insuficientes\nCréditos actuales: ``0 Credits``",
        ephemeral=True
    )

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
