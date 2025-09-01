import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import asyncio
import datetime
from datetime import datetime
import pytz


# Diccionario global para las colas de música por servidor
queues = {}

load_dotenv()

# Configuración para yt-dlp (para extraer audio)
yt_dlp_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

# Configuración de FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

source = discord.FFmpegPCMAudio('audio.mp3', **ffmpeg_options)

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando simple de prueba
@bot.command()
async def hola(ctx):
    await ctx.send(f'¡Hola, {ctx.author.name}, en que puedo ayudarte hoy?!')

# Comando que responde a '$le sabe'
@bot.command(name='le sabe')
async def le_sabe(ctx):
    await ctx.send('¡Sí le sabe!')

@bot.command()
async def hora(ctx):
    await ctx.send(f'La hora actual es: {datetime.now().strftime("%H:%M")}')


@bot.command()
async def play(ctx, *, search_query):
    #agrega audio desde yt
    if not ctx.message.author.voice:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")
        return
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

    # Conectar al canal de voz si no está conectado
    if not voice_client:
        voice_client = await voice_channel.connect()
    # Mover si está en un canal diferente
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    # Inicializar la cola para el servidor si no existe
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = deque()

    # Buscar y procesar el audio
    try:
        with yt_dlp.YoutubeDL(yt_dlp_options) as ydl:
            info = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            
            if not info['entries']:
                await ctx.send("❌ No se encontraron resultados.")
                return

            video = info['entries'][0]
            title = video['title']
            url = video['url']

        # Crear el reproductor de audio
        player = discord.FFmpegPCMAudio(url, **ffmpeg_options)
        
        # Si ya se está reproduciendo algo, añadir a la cola
        if voice_client.is_playing():
            queues[ctx.guild.id].append({
                'title': title,
                'url': url,
                'player': player
            })
            await ctx.send(f"🎵 Añadido a la cola: **{title}**")
        else:
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f"🎵 Reproduciendo: **{title}**")
            
    except Exception as e:
        await ctx.send(f"❌ Error al reproducir: {str(e)}")

@bot.command()
async def pause(ctx):
    """Pausa la cancion"""
    if ctx.voice_cliente and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Canción pausada.")

@bot.command()
async def skip(ctx):
    """Salta la canción actual."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Acabas de saltar la canción.")
    else:
        await ctx.send("❌ No hay ninguna canción reproduciéndose.")

async def play_next(ctx):
    """Reproduce la siguiente canción en la cola."""
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].popleft()
        ctx.voice_client.play(next_song['player'], after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"🎵 Reproduciendo: **{next_song['title']}**")
    else:
        # Opcional: desconectar después de un tiempo si no hay más canciones
        await asyncio.sleep(300)  # Esperar 5 minutos
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()


# EJECUCIÓN DEL BOT
bot.run(os.getenv('DISCORD_TOKEN'))

# Intents del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)