import asyncio
from datetime import datetime
import random
import sqlite3
import discord
from discord.ext import commands

# Bot Ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='.', intents=intents)

# Veritabanı Bağlantısı
db = sqlite3.connect('ryven_bot.db')
cursor = db.cursor()

# Tabloları Oluşturma
cursor.execute('''
    CREATE TABLE IF NOT EXISTS agaclar (
        guild_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        su_puani INTEGER DEFAULT 0,
        boy REAL DEFAULT 1.0,
        son_sulama TEXT,
        son_sulayan TEXT DEFAULT 'Henüz sulanmadı',
        en_cok_sulayan TEXT DEFAULT 'Henüz kimse sulamadı'
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS uyeler (
        user_id INTEGER PRIMARY KEY,
        oy_sayisi INTEGER DEFAULT 0,
        son_oy_verilen TEXT,
        son_farkli_oy TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS uye_kayit (
        guild_id INTEGER PRIMARY KEY,
        joined INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS oyun_kanallari (
        guild_id INTEGER PRIMARY KEY,
        kelime_kanal_id INTEGER,
        saymaca_kanal_id INTEGER,
        saymaca_sayi INTEGER DEFAULT 0,
        saymaca_son_yazan INTEGER DEFAULT 0,
        son_kelime TEXT DEFAULT ''
    )
''')
db.commit()


# Kurucu Rolü Kontrol Fonksiyonu
def kurucu_mu(ctx):
  rol_kontrol = any(
      'kurucu' in role.name.lower() for role in ctx.author.roles
  )
  return rol_kontrol or ctx.author.guild_permissions.administrator


@bot.event
async def on_ready():
  print(f'RyvenBot ({bot.user.name}) başarıyla aktif ve çalışıyor!')


# ================= KURUCU YARDIM SİSTEMİ =================


@bot.command(name='kurucuyardım')
@commands.check(kurucu_mu)
async def kurucuyardim(ctx):
  embed = discord.Embed(
      title='🛡️ RyvenBot - Kurucu Komutları Menüsü',
      description=(
          'Sunucuyu yönetmek ve oyun sistemlerini kurmak için kullanabileceğiniz'
          ' tüm yetkili komutları aşağıdadır:\n\n'
          '🌳 **Ağaç Sistemi Komutları:**\n'
          '• `.ağaçkanal #kanal` — Global ağaç duyurusunu ve kanalını'
          ' ayarlar.\n\n'
          '🎫 **Destek Sistemi Komutları:**\n'
          '• `.ticketkur` — Destek talebi menüsünü kurar.\n\n'
          '🎮 **Oyun Sistemi Komutları:**\n'
          '• `.unobaşlat` — UNO oyununu başlatır (Min 4 kişi).\n'
          '• `.vampirköylü` — Vampir Köylü oyununu başlatır (Min 5 kişi).\n'
          '• `.kelimebaşlat #kanal` — Kelime oyunu kanalını ayarlar.\n'
          '• `.saymacaşlat #kanal` — Saymaca oyunu kanalını ayarlar.\n'
          '• `.tahminbaşlat` — Sayı tahmin oyununu başlatır.\n'
          '• `.20sorubaşlat` — 20 soru / nesne tahmin oyununu başlatır.\n\n'
          '📊 **Üye İstatistik Komutları:**\n'
          '• `.üyelist` — Toplam oy alan yarışmacı sayısını gösterir.'
      ),
      color=discord.Color.dark_theme(),
  )
  embed.set_footer(text='RyvenBot Güvenlik ve Yönetim Paneli')
  await ctx.send(embed=embed)


# ================= ÜYE YARIŞMA SİSTEMİ =================


@bot.command(name='üyekatıl')
async def uyekatil(ctx):
  cursor.execute(
      'SELECT joined FROM uye_kayit WHERE guild_id = ?', (ctx.guild.id,)
  )
  res = cursor.fetchone()
  if not res:
    cursor.execute(
        'INSERT OR REPLACE INTO uye_kayit (guild_id, joined) VALUES (?, 1)',
        (ctx.guild.id,),
    )
    db.commit()

  embed = discord.Embed(
      title='🌟 10M OWO CASH ÖDÜLLÜ ÜYE YARIŞMASI BAŞLADI!',
      description=(
          '🏆 **Büyük Ödül:** `10M Owo Cash`\n\n'
          'Sunucumuzdaki bu büyük yarışmaya başarıyla katıldın! En çok oyu'
          ' toplayıp zirveye yerleşmek için hemen arkadaşlarına oy verdir!\n\n'
          '📌 **Nasıl Katılınır / Oy Verilir?**\n'
          '• Oy vermek için: `.oyver @Kullanici`\n'
          '• Sıralamayı görmek için: `.üyetop`\n'
          '• Profilini incelemek için: `.üye`'
      ),
      color=discord.Color.gold(),
  )
  embed.set_thumbnail(
      url='https://images.unsplash.com/photo-1563089145-599997674d42'
  )
  await ctx.send(embed=embed)


