import os
import io
import discord
from discord.ext import commands
import google.generativeai as genai
from flask import Flask
from threading import Thread

# Render'ın uyutmaması için mini web sunucusu
app = Flask('')

@app.route('/')
def home():
    return "Sansürsüz AI Ticket Bot aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Gemini API Yapılandırması (Sansürleri esneten güvenlik ayarlarıyla)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Güvenlik filtrelerini en aza indiren (sansürsüz deneyim için) ayar
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

text_model = genai.GenerativeModel('gemini-3.6-flash', safety_settings=safety_settings)

# Bot Ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Buton Sınıfı (Ticket Mantığı)
class AITicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤖 Yapay Zeka Odası Aç", style=discord.ButtonStyle.success, custom_id="ai_ticket_olustur")
    async def ai_ac_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing_channel = discord.utils.get(guild.text_channels, name=f"ai-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"⚠️ Zaten açık olan bir yapay zeka odan var: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        category = discord.utils.get(guild.categories, name="YAPAY ZEKA ODALARI")
        if not category:
            category = await guild.create_category("YAPAY ZEKA ODALARI")

        channel = await guild.create_text_channel(
            name=f"ai-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"{user.name} için özel yapay zeka asistan odası."
        )

        await interaction.response.send_message(f"✅ Sana özel yapay zeka odası oluşturuldu: {channel.mention}", ephemeral=True)
        
        close_view = KapatView()
        await channel.send(
            f"Selam {user.mention}! Burası tamamen sana özel, komutsuz ve serbest yapay zeka odası.\n"
            f"• Bana dilediğin her şeyi sorabilir, normal bir insanla konuşur gibi sohbet edebilirsin.\n"
            f"• Resim çizdirmek istediğinde ekstra komut vermene gerek yok, sadece **'şu resmi çiz'** de yeterli.\n"
            f"• İşin bittiğinde aşağıdaki butona basarak odayı kapatabilirsin.",
            view=close_view
        )

class KapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Odayı Kapat / Sil", style=discord.ButtonStyle.danger, custom_id="ai_oda_kapat")
    async def kapat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Bu oda 5 saniye içinde kapatılıp silinecektir...", ephemeral=True)
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
        await interaction.channel.delete()

@bot.event
async def on_ready():
    print(f"{bot.user.name} Doğal & Sansürsüz AI Sistemi Aktif!")

@bot.event
async def setup_hook():
    bot.add_view(AITicketView())
    bot.add_view(KapatView())

@bot.command(name="aipanel")
async def aipanel(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("Bu komutu sadece sunucu sahibi kullanabilir!", delete_after=5)
        return
    
    embed = discord.Embed(
        title="🤖 Yapay Zeka Asistan Paneli",
        description="Tamamen sana özel, gizli ve sansürsüz bir yapay zeka odası açmak için aşağıdaki **Yapay Zeka Odası Aç** butonuna tıkla!",
        color=discord.Color.blue()
    )
    view = AITicketView()
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name.startswith("ai-"):
        content = message.content.strip()
        
        async with message.channel.typing():
            try:
                # Kullanıcının mesajında çizim/görsel isteği var mı diye akıllıca anlıyoruz
                lower_content = content.lower()
                gorsel_kelimeleri = ["çiz", "resmini yap", "görsel oluştur", "fotoğrafını yap", "tasarla"]
                
                if any(kelime in lower_content for kelime in gorsel_kelimeleri):
                    # Kullanıcı resim istemişse Imagen ile üret
                    image_result = genai.generate_images(
                        model='imagen-3.0-generate-002',
                        prompt=content,
                        number_of_images=1,
                        aspect_ratio="1:1",
                        safety_filter_level="block_none", # Görsel tarafında da sansürü minimuma indiriyoruz
                        person_generation="allow_adult",
                    )
                    
                    for generated_image in image_result.generated_images:
                        image_bytes = generated_image.image.image_bytes
                        file = discord.File(io.BytesIO(image_bytes), filename="ai_serbest_gorsel.png")
                        await message.reply(f"🎨 İstediğin görsel hazır:", file=file)
                else:
                    # Normal metin sohbeti (tamamen sansürsüz/serbest model ile)
                    response = text_model.generate_content(content)
                    await message.reply(response.text)
                    
            except Exception as e:
                await message.reply(f"Bir hata oluştu: {e}")

    await bot.process_commands(message)

# Web sunucusunu başlat ve botu çalıştır
keep_alive()
bot.run(os.getenv("BOT_TOKEN"))
