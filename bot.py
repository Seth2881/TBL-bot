import discord
from discord.ext import commands
import asyncio
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

TOKEN = "MTQxMjQ4ODYxODY4MTA0NTEzMw.GbC3pc.HjkPUstmcTOPHw_lddEFQEO-HF-UMZJZBYV8Vo"

FORUM_1_ID = 1411136856195596421 # completion
FORUM_2_ID = 1411136498685972649 # submit level
CHANNEL_ID = 1411118206101225613 # changelog

CACHE_FILE = "levels_cache.json"

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f":) Connecté en tant que {bot.user}")
    asyncio.create_task(check_levels_loop())

@bot.event
async def on_thread_create(thread: discord.Thread):
    # Vérifie que c’est bien un forum surveillé
    if isinstance(thread.parent, discord.ForumChannel):
        try:
            first_message = await thread.fetch_message(thread.id)
            titre = thread.name
            contenu = first_message.content
            base = contenu.splitlines()
            auteur = first_message.author

            # Forum 1 : completion
            if thread.parent.id == FORUM_1_ID:
                if len(base) == 2:
                    user = base[0].strip().replace("-pseudo:","")
                    link = base[1].strip().replace("-url:","")
                    data = {
                        "user": user,
                        "link": link,
                        "percent": 100
                    }
                    message = json.dumps(data, indent=4)
                    await thread.send(f"```json\n{message}\n```")
                    await thread.send(f"{auteur.mention} Code javascript généré, veuillez patienter la validation d'un list verifier.")
                else:
                    await thread.send(f"{auteur.mention} Votre post ne respecte pas les critères pour être converti en javascript, votre entrée est donc invalidée, ce post sera supprimé dans 30 secondes.")
                    await asyncio.sleep(30)
                    await thread.delete()
            # Forum 2 : submit level
            elif thread.parent.id == FORUM_2_ID:
                if len(base) == 5 :
                    id = base[0].strip().replace("-id:","")        
                    publisher = base[1].strip().replace("-publisher:","")
                    creators = base[2].strip().replace("-créateur(s):","").split(",")
                    verifier = base[3].strip().replace("-verifier:","")
                    link = base[4].strip().replace("-url:","")
                    if len(titre) <= 20 :
                        data = {
                            "id": id,
                            "name": titre,
                            "author": publisher,
                            "creators": creators,
                            "verifier": verifier,
                            "verification": link,
                            "percentToQualify": "100",
                            "password": "Free To Copy",
                            "records": []
                        }

                        message = json.dumps(data, indent=4)  # formaté avec 4 espaces
                        await thread.send(f"```json\n{message}\n```")
                        await thread.send(f"{auteur.mention} code javascript généré, veuillez patienter la validation d'un list verifier")
                    else :
                        pass
                else:
                    await thread.send(f"{auteur.mention} Votre post ne respecte pas les critères pour être converti en javascript, votre entrée est donc invalidée, **ce post sera supprimé dans 30 secondes.**")
                    await asyncio.sleep(30)
                    await thread.delete()
        except Exception as e:
            print(f"/!\ Impossible de récupérer le premier message : {e}")

async def check_levels_loop():
    while True:
        print("Vérification de la liste des niveaux...")
        messages = await check_levels()
        channel = bot.get_channel(CHANNEL_ID)

        if channel:
            for msg in messages:
                sent_msg = await channel.send(msg)  # envoie le message
                try:
                    # si le salon est un salon annonce, publie le message
                    await sent_msg.publish()
                except Exception as e:
                    print(f"/!\ Impossible de publier le message : {e}")
        else:
            print("Salon Discord introuvable.")

        print("Attente avant la prochaine vérification.\n")
        await asyncio.sleep(10)  # 600 secondes = 10 minutes

async def check_levels():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-software-rasterizer")

    driver = webdriver.Chrome(options=options)
    driver.get('https://thebaguettelistofficiel.pages.dev/')

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".list-container"))
    )

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    list_container = soup.find("div", class_="list-container")

    levels = []
    messages = []
    if list_container:
        rows = list_container.find_all("tr")
        for row in rows:
            rank_td = row.find("td", class_="rank")
            level_td = row.find("td", class_="level")
            if rank_td and level_td:
                rank = rank_td.find("p", class_="type-label-lg").get_text(strip=True)
                name = level_td.find("span", class_="type-label-lg").get_text(strip=True)
                levels.append(name)

        # Charge le cache précédent
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                old_levels = json.load(f)
        else:
            old_levels = []

        if not old_levels:
            messages.append("Première exécution, cache créé.")
        else:
            ajout_ou_suppression = False

            # Ajouts
            for i, name in enumerate(levels):
                if name not in old_levels:
                    messages.append(f"**Ajout** : **{name}** à la position **#{i+1}**")
                    ajout_ou_suppression = True

            # Suppressions
            for name in old_levels:
                if name not in levels:
                    messages.append(f"**Suppression** : **{name}**")
                    ajout_ou_suppression = True

            # Déplacements (uniquement si pas d’ajout/suppression)
            if not ajout_ou_suppression:
                for name in levels:
                    if name in old_levels:
                        old_index = old_levels.index(name)
                        new_index = levels.index(name)
                        if old_index != new_index:
                            messages.append(f"**Déplacement** : **{name}** de la position **#{old_index+1}** à **#{new_index+1}**")

        # Sauvegarde la nouvelle liste
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(levels, f, ensure_ascii=False, indent=2)
    else:
        messages.append("Impossible de trouver la div list-container.")
    return messages


bot.run(TOKEN)