@bot.command(name='oyver')
async def oyver(ctx, hedef: discord.Member = None):
  if hedef is None:
    await ctx.send(
        '❌ Lütfen oy vermek istediğin üyeyi etiketle! Örnek: `.oyver @Kullanici`'
    )
    return

  if ctx.author.id == hedef.id:
    await ctx.send('❌ Kendine oy veremezsin!')
    return

  simdi = datetime.now()
  cursor.execute(
      'SELECT oy_sayisi, son_oy_verilen, son_farkli_oy FROM uyeler WHERE'
      ' user_id = ?',
      (hedef.id,),
  )
  data = cursor.fetchone()

  oy_sayisi = data[0] if data else 0
  son_oy_verilen_str = data[1] if data else None

  if son_oy_verilen_str:
    son_zaman = datetime.fromisoformat(son_oy_verilen_str)
    if (simdi - son_zaman).total_seconds() < 7200:  # 2 saat
      await ctx.send(
          '❌ Aynı kişiye tekrar oy vermek için 2 saat beklemelisin.'
      )
      return

  yeni_puan = oy_sayisi + 1
  cursor.execute(
      'INSERT OR REPLACE INTO uyeler (user_id, oy_sayisi, son_oy_verilen,'
      ' son_farkli_oy) VALUES (?, ?, ?, ?)',
      (hedef.id, yeni_puan, simdi.isoformat(), simdi.isoformat()),
  )
  db.commit()

  embed = discord.Embed(
      title='✨ OY VERİLDİ!',
      description=(
          f'✨ **{hedef.name}** adlı üyeye başarıyla oy verildi!\nToplam Oy:'
          f' **{yeni_puan}**'
      ),
      color=discord.Color.blurple(),
  )
  await ctx.send(embed=embed)


@bot.command(name='üyetop')
async def uyetop(ctx):
  cursor.execute(
      'SELECT user_id, oy_sayisi FROM uyeler ORDER BY oy_sayisi DESC LIMIT 10'
  )
  rows = cursor.fetchall()
  if not rows:
    await ctx.send('Henüz oy alan üye bulunmuyor.')
    return

  desc = ''
  for i, (uid, puan) in enumerate(rows, 1):
    m = ctx.guild.get_member(uid)
    isim = m.name if m else f'Kullanıcı ID: {uid}'
    desc += f'**{i}.** {isim} — **{puan}** Oy 🌟\n'

  embed = discord.Embed(
      title='🏆 Üye Yarışması Canlı Sıralama (10M Owo Ödüllü)',
      description=desc,
      color=discord.Color.gold(),
  )
  await ctx.send(embed=embed)


@bot.command(name='üye')
async def uye_profil(ctx, hedef: discord.Member = None):
  hedef = hedef or ctx.author
  cursor.execute(
      'SELECT oy_sayisi FROM uyeler WHERE user_id = ?', (hedef.id,)
  )
  res = cursor.fetchone()
  puan = res[0] if res else 0

  embed = discord.Embed(
      title=f'👤 {hedef.name} - Üye Profili',
      description=f'Toplam Oy Sayısı: **{puan}**',
      color=discord.Color.green(),
  )
  await ctx.send(embed=embed)


@bot.command(name='üyelist')
@commands.check(kurucu_mu)
async def uyelist(ctx):
  cursor.execute('SELECT COUNT(*) FROM uyeler')
  res = cursor.fetchone()
  toplam = res[0] if res else 0
  await ctx.send(f'Toplam yarışmacı (oy alan) sayısı: **{toplam}**')


# ================= AĞAÇ SİSTEMİ =================


class AgacView(discord.ui.View):

  def __init__(self, guild_id):
    super().__init__(timeout=None)
    self.guild_id = guild_id

  @discord.ui.button(
      label='Sula', style=discord.ButtonStyle.primary, emoji='💧'
  )
  async def sula_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.defer(ephemeral=True)
    cursor.execute(
        'SELECT su_puani, boy, son_sulama FROM agaclar WHERE guild_id = ?',
        (self.guild_id,),
    )
    res = cursor.fetchone()
    if not res:
      await interaction.followup.send(
          'Önce `.ağaç` ile ağacı oluşturun!', ephemeral=True
      )
      return

    su_puani, boy, son_sulama = res
    simdi = datetime.now()

    if son_sulama:
      gecen = simdi - datetime.fromisoformat(son_sulama)
      if gecen.total_seconds() < 7200:  # 2 saat
        kalan = 7200 - gecen.total_seconds()
        dk, sn = divmod(int(kalan), 60)
        await interaction.followup.send(
            f'❌ Ağacı tekrar sulamak için **{dk} dakika {sn} saniye**'
            ' beklemelisin.',
            ephemeral=True,
        )
        return

    yeni_su = su_puani + 1
    yeni_boy = boy + (0.5 if yeni_su % 18 == 0 else 0.0)
    sulayan_isim = interaction.user.name

    cursor.execute(
        'UPDATE agaclar SET su_puani = ?, boy = ?, son_sulama = ?, son_sulayan'
        ' = ?, en_cok_sulayan = ? WHERE guild_id = ?',
        (
            yeni_su,
            yeni_boy,
            simdi.isoformat(),
            sulayan_isim,
            sulayan_isim,
            self.guild_id,
        ),
    )
    db.commit()

    await interaction.followup.send(
        f'💧 **Can suyu verildi**\n**{sulayan_isim}** ağacı suladı.\nBoy:'
        f' **{yeni_boy:.1f} m** • Toplam: **{yeni_su}** sulama\nSonraki büyümeye'
        f' **{18 - (yeni_su % 18)}** sulama kaldı.',
        ephemeral=True,
    )

  @discord.ui.button(
      label='Sıralama', style=discord.ButtonStyle.secondary, emoji='🏆'
  )
  async def siralama_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    await interaction.response.defer(ephemeral=True)
    cursor.execute(
        'SELECT guild_id, boy, su_puani FROM agaclar ORDER BY boy DESC LIMIT 10'
    )
    rows = cursor.fetchall()
    desc = ''
    for i, (g_id, b, s) in enumerate(rows, 1):
      g = bot.get_guild(g_id)
      g_adi = g.name if g else 'Sunucu'
      desc += f'**{i}.** {g_adi} — Boy: **{b:.1f}m** ({s} Sulama) 🌳\n'
    await interaction.followup.send(
        embed=discord.Embed(
            title='🏆 Global Ağaç Sıralaması (12M Owo Ödüllü)',
            description=desc,
            color=discord.Color.gold(),
        ),
        ephemeral=True,
    )


@bot.command(name='ağaçkanal')
@commands.check(kurucu_mu)
async def agackanal(ctx, kanal: discord.TextChannel):
  cursor.execute(
      'INSERT INTO agaclar (guild_id, channel_id) VALUES (?, ?) ON'
      ' CONFLICT(guild_id) DO UPDATE SET channel_id = ?',
      (ctx.guild.id, kanal.id, kanal.id),
  )
  db.commit()

  embed = discord.Embed(
      title='🌳 12M OWO CASH ÖDÜLLÜ YAŞAM AĞACI SİSTEMİ',
      description=(
          '🌿 **Global Ağaç Yarışması Başladı!**\n\n'
          'Sunucular arası bu büyük yarışmada ağacınızı hep birlikte büyütün, '
          'global sıralamada 1. olup **12M Owo Cash** ödülünün sahibi olun!\n\n'
          '💧 **Nasıl Oynanır?**\n'
          '• Her 2 saatte bir ağacınızı sulayabilirsiniz.\n'
          '• Ağacı sulamak için aşağıdaki **Sula** butonunu kullanın.\n'
          '• Diğer sunucuların durumunu görmek için **Sıralama** butonuna basın.'
      ),
      color=discord.Color.from_rgb(40, 45, 50),
  )
  embed.set_image(
      url='https://images.unsplash.com/photo-1542273917363-3b1817f69a2d'
  )
  await kanal.send(embed=embed, view=AgacView(ctx.guild.id))
  await ctx.send(
      f'✅ Ağaç kanalı başarıyla {kanal.mention} olarak ayarlandı ve duyuru'
      ' mesajı gönderildi.'
  )


@bot.command(name='ağaç')
async def agac(ctx):
  cursor.execute(
      'SELECT channel_id, su_puani, boy, son_sulama, son_sulayan,'
      ' en_cok_sulayan FROM agaclar WHERE guild_id = ?',
      (ctx.guild.id,),
  )
  res = cursor.fetchone()
  if not res:
    await ctx.send('❌ Bu sunucuda ağaç kanalı ayarlanmamış!')
    return

  channel_id, su_puani, boy, son_sulama, son_sulayan, en_cok = res
  if ctx.channel.id != channel_id:
    await ctx.send(f'❌ Bu komut sadece <#{channel_id}> kanalında kullanılabilir!')
    return

  sunucu_adi = ctx.guild.name
  embed = discord.Embed(
      title=f'🌳 {sunucu_adi} Yaşam Ağacı (12M Ödüllü)',
      description=(
          'Sunucular arası yarışmada ağacınızı birlikte büyütün ve 1. olup **12M'
          ' Owo** ödülü kapın!\n\nBoy:'
          f' **{boy:.1f} m** • Sulama: **{su_puani}** • Global Sıralama\nSon'
          f' sulayan: **{son_sulayan}**\n\n**En çok sulayanlar**\n⭐ {en_cok} —'
          f' **{su_puani}**\n\n2 saatte bir sulayabilirsin • Sonraki büyümeye'
          f' **{18 - (su_puani % 18)}** sulama kaldı.'
      ),
      color=discord.Color.from_rgb(40, 45, 50),
  )
  embed.set_image(
      url='https://images.unsplash.com/photo-1542273917363-3b1817f69a2d'
  )
  await ctx.send(embed=embed, view=AgacView(ctx.guild.id))


# ================= TICKET (DESTEK) SİSTEMİ =================


class TicketSelect(discord.ui.Select):

  def __init__(self):
    options = [
        discord.SelectOption(
            label='Partner',
            description='Partnerlik işlemleri için destek talebi açar.',
            emoji='🤝',
        ),
        discord.SelectOption(
            label='Reklam',
            description='Reklam işlemleri için destek talebi açar.',
            emoji='📢',
        ),
        discord.SelectOption(
            label='Bilgi',
            description='Merak ettiğiniz konular hakkında bilgi alır.',
            emoji='💡',
        ),
        discord.SelectOption(
            label='Yetkili Başvuru',
            description='Sunucumuzda yetkili olmak için başvuru yaparsınız.',
            emoji='🛡️',
        ),
    ]
    super().__init__(
        placeholder='Destek talebi açmak için bir kategori seçin...',
        min_values=1,
        max_values=1,
        options=options,
        custom_id='ticket_select',
    )

  async def callback(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    secim = self.values[0]
    guild = interaction.guild

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
    }

    kanal = await guild.create_text_channel(
        name=f'{secim.lower().replace(" ", "-")}-{interaction.user.name}',
        overwrites=overwrites,
    )

    class TicketKapatView(discord.ui.View):

      def __init__(self):
        super().__init__(timeout=None)

      @discord.ui.button(
          label='Talebi Kapat',
          style=discord.ButtonStyle.danger,
          emoji='🔒',
          custom_id='ticket_kapat',
      )
      async def kapat_btn(
          self, inter: discord.Interaction, button: discord.ui.Button
      ):
        await inter.response.send_message(
            '🔒 Talep 5 saniye içinde kapatılıyor...'
        )
        await asyncio.sleep(5)
        await inter.channel.delete()

    embed = discord.Embed(
        title=f'🎫 {secim} Destek Talebi',
        description=(
            f'Merhaba {interaction.user.mention}!\nDestek ekibimiz en kısa sürede'
            ' sizinle ilgilenecektir.\nTalebi kapatmak için aşağıdaki butonu'
            ' kullanabilirsiniz.'
        ),
        color=discord.Color.green(),
    )
    await kanal.send(
        content=interaction.user.mention,
        embed=embed,
        view=TicketKapatView(),
    )
    await interaction.followup.send(
        f'✅ Destek kanalınız başarıyla oluşturuldu: {kanal.mention}',
        ephemeral=True,
    )


class TicketView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(TicketSelect())


@bot.command(name='ticketkur')
@commands.check(kurucu_mu)
async def ticketkur(ctx):
  embed = discord.Embed(
      title='🎫 RyvenBot Destek Sistemi',
      description=(
          'Aşağıdaki menüden ihtiyacınıza uygun kategori seçerek destek talebi'
          ' oluşturabilirsiniz.'
      ),
      color=discord.Color.blue(),
  )
  await ctx.send(embed=embed, view=TicketView())


# ================= UNO OYUNU SİSTEMİ =================

RENKLER = ['Kırmızı', 'Mavi', 'Sarı', 'Yeşil']
RENGIN_EMOJISI = {
    'Kırmızı': '🟥',
    'Mavi': '🟦',
    'Sarı': '🟨',
    'Yeşil': '🟩',
}


class UnoKatilimView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=60)
    self.katilanlar = []

  @discord.ui.button(
      label='UNO Oyununa Katıl (0/5)',
      style=discord.ButtonStyle.success,
      emoji='🎴',
  )
  async def katil_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if interaction.user in self.katilanlar:
      await interaction.response.send_message(
          'Zaten katıldın!', ephemeral=True
      )
      return

    self.katilanlar.append(interaction.user)
    button.label = f'UNO Oyununa Katıl ({len(self.katilanlar)}/5)'

    if len(self.katilanlar) == 5:
      for child in self.children:
        child.disabled = True
      await interaction.message.edit(view=self)
      self.stop()
      await oyunu_baslat(interaction.channel, self.katilanlar)
      return

    await interaction.message.edit(view=self)
    await interaction.response.send_message(
        'Oyuna başarıyla katıldın!', ephemeral=True
    )

  @discord.ui.button(
      label='Oyunu Başlat (Min 4)',
      style=discord.ButtonStyle.primary,
      emoji='▶️',
  )
  async def baslat_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if len(self.katilanlar) < 4:
      await interaction.response.send_message(
          '❌ Oyunu başlatmak için en az 4 kişi olmalı!', ephemeral=True
      )
      return

    for child in self.children:
      child.disabled = True
    await interaction.message.edit(view=self)
    self.stop()
    await oyunu_baslat(interaction.channel, self.katilanlar)


async def oyunu_baslat(channel, oyuncular):
  destaOlustur = lambda: [
      (random.choice(RENKLER), random.randint(0, 9)) for _ in range(40)
  ]
  deste = destaOlustur()
  kartlar = {
      o.id: [deste.pop(), deste.pop(), deste.pop(), deste.pop(), deste.pop()]
      for o in oyuncular
  }
  ustteki_kart = deste.pop()

  class UnoOyunView(discord.ui.View):

    def __init__(self):
      super().__init__(timeout=None)
      self.siradaki = 0

    def embed_olustur(self):
      sira_kisi = oyuncular[self.siradaki]
      renk_emo = RENGIN_EMOJISI.get(ustteki_kart[0], '⬜')
      desc = (
          f'🔔 **SIRA Sende:** {sira_kisi.mention}\n\n'
          f'🎯 **Masadaki Kart:** {renk_emo} **{ustteki_kart[1]} {ustteki_kart[0]}**\n\n'
          '📊 **Oyuncu Kart Sayıları:**\n'
      )
      for o in oyuncular:
        k_sayi = len(kartlar[o.id])
        uno_str = ' ⚠️ **UNO!**' if k_sayi == 1 else ''
        desc += f'• {o.name} → **{k_sayi} Kart**{uno_str}\n'

      return discord.Embed(
          title='🎴 UNO MASASI',
          description=desc,
          color=discord.Color.green(),
      )

    @discord.ui.button(
        label='Kartlarımı Gör / Hamle Yap',
        style=discord.ButtonStyle.primary,
        emoji='👁️',
    )
    async def hamle_yap(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
      aktif_oyuncu = oyuncular[self.siradaki]
      if interaction.user.id != aktif_oyuncu.id:
        await interaction.response.send_message(
            '❌ Sıra sende değil!', ephemeral=True
        )
        return

      k_listesi = kartlar[interaction.user.id]

      secenekler = []
      for i, k in enumerate(k_listesi):
        secenekler.append(
            discord.SelectOption(
                label=f'{i+1}. Kart: {k[1]} {k[0]}',
                value=str(i),
                emoji=RENGIN_EMOJISI.get(k[0], '⬜'),
            )
        )

      class KartSecimSelect(discord.ui.Select):

        def __init__(self, parent_view, k_list, o_listesi, oyuncu_obj):
          nonlocal ustteki_kart
          self.p_view = parent_view
          self.k_list = k_list
          self.o_listesi = o_listesi
          self.oyuncu_obj = oyuncu_obj
          super().__init__(
              placeholder='Yere atmak istediğin kartı seç...',
              options=secenekler,
          )

        async def callback(self, inter: discord.Interaction):
          nonlocal ustteki_kart
          idx = int(self.values[0])
          if idx >= len(self.k_list):
            await inter.response.send_message(
                '❌ Geçersiz kart seçimi!', ephemeral=True
            )
            return

          atilan = self.k_list[idx]

          if atilan[0] == ustteki_kart[0] or atilan[1] == ustteki_kart[1]:
            self.k_list.pop(idx)
            ustteki_kart = atilan

            if len(self.k_list) == 0:
              await inter.response.send_message(
                  f'🏆 **OYUN BİTTİ! KAZANAN:** {inter.user.mention} 👑',
                  ephemeral=False,
              )
              return

            self.p_view.siradaki = (self.p_view.siradaki + 1) % len(
                self.o_listesi
            )
            try:
              await interaction.message.edit(
                  embed=self.p_view.embed_olustur(), view=self.p_view
              )
            except Exception:
              pass

            await inter.response.send_message(
                f'✅ Atılan Kart: {RENGIN_EMOJISI.get(atilan[0], "⬜")} **{atilan[1]} {atilan[0]}**',
                ephemeral=True,
            )
          else:
            await inter.response.send_message(
                '❌ Bu kart masadaki karta uymuyor! Kart çekmelisin.',
                ephemeral=True,
            )

      class KartSecimView(discord.ui.View):

        def __init__(self):
          super().__init__(timeout=30)
          self.add_item(
              KartSecimSelect(view, k_listesi, oyuncular, interaction.user)
          )

        @discord.ui.button(
            label='Kart Çek (+1)',
            style=discord.ButtonStyle.secondary,
            emoji='📥',
        )
        async def kart_cek(
            self, inter_btn: discord.Interaction, btn: discord.ui.Button
        ):
          nonlocal deste
          if len(deste) == 0:
            deste = destaOlustur()
          cekilen = deste.pop()
          k_listesi.append(cekilen)
          emo = RENGIN_EMOJISI.get(cekilen[0], '⬜')
          await inter_btn.response.send_message(
              f'📥 Desteden Kart Çektin: {emo} **{cekilen[1]} {cekilen[0]}**',
              ephemeral=True,
          )

      await interaction.response.send_message(
          '🎴 **Elindeki Kartlar:** Uygun kartını seçebilir veya kart'
          ' çekebilirsin.',
          view=KartSecimView(),
          ephemeral=True,
      )

  view = UnoOyunView()
  await channel.send(
      '🟢 **UNO Oyunu Başladı!** Masa kuruldu.',
      embed=view.embed_olustur(),
      view=view,
  )


@bot.command(name='unobaşlat')
@commands.check(kurucu_mu)
async def unobaslat(ctx):
  view = UnoKatilimView()
  await ctx.send(
      '🎴 **UNO Oyunu Katılım Başladı!**\nEn az 4, en fazla 5 kişi olabilir.'
      ' Katılmak için aşağıdaki butona basın.',
      view=view,
  )


# ================= VAMPİR KÖYLÜ SİSTEMİ =================


class VampirKatilimView(discord.ui.View):

  def __init__(self):
    super().__init__(timeout=60)
    self.katilanlar = []

  @discord.ui.button(
      label='Vampir Köylüye Katıl (0/15)',
      style=discord.ButtonStyle.danger,
      emoji='🧛‍♂️',
  )
  async def katil_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if interaction.user in self.katilanlar:
      await interaction.response.send_message(
          'Zaten katıldın!', ephemeral=True
      )
      return

    self.katilanlar.append(interaction.user)
    button.label = f'Vampir Köylüye Katıl ({len(self.katilanlar)}/15)'

    if len(self.katilanlar) == 15:
      for child in self.children:
        child.disabled = True
      await interaction.message.edit(view=self)
      self.stop()
      await vampir_oyunu_baslat(interaction.channel, self.katilanlar)
      return

    await interaction.message.edit(view=self)
    await interaction.response.send_message(
        'Oyuna başarıyla katıldın!', ephemeral=True
    )

  @discord.ui.button(
      label='Oyunu Başlat (Min 5)', style=discord.ButtonStyle.primary, emoji='▶️'
  )
  async def baslat_btn(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    if len(self.katilanlar) < 5:
      await interaction.response.send_message(
          '❌ Oyunu başlatmak için en az 5 kişi olmalı!', ephemeral=True
      )
      return

    for child in self.children:
      child.disabled = True
    await interaction.message.edit(view=self)
    self.stop()
    await vampir_oyunu_baslat(interaction.channel, self.katilanlar)


async def vampir_oyunu_baslat(channel, oyuncular):
  roller = ['Vampir', 'Doktor', 'Dedektif', 'Köylü', 'Köylü']
  while len(roller) < len(oyuncular):
    roller.append('Köylü')

  random.shuffle(roller)
  oyuncu_rolleri = {oyuncular[i]: roller[i] for i in range(len(oyuncular))}

  await channel.send(
      '🧛‍♂️ **Vampir Köylü Oyunu Başladı!**\nRoller oyunculara özel mesaj (DM)'
      ' olarak gönderildi. Gece vakti başladı!'
  )

  for oyuncu, rol in oyuncu_rolleri.items():
    try:
      if rol == 'Vampir':
        vampir_view = discord.ui.View()
        for hedef in oyuncular:
          if hedef.id != oyuncu.id:
            btn = discord.ui.Button(
                label=hedef.name,
                style=discord.ButtonStyle.danger,
                emoji='🗡️',
            )

            async def hedef_sec_cb(inter, h=hedef):
              await inter.response.send_message(
                  f'🩸 **KURBAN SEÇİLDİ!**\nBu gece hedefin **{h.name}** olarak'
                  ' belirlendi. 🦇',
                  ephemeral=True,
              )

            btn.callback = hedef_sec_cb
            vampir_view.add_item(btn)

        await oyuncu.send(
            '🌙 **Vampir Köylü Oyunu Başladı!**\nGizli Rolün: 🧛‍♂️ **Vampir**'
            ' 🧛‍♂️\n\nGece oldu! Avlamak istediğin kişiyi seç:',
            view=vampir_view,
        )

      elif rol == 'Doktor':
        doktor_view = discord.ui.View()
        for hedef in oyuncular:
          btn = discord.ui.Button(
              label=hedef.name, style=discord.ButtonStyle.success, emoji='💉'
          )

          async def koru_sec_cb(inter, h=hedef):
            await inter.response.send_message(
                f'💉 **KORUMA SAĞLANDI!**\nBu gece koruduğun kişi: **{h.name}**'
                ' 🩺',
                ephemeral=True,
            )

          btn.callback = koru_sec_cb
          doktor_view.add_item(btn)

        await oyuncu.send(
            '🌙 **Vampir Köylü Oyunu Başladı!**\nGizli Rolün: 💉 **Doktor**'
            ' 💉\n\nGece oldu! Korumak istediğin kişiyi seç:',
            view=doktor_view,
        )
      else:
        await oyuncu.send(
            f'🌙 **Vampir Köylü Oyunu Başladı!**\nGizli Rolün: **{rol}**\nGece'
            ' vakti, sabahı bekle...'
        )
    except Exception:
      pass


@bot.command(name='vampirköylü')
@commands.check(kurucu_mu)
async def vampirkoylu(ctx):
  view = VampirKatilimView()
  await ctx.send(
      '🧛‍♂️ **Vampir Köylü Katılım Başladı!**\nEn az 5, en fazla 15 kişi'
      ' olmalıdır. Katılmak için aşağıdaki butona basın.',
      view=view,
  )


# ================= DİĞER OYUN SİSTEMLERİ =================

# 1. Kelime Oyunu Sistemi
@bot.command(name='kelimebaşlat')
@commands.check(kurucu_mu)
async def kelime_baslat(ctx, kanal: discord.TextChannel):
  cursor.execute(
      'INSERT INTO oyun_kanallari (guild_id, kelime_kanal_id, son_kelime)'
      ' VALUES (?, ?, ? ) ON CONFLICT(guild_id) DO UPDATE SET'
      ' kelime_kanal_id = ?',
      (ctx.guild.id, kanal.id, '', kanal.id),
  )
  db.commit()
  await ctx.send(
      f'✅ Kelime oyunu kanalı başarıyla {kanal.mention} olarak ayarlandı.'
  )


# 2. Saymaca Sistemi
@bot.command(name='saymacaşlat')
@commands.check(kurucu_mu)
async def saymaca_baslat(ctx, kanal: discord.TextChannel):
  cursor.execute(
      'INSERT INTO oyun_kanallari (guild_id, saymaca_kanal_id, saymaca_sayi,'
      ' saymaca_son_yazan) VALUES (?, ?, 0, 0) ON CONFLICT(guild_id) DO UPDATE'
      ' SET saymaca_kanal_id = ?, saymaca_sayi = 0, saymaca_son_yazan = 0',
      (ctx.guild.id, kanal.id, kanal.id),
  )
  db.commit()
  await ctx.send(
      f'✅ Saymaca oyunu kanalı başarıyla {kanal.mention} olarak ayarlandı.'
  )


# 3. Adam Asmaca Oyunu
KELİMELER = [
    'discord',
    'python',
    'bilgisayar',
    'yazilim',
    'oyun',
    'sunucu',
    'klavye',
    'maceraci',
]


class AdamAsmacaView(discord.ui.View):

  def __init__(self, kelime):
    super().__init__(timeout=120)
    self.kelime = kelime
    self.dogru_tahminler = set()
    self.yanlis_hak = 6

  def get_display(self):
    return ' '.join(
        [c if c in self.dogru_tahminler else '_' for c in self.kelime]
    )

  @discord.ui.button(
      label='Harf Tahmin Et', style=discord.ButtonStyle.primary, emoji='🔤'
  )
  async def harf_sec(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):

    class HarfModal(discord.ui.Modal, title='Adam Asmaca - Harf Gir'):
      harf = discord.ui.TextInput(label='Bir harf girin', max_length=1)

      async def on_submit(self, inter: discord.Interaction):
        h = self.harf.value.lower()
        if len(h) != 1 or not h.isalpha():
          await inter.response.send_message(
              '❌ Lütfen geçerli bir tek harf girin!', ephemeral=True
          )
          return

        view = self.view_ref
        if h in view.kelime:
          view.dogru_tahminler.add(h)
          if all(c in view.dogru_tahminler for c in view.kelime):
            for child in view.children:
              child.disabled = True
            await inter.message.edit(
                content=(
                    '🎉 **Tebrikler! Kelimeyi bildiniz:**'
                    f' `{view.kelime}`'
                ),
                view=view,
            )
            await inter.response.send_message(
                '🏆 Oyunu kazandınız!', ephemeral=True
            )
            return

          await inter.response.send_message(
              f'✅ Doğru harf: **{h}**', ephemeral=True
          )
        else:
          view.yanlis_hak -= 1
          if view.yanlis_hak <= 0:
            for child in view.children:
              child.disabled = True
            await inter.message.edit(
                content=f'💀 **Kaybettiniz! Kelime şuydu:** `{view.kelime}`',
                view=view,
            )
            await inter.response.send_message(
                '❌ Haklarınız bitti.', ephemeral=True
            )
            return
          await inter.response.send_message(
              f'❌ Yanlış harf! Kalan hak: {view.yanlis_hak}', ephemeral=True
          )

        embed = discord.Embed(
            title='🎯 Adam Asmaca Oyunu',
            description=(
                f'Kelime: `{view.get_display()}`\nKalan Yanlış Hakkı:'
                f' **{view.yanlis_hak}/6**'
            ),
            color=discord.Color.orange(),
        )
        await inter.message.edit(embed=embed, view=view)

    modal = HarfModal()
    modal.view_ref = self
    await interaction.response.send_modal(modal)


@bot.command(name='adamasmaca')
async def adamasmaca(ctx):
  secilen_kelime = random.choice(KELİMELER)
  view = AdamAsmacaView(secilen_kelime)
  embed = discord.Embed(
      title='🎯 Adam Asmaca Oyunu Başladı!',
      description=f'Kelime: `{view.get_display()}`\nKalan Yanlış Hakkı: **6/6**',
      color=discord.Color.orange(),
  )
  await ctx.send(embed=embed, view=view)


# 4. Yüksek / Alçak (Sayı Tahmin) Oyunu
@bot.command(name='tahminbaşlat')
@commands.check(kurucu_mu)
async def tahmin_baslat(ctx):
  hedef_sayi = random.randint(1, 100)
  await ctx.send(
      '🎯 **1 ile 100 Arası Sayı Tahmin Oyunu Başladı!**\nSohbete 1-100 arasında'
      ' bir sayı yazarak tahmin edin.'
  )

  def check(m):
    return (
        m.channel == ctx.channel and not m.author.bot and m.content.isdigit()
    )

  for _ in range(15):
    try:
      msg = await bot.wait_for('message', timeout=30.0, check=check)
      tahmin = int(msg.content)
      if tahmin == hedef_sayi:
        await ctx.send(
            f'🎉 Tebrikler {msg.author.mention}, doğru tahmin! Sayı'
            f' **{hedef_sayi}** idi.'
        )
        return
      elif tahmin < hedef_sayi:
        await ctx.send(
            f'📈 Daha **yüksek** bir sayı söyle! ({msg.author.name})'
        )
      else:
        await ctx.send(f'📉 Daha **alçak** bir sayı söyle! ({msg.author.name})')
    except asyncio.TimeoutError:
      await ctx.send(
          f'⏰ Süre bitti! Kimse bilemedi. Doğru sayı **{hedef_sayi}** idi.'
      )
      return


# 5. 20 Soru / Nesne Tahmin Oyunu
@bot.command(name='20sorubaşlat')
@commands.check(kurucu_mu)
async def yirmi_soru_baslat(ctx):
  nesneler = [
      'Elma',
      'Bilgisayar',
      'Gözlük',
      'Araba',
      'Kalem',
      'Telefon',
      'Kitap',
      'Gitar',
  ]
  secilen = random.choice(nesneler)
  await ctx.send(
      '🧠 **20 Soru / Nesne Tahmin Oyunu Başladı!**\nAklımdan bir nesne tuttum.'
      ' Sadece **"Evet"** veya **"Hayır"** cevabı alabileceğiniz sorular'
      ' sorun veya direkt tahmin edin!'
  )


# Mesaj Dinleyicisi
@bot.event
async def on_message(message):
  if message.author.bot:
    return

  await bot.process_commands(message)

  cursor.execute(
      'SELECT kelime_kanal_id, saymaca_kanal_id, saymaca_sayi, saymaca_son_yazan,'
      ' son_kelime FROM oyun_kanallari WHERE guild_id = ?',
      (message.guild.id,),
  )
  res = cursor.fetchone()

  if res:
    kelime_kanal, saymaca_kanal, saymaca_sayisi, saymaca_son, son_kel = res

    # Kelime Oyunu Mantığı
    if kelime_kanal and message.channel.id == kelime_kanal:
      kelime = message.content.strip().lower()
      if ' ' in kelime or not kelime.isalpha():
        return
      if son_kel and kelime[0] != son_kel[-1]:
        await message.add_reaction('❌')
        return

      cursor.execute(
          'UPDATE oyun_kanallari SET son_kelime = ? WHERE guild_id = ?',
          (kelime, message.guild.id),
      )
      db.commit()
      await message.add_reaction('✅')

    # Saymaca Oyunu Mantığı
    elif saymaca_kanal and message.channel.id == saymaca_kanal:
      if message.content.isdigit():
        sayi = int(message.content)
        if message.author.id == saymaca_son:
          await message.delete()
          return
        if sayi == saymaca_sayisi + 1:
          cursor.execute(
              'UPDATE oyun_kanallari SET saymaca_sayi = ?, saymaca_son_yazan ='
              ' ? WHERE guild_id = ?',
              (sayi, message.author.id, message.guild.id),
          )
          db.commit()
          await message.add_reaction('👍')
        else:
          await message.delete()


bot.run('TOKENINIZI_BURAYA_YAZIN')
