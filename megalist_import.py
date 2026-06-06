#!/usr/bin/env python3
"""Import Multiplayer Mods MEGA-LIST data into games.db."""

import sys
from database import get_connection, init_db

# ── Raw megalist data ─────────────────────────────────────────────────────────
# Format: (game_title, platform, mod_name, notes)
MEGALIST = [
    # ── WINDOWS PC ─────────────────────────────────────────────────────────────
    ("Age of Mythology: Retold", "Windows PC", "Campaign Co-Op", "2 players"),
    ("Age of Wonders", "Windows PC", "AoW Coop", "Campaigns converted into multiplayer scenarios"),
    ("A Hat In Time", "Windows PC", "Coop Anywhere", ""),
    ("Ale & Tale Tavern", "Windows PC", "MorePlayers", "Adds support for up to 6 players"),
    ("Aliens versus Predator 2", "Windows PC", "Cooperative mod", ""),
    ("Aliens vs Predator", "Windows PC", "Co-Op Campaign", "Map swap, may be buggy"),
    ("Alien Swarm: Reactive Drop", "Windows PC", "32 Player Server", "Adds support for up to 32 players"),
    ("Arma 3", "Windows PC", "Vietcong COOP", "Remake of Vietcong (2003) in Arma 3 w/ Co-op support"),
    ("Armored Core VI: Fires of Rubicon", "Windows PC", "Coop Mod", ""),
    ("Balatro", "Windows PC", "Balatro Multiplayer", ""),
    ("Baldur's Gate 3", "Windows PC", "Party Limit Begone / Versus Mode", "Up to 8 players / Host controls enemies in combat"),
    ("Barony", "Windows PC", "8 Player", "Adds support for up to 8 players"),
    ("Batman: Arkham Asylum", "Windows PC", "Local Co-Op", ""),
    ("BattleBlock Theater", "Windows PC", "4 Player Co-optional", "Play through the 2 player campaign with 4 players"),
    ("Battlefield 2", "Windows PC", "64 Coop", "Adds co-op maps that support up to 64 players with working bots"),
    ("Battlezone 2: Combat Commander", "Windows PC", "Reimagined", "Support for up to 4 players through all but last two missions"),
    ("BeamNG.drive", "Windows PC", "KISS Multiplayer / BeamMP", ""),
    ("Bendy and the Dark Revival", "Windows PC", "BATDR Multiplayer", ""),
    ("Binding of Isaac", "Windows PC", "Local PVP", "Player 2 controls the enemies"),
    ("Black Mesa", "Windows PC", "SourceCoop", ""),
    ("Black Myth: Wukong", "Windows PC", "WukongMP", "Adds campaign co-op & PVP/PVE modes (up to 10 players)"),
    ("Black Souls", "Windows PC", "Multi", ""),
    ("Black Souls 2", "Windows PC", "Multi", ""),
    ("Blade & Sorcery", "Windows PC", "Adammantium's Multiplayer Mod", ""),
    ("Blasphemous", "Windows PC", "Multiplayer", ""),
    ("Blood 2: The Chosen", "Windows PC", "Co-op Addon", ""),
    ("Bomberman", "Windows PC", "Power Bomberman", "Remade games from series combined into one w/ netplay"),
    ("Bomb Rush Cyberfunk", "Windows PC", "SlopCrew", ""),
    ("Bonelab", "Windows PC", "Fusion", ""),
    ("Bopl Battle", "Windows PC", "MoreBoplPlayers", "Adds support for up to 8 players"),
    ("Broforce", "Windows PC", "Control Enemies Mod", "Player 2 controls the enemies"),
    ("Brotato", "Windows PC", "Brotatogether", ""),
    ("Bubble Bobble", "Windows PC", "The Bub's Brothers", "PC remake of Bubble Bobble (NES) + 10 player local & online co-op"),
    ("Bully: Scholarship Edition", "Windows PC", "Bash-Coop", "2 Player Local"),
    ("Cairn", "Windows PC", "Episure", ""),
    ("Call of Duty: Black Ops", "Windows PC", "Black Ops Coop", "Russian language only(?)"),
    ("Call of Duty: Modern Warfare 2", "Windows PC", "MW 2 COOP", "Russian language only(?)"),
    ("Call to Arms", "Windows PC", "16 Players", "Adds support for up to 16 players"),
    ("Call to Arms - Gates of Hell: Ostfront", "Windows PC", "Increased player slots", "Adds support for up to 16 players"),
    ("Car Mechanic Simulator 2021", "Windows PC", "CMS21 Together", ""),
    ("Casualties: Unknown", "Windows PC", "Casualties: Together", ""),
    ("Cave Story", "Windows PC", "Multiplayer", ""),
    ("Celeste", "Windows PC", "CelesteNet", ""),
    ("Choo-Choo Charles", "Windows PC", "Skizzium's Discord", ""),
    ("Cities: Skylines", "Windows PC", "Multiplayer", ""),
    ("Civilization 2", "Windows PC", "FreeCiv", "Open source remake w/ multiplayer support"),
    ("Clair Obscur: Expedition 33", "Windows PC", "Coop Mod", "Battles only w/ alternating world control"),
    ("Command & Conquer: Red Alert", "Windows PC", "OpenRA Coop Campaigns", "Adds co-op (1-6 players) to C&C campaigns"),
    ("Cosmoteer: Starship Architect & Commander", "Windows PC", "More Balanced Multiplayer", "Adds support for up to 8 players"),
    ("Crash Bash", "Windows PC", "Crash Bash LIVE", "Fan remake w/ online & multiple gameplay modes"),
    ("CrossCode", "Windows PC", "coop/multiplayer", ""),
    ("Crysis", "Windows PC", "Crysis Co-Op", ""),
    ("Cult of the Lamb", "Windows PC", "WW_COOP SYSTEM", ""),
    ("Dance of Fire and Ice", "Windows PC", "Together", ""),
    ("Dark Messiah of Might and Magic", "Windows PC", "Dark Messiah Coop", ""),
    ("Dark Souls", "Windows PC", "Seamless Co-Op", "Play co-op without summoning boundaries"),
    ("Dark Souls II", "Windows PC", "Open Server", "Host a private server for playing multiplayer w/ mods"),
    ("Dark Souls III", "Windows PC", "Seamless Co-Op / Open Server", "Play co-op without summoning boundaries"),
    ("Dawn of War", "Windows PC", "DoW Online", "Overall improvement on multiplayer systems + ladder"),
    ("Dead Cells", "Windows PC", "Multiplayer Mod", ""),
    ("Death's Door", "Windows PC", "WW_COOP SYSTEM", ""),
    ("Deep Rock Galactic", "Windows PC", "More Players Balanced", "Up to 24 players (lobby only)"),
    ("Delta Force: Black Hawk Down", "Windows PC", "Co-op Campaign Mod", "Plays best w/ up to 10 players"),
    ("Deltarune", "Windows PC", "Local Multiplayer Mod", "Up to 4 players (first 4 chapters so far)"),
    ("Derail Valley", "Windows PC", "DV Multiplayer", ""),
    ("Deus Ex", "Windows PC", "HX", ""),
    ("Devil May Cry 3", "Windows PC", "DDMK", "4 players"),
    ("Devil May Cry 5", "Windows PC", "COOP Trainer", ""),
    ("Diablo", "Windows PC", "DevilutionX / The Hell 3", "Mod suite w/ multiplayer support"),
    ("Diablo II: Lord of Destruction", "Windows PC", "Median XL Ultimative / Path of Diablo / Project Diablo 2", "Community servers & more"),
    ("Diablo III: Reaper of Souls", "Windows PC", "Blizless DIIIS", "Play multiplayer on a local server"),
    ("Divinity: Original Sin", "Windows PC", "Gandos Unlimited Party", "Support for up to 12 players in co-op"),
    ("Divinity: Original Sin 2", "Windows PC", "Expanded Party Size", "Up to 7 players"),
    ("Don't Starve Together", "Windows PC", "Increased Max Players", ""),
    ("DOOM 3", "Windows PC", "dhewm3 + Librecoop", ""),
    ("DOOM (2016)", "Windows PC", "Snapmaps / Co-op Maps", "User-created maps downloadable in-game"),
    ("DOOM Eternal", "Windows PC", "Co-operative Mode", ""),
    ("DREDGE", "Windows PC", "Cosmic Horror Fishing Buddies", ""),
    ("Dungeon Keeper", "Windows PC", "KeeperFX", "Remake w/ restored multiplayer + QOL improvements"),
    ("Dungeon Master", "Windows PC", "DMNet", ""),
    ("Dyson Sphere Program", "Windows PC", "Nebula", ""),
    ("Elden Ring", "Windows PC", "Seamless Co-Op", ""),
    ("Elden Ring: Nightreign", "Windows PC", "Seamless Co-Op", ""),
    ("Elder Scrolls II: Daggerfall", "Windows PC", "DFU Tanguy's Multiplayer", "Mod for the Unity remake"),
    ("Elder Scrolls III: Morrowind", "Windows PC", "TES3MP", ""),
    ("Elder Scrolls IV: Oblivion", "Windows PC", "Online Mod - MadeEasy / Co-Op Oblivion", ""),
    ("Elder Scrolls IV: Oblivion Remastered", "Windows PC", "Ghosts of Tamriel", "Soulslike player messages in-world"),
    ("Elder Scrolls V: Skyrim", "Windows PC", "Skyrim Together / Adventurers Like You / Keizaal Online", "Full co-op / local co-op / Persistent MMORPG"),
    ("Erenshor", "Windows PC", "COOP", ""),
    ("Escape from Duckov", "Windows PC", "Coop Mod", "Adds support for unlimited(?) players"),
    ("Escape From Tarkov", "Windows PC", "Stay In Tarkov / FIKA Project", ""),
    ("Euro Truck Simulator 2", "Windows PC", "TruckersMP", ""),
    ("Europa Universalis IV", "Windows PC", "HashMP", ""),
    ("Fallout 2", "Windows PC", "FOnline: Reloaded / FOnline 2 / FOnline: Ashes of Phoenix", "Massively-Multiplayer, supports local servers"),
    ("Fallout 3", "Windows PC", "VaultMP", ""),
    ("Fallout: New Vegas", "Windows PC", "NVMP", "Local or 50-player public server"),
    ("Far Cry", "Windows PC", "FCAV", ""),
    ("Far Cry 3", "Windows PC", "Open World Co-Op Mod", "No campaign"),
    ("Far Cry 4", "Windows PC", "Campaign Co-op", "Support for two players through the campaign"),
    ("Far Far West", "Windows PC", "More Players Mod", "Support for up to 8 players + more"),
    ("FAR: Lone Sails", "Windows PC", "WW_COOP SYSTEM", ""),
    ("F.E.A.R.", "Windows PC", "Co-Op Mod", ""),
    ("Fear & Hunger", "Windows PC", "Multiplayer Mod", ""),
    ("Fez", "Windows PC", "FezMultiplayerMod", ""),
    ("Firewatch", "Windows PC", "Two-Forks Multiplayer", "Free roam only"),
    ("Forager", "Windows PC", "PencilPal", ""),
    ("Friday Night Funkin'", "Windows PC", "Multiplayer / Psych Online", ""),
    ("Getting Over It", "Windows PC", "Oxide MP", ""),
    ("Geometry Dash", "Windows PC", "Globed", ""),
    ("Gothic", "Windows PC", "Gothic Online / Gothic Coop", "Massively-Multiplayer / Private Servers"),
    ("Gothic II", "Windows PC", "Gothic Coop", "Private Servers"),
    ("GTA2 Grand Theft Auto 2", "Windows PC", "Co-op Campaign Mode / Splitscreen Mod", "In development / Support for up to 6 players"),
    ("Grand Theft Auto III", "Windows PC", "Grand Theft Auto Connected", ""),
    ("Grand Theft Auto: Vice City", "Windows PC", "VC 2 Players Mod", "Play through the SP campaign"),
    ("Grand Theft Auto: San Andreas", "Windows PC", "2 Player Deluxe / MTA / open.mp", ""),
    ("Grand Theft Auto V", "Windows PC", "RAGECOOP", ""),
    ("GTFO", "Windows PC", "LobbyExpansion", "Adds support for up to 8 players"),
    ("Hades", "Windows PC", "Co-op", "Local co-op support for 2 players"),
    ("Hades II", "Windows PC", "CoopMod", "Local co-op"),
    ("Halo: Master Chief Collection", "Windows PC", "Splitscreen Mod", "Adds 4-player splitscreen to all games"),
    ("Half-Life", "Windows PC", "Sven Co-Op", ""),
    ("Half-Life 2", "Windows PC", "Synergy / SourceCoop", ""),
    ("Half-Life: Alyx", "Windows PC", "Kiwi's Co-Op", ""),
    ("Hello Neighbor", "Windows PC", "HelloMultiplayer", "Support for 2 players up to Act 1"),
    ("Hobbit", "Windows PC", "Synchrony", ""),
    ("Hogwarts Legacy", "Windows PC", "HogWarp", ""),
    ("Hollow Knight", "Windows PC", "HKMP / SilklessCoop", ""),
    ("Hollow Knight: Silksong", "Windows PC", "Steam Multiplayer Mod / Legacy of the Abyss", "WIP / Full co-op with unique companion"),
    ("HoloCure: Save the Fans!", "Windows PC", "Multiplayer Mod", ""),
    ("Hot Dogs, Horseshoes & Hand Grenades", "Windows PC", "H3MP", ""),
    ("Jak & Daxter: The Precursor Legacy", "Windows PC", "Teamruns", "Mod for the OpenGOAL PC port"),
    ("Jak II", "Windows PC", "Coop multiplayer mod", "Mod for the OpenGOAL PC port"),
    ("Jak 3", "Windows PC", "Coop multiplayer mod", "Mod for the OpenGOAL PC port"),
    ("Just Cause 2", "Windows PC", "JC2-MP", ""),
    ("Just Cause 3", "Windows PC", "JC3-MP", ""),
    ("Katana Zero", "Windows PC", "Multiplayer", ""),
    ("Kerbal Space Program", "Windows PC", "Luna multiplayer", ""),
    ("Kingdom Hearts 3", "Windows PC", "C-ModMenu", ""),
    ("Kingpin: Life of Crime", "Windows PC", "Multiplayer", ""),
    ("Left 4 Dead", "Windows PC", "Left 4 Dead Slots", "Adds support for up to 32 players"),
    ("Legend of Zelda: Ocarina of Time", "Windows PC", "Anchor", "Mod for Ship of Harkinian PC port"),
    ("Lemnis Gate", "Windows PC", "Salvage Ops", ""),
    ("Lethal Company", "Windows PC", "MoreCompany / ControlCompany", "Up to 8 players / Host can control enemies"),
    ("Long Dark", "Windows PC", "SkyCoop", ""),
    ("Long Drive", "Windows PC", "Splitscreen Multiplayer", ""),
    ("Lord of the Rings: Conquest", "Windows PC", "30FPS and 16 Campaign Players Multiplayer Patch", "Raises framerate to allow up to 16 players"),
    ("Marathon / Marathon 2 / Marathon Infinity", "Windows PC", "Aleph One", "Open source port w/ expanded multiplayer modes"),
    ("Mario vs. Luigi", "Windows PC", "NSMB Mario vs. Luigi Online", "Unity remake of the NSMB DS game mode w/ online multiplayer"),
    ("Master of Magic", "Windows PC", "IME", "Java rewrite with multiplayer support"),
    ("Medal of Honor: Allied Assault", "Windows PC", "HaZardModding Co-Op", ""),
    ("Metal Gear Survive", "Windows PC", "Freeroam Co-op", "Africa map only"),
    ("Metal Gear Online", "Windows PC", "MGO2PC", "Revival of MGO for PC & PS3"),
    ("Metal Gear Rising: Revengeance", "Windows PC", "2 Players Mode", ""),
    ("Metal Gear Solid V: The Phantom Pain", "Windows PC", "dynamite", "2 players"),
    ("Metroid", "Windows PC", "Metroid Planets", "PC remake + online multiplayer + random map generator"),
    ("Might and Magic VI / VII / VIII", "Windows PC", "Multiplayer for MMMerge", "Mod for MMMerge PC port"),
    ("Mirror's Edge", "Windows PC", "Multiplayer Mod", ""),
    ("Mon Bazou", "Windows PC", "MP", "Up to 4 players"),
    ("Monstrum", "Windows PC", "Monstrum Extended Settings Mod", ""),
    ("Mount & Blade: Warband", "Windows PC", "Battle Time", "Battles only"),
    ("Mount & Blade II: Bannerlord", "Windows PC", "Bannerlord Online / Full Invasion 3 / Bannerlord Together", "MMO / Custom invasions / Campaign co-op"),
    ("Mycopunk", "Windows PC", "BigLobbyMod", "Support for up to 32 players"),
    ("My Summer Car", "Windows PC", "MSCO / WreckMP", ""),
    ("Noita", "Windows PC", "Noita Together / Noita Entangled Worlds", ""),
    ("No One Lives Forever", "Windows PC", "Co-Op Mod Complete", ""),
    ("No One Lives Forever 2", "Windows PC", "Coop Mod", ""),
    ("Nox", "Windows PC", "OpenNox", "Open source remake w/ online servers (requires original game)"),
    ("Nuclear Throne", "Windows PC", "Nuclear Throne Together", ""),
    ("Ori and the Blind Forest", "Windows PC", "WW_COOP SYSTEM", ""),
    ("Ori and the Will of the Wisps", "Windows PC", "WW_COOP SYSTEM", ""),
    ("Outer Wilds", "Windows PC", "Outer Wilds Online / Quantum Space Buddies", "Separate games w/ chat / Full campaign co-op"),
    ("Outward", "Windows PC", "Raid Mode", "Adds support for up to 10 players"),
    ("Overgrowth", "Windows PC", "Overgrowth Story Multiplayer / Lugaru Campaign Co-op", ""),
    ("Oxygen Not Included", "Windows PC", "Multiplayer Mod", ""),
    ("Painkiller", "Windows PC", "Cooperative mode", ""),
    ("PEAK", "Windows PC", "Unlimited", "Adds support for unlimited(?) players"),
    ("Phasmophobia", "Windows PC", "8 Player Mod", "Adds support for up to 8 players"),
    ("Pizza Tower", "Windows PC", "Noise Co-op", "Full feature simultaneous co-op with splitscreen support"),
    ("Plants vs. Zombies", "Windows PC", "Competitive Adventure", ""),
    ("Plants vs. Zombies: Garden Warfare 2", "Windows PC", "Co-op Mod", ""),
    ("Pokemon Red / Blue", "Windows PC", "Pokemon 3D / PokeMMO", "Massively-Multiplayer"),
    ("Portal", "Windows PC", "Portal 1 Multiplayer In Portal 2 Co-Op", ""),
    ("Portal 2", "Windows PC", "Portal 1 Multiplayer In Portal 2 Co-Op / Multiplayer Mod", "Support for up to 33 players"),
    ("Postal 2", "Windows PC", "NicksCoop", ""),
    ("PULSAR: Lost Colony", "Windows PC", "Max Players", "Support for up to 64 players"),
    ("Quake", "Windows PC", "Millennium Co-Op", "Greatly improved co-op gameplay & challenge balancing"),
    ("Quake 4", "Windows PC", "OpenCoop", ""),
    ("Rain World", "Windows PC", "Rain Meadow", ""),
    ("Ravenfield", "Windows PC", "RavenM", ""),
    ("Rayman M / Arena", "Windows PC", "Rayman Arena Online", ""),
    ("Ready or Not", "Windows PC", "Simple Mod Menu and Blueprint Loader", "Allows you to increase player limit + more"),
    ("Red Dead Redemption", "Windows PC", "RDRMP", "Custom server support"),
    ("Red Dead Redemption 2", "Windows PC", "RedM", "Custom server support"),
    ("Remnant: From the Ashes", "Windows PC", "6 Player Co-Op Mod", ""),
    ("Remnant II", "Windows PC", "More Players Mod", "Support for up to 8 players in all game content"),
    ("Resident Evil 0", "Windows PC", "HD Remaster Trainer", ""),
    ("Resident Evil 4", "Windows PC", "Co/operative / UHD Multiplayer Mod", ""),
    ("Resident Evil 5", "Windows PC", "4-Player Mod", ""),
    ("Return to Castle Wolfenstein", "Windows PC", "RTCWCOOP", ""),
    ("R.E.P.O.", "Windows PC", "MorePlayers", "Unlock the player cap"),
    ("Reventure", "Windows PC", "Hyaku", ""),
    ("RimWorld", "Windows PC", "Zeltrith's Mod / RimWorld Together", "Real-Time Co-Op / MMO Style"),
    ("Risk of Rain 2", "Windows PC", "XSplitScreen", "Split-screen support"),
    ("Road to Vostok", "Windows PC", "RTVCoop", ""),
    ("RollerCoaster Tycoon 2", "Windows PC", "OpenRCT2", "Open source remake w/ multiplayer support"),
    ("Rune", "Windows PC", "Rune Co-op mod", ""),
    ("RV There Yet", "Windows PC", "MoreRVers", "Increase max players"),
    ("Saints Row 2", "Windows PC", "Multiplayer Restored", ""),
    ("Schedule I", "Windows PC", "Servers Mod + Client Mod", "Servers, expands player cap + more"),
    ("SCP-087-B", "Windows PC", "Multiplayer Mod", ""),
    ("SCP - Containment Breach", "Windows PC", "Multiplayer", "Remake w/ multiplayer modes"),
    ("Sekiro: Shadows Die Twice", "Windows PC", "Sekiro Online", ""),
    ("Severance: Blade of Darkness", "Windows PC", "Coop Mod", ""),
    ("Shogo: Mobile Armor Division", "Windows PC", "Shogo Co-Op", ""),
    ("Signalis", "Windows PC", "CoOp Mod Testing", "Buggy / lacks features - Open testing"),
    ("SimplePlanes", "Windows PC", "Multiplayer", ""),
    ("Sims 4", "Windows PC", "S4MP", ""),
    ("Slay The Spire", "Windows PC", "Spire With Friends / Together in Spire", ""),
    ("Slime Rancher", "Windows PC", "SRMP", ""),
    ("Slime Rancher 2", "Windows PC", "NewSR2MP", ""),
    ("Software Inc.", "Windows PC", "Multiplayer Mod", ""),
    ("Sonic Adventure DX", "Windows PC", "SADX Multiplayer", ""),
    ("Sonic A.I.R.", "Windows PC", "Co-Op Deluxe", "Improves co-op functionality"),
    ("Sonic Frontiers", "Windows PC", "Multiplayer", "Multiplayer for SF + HE2 engine"),
    ("Spelunky Classic", "Windows PC", "Spelunky SD", "Support for 2 player online multiplayer + QOL fixes"),
    ("Spelunky HD", "Windows PC", "Frozlunky", "Support for online multiplayer, custom maps + more"),
    ("Spyro: Year of the Dragon", "Windows PC", "Sprash Co-op", "Spyro 3 remade in Unreal Engine with 2-player co-op (Player 2 is Crash Bandicoot!)"),
    ("Marvel's Spider-Man", "Windows PC", "Spider-Man Multiplayer", ""),
    ("Spyro Reignited Trilogy", "Windows PC", "Local Co-Op with Skin Swapping", ""),
    ("S.T.A.L.K.E.R.: Call of Pripyat", "Windows PC", "X-Ray Multiplayer Extension / STALKER TOGETHER", ""),
    ("S.T.A.L.K.E.R.: Shadow of Chernobyl", "Windows PC", "Shadow of Co-op", ""),
    ("StarCraft: Brood War", "Windows PC", "Co-op Campaign / Shield Battery", "Play campaigns w/ 2nd player / Improved multiplayer systems"),
    ("Stardew Valley", "Windows PC", "Unlimited Players", ""),
    ("Stardew Valley: Journey of the Prairie King", "Windows PC", "Multiplayer", ""),
    ("Star Trek: Elite Force II", "Windows PC", "HazardModding Coop", ""),
    ("Star Wars: Battlefront 2 (2005)", "Windows PC", "Campaign in Multiplayer Commands", "Guide for adding campaign maps to multiplayer"),
    ("Star Wars: Jedi Academy", "Windows PC", "OJP Enhanced Universe", ""),
    ("Star Wars Jedi Knight: Dark Forces II", "Windows PC", "Single Player CO-OP", ""),
    ("Stray", "Windows PC", "Splitscreen", ""),
    ("Subnautica", "Windows PC", "Nitrox", ""),
    ("Subnautica: Below Zero", "Windows PC", "Multiplayer Mod", ""),
    ("Subnautica 2", "Windows PC", "Too Many Divers", "Adds support for up to 16 players in co-op"),
    ("Super Mario 64", "Windows PC", "Coop Deluxe / Mob Control", "Full co-op / Players can control some enemies"),
    ("Super Mario Kart", "Windows PC", "ZX", "Remake w/ 4 player support"),
    ("Super Mario World", "Windows PC", "SMW Remastered", "Remake in Godot w/ 4 player co-op"),
    ("Supreme Commander 2", "Windows PC", "Co-Op Campaign Mod / Forged Alliance Forever", "Campaign co-op / Multiplayer servers w/ 4 player co-op campaigns"),
    ("Tales of Arise", "Windows PC", "Multiplayer Mod", ""),
    ("Teardown", "Windows PC", "TDMP", ""),
    ("Thief 2: The Metal Age", "Windows PC", "T2Fix", ""),
    ("Thronefall", "Windows PC", "Multiplayer", ""),
    ("Timberborn", "Windows PC", "Beaver Buddies", ""),
    ("Titanfall 2", "Windows PC", "Northstar", ""),
    ("Tony Hawk's Underground 2", "Windows PC", "THUG Pro", "THUG2 online + maps from the whole series"),
    ("Tony Hawk's American Wasteland", "Windows PC", "ReTHAWed", "Overhaul mod with multiplayer"),
    ("Tomb Raider Remastered I-III", "Windows PC", "Multiplayer Mod", ""),
    ("Tomb Raider 2", "Windows PC", "Multiplayer Mod", ""),
    ("Townscaper", "Windows PC", "LittleMultiplayer", ""),
    ("Towerfall", "Windows PC", "TF.EX", ""),
    ("Turok 2", "Windows PC", "Co-Op", ""),
    ("Turok: Evolution", "Windows PC", "T4MP", "Adds online multiplayer to the PC port"),
    ("Ty the Tasmanian Tiger", "Windows PC", "Mul-Ty-Player", ""),
    ("ULTRAKILL", "Windows PC", "Join and kill em together", ""),
    ("Undertale", "Windows PC", "Undertale Together / Undertale Connect", "Support for up to 2 / 10 players"),
    ("Clive Barker's Undying", "Windows PC", "Undying Renewal", "Multiplayer, QOL improvements, more!"),
    ("Unreal", "Windows PC", "Wolf Coop / OldUnreal", "Expands & improves on native coop / Community patches"),
    ("Unreal Tournament series", "Windows PC", "OldUnreal / foxMod", "Community patches / Splitscreen support"),
    ("Vampire: The Masquerade - Bloodlines", "Windows PC", "VTMBMP", "Full featured PVP modes with limited co-op modes"),
    ("Vampire: The Masquerade - Redemption", "Windows PC", "Age of Redemption", "QOL overhaul + full SP campaign in multiplayer, up to 8 players"),
    ("Warcraft II", "Windows PC", "War2 - Multiplayer Campaign", ""),
    ("Warcraft III", "Windows PC", "2-Player Campaign / W3Champions / 8-Player Co-Op Campaign / Campaign Splitter", "Campaign co-op / Improved multiplayer / Up to 8 players"),
    ("Wargroove", "Windows PC", "Coop Conversion Project", ""),
    ("Wargroove 2", "Windows PC", "Coop Campaign Conversion Project", "Hotseat suggested - online is buggy"),
    ("Warhammer 40,000: Space Marine 2", "Windows PC", "12-Player Co-Op", "Adds support for 9 more players"),
    ("Warhammer: Vermintide 2", "Windows PC", "BTMP More Players Fix", "Adds support for more players"),
    ("Wayfinder", "Windows PC", "MorePlayers", "Adds support for more players"),
    ("William Shatner's TekWar", "Windows PC", "Tekwar Improved COOP Mod", ""),
    ("Witcher 3: Wild Hunt", "Windows PC", "Witcher Online", ""),
    ("Wolfenstein 3D", "Windows PC", "COOP+DM", ""),
    ("WRATH: Aeon of Ruin", "Windows PC", "Multiplayer and Coop", ""),
    ("X-COM: UFO Defense / Terror from the Deep", "Windows PC", "UFO: The Two Sides 2 / OpenXcom Coop", "Fan remakes w/ multiplayer support"),
    ("Yakuza 0", "Windows PC", "Co-Op", "Local co-op up to 4 players"),
    ("Yakuza: Like A Dragon", "Windows PC", "Heroes of Yokohama", "Local co-op up to 4 players"),
    ("Ys I & II Chronicles", "Windows PC", "Ys Chronicles Co-Op Mod", ""),
    ("Yume Nikki / Yume 2kki / collective unconscious", "Windows PC", "YNOproject", "Massively-Multiplayer Online walking simulators!"),

    # ── NINTENDO SWITCH ─────────────────────────────────────────────────────────
    ("Super Mario 3D World", "Nintendo Switch", "Bowser's Fury Online", "Bowser's Fury with 5 players"),
    ("Super Mario Odyssey", "Nintendo Switch", "Online Multiplayer / Kirbymimi's Mod", ""),
    ("Legend of Zelda: Breath of the Wild", "Nintendo Switch", "Couch Coop Multiplayer / Milk Bar Launcher / Kirbymimi's Mod", "Split-screen up to 4 players"),
    ("Legend of Zelda: Link's Awakening", "Nintendo Switch", "Kirbymimi's Mod", ""),
    ("Legend of Zelda: Tears of the Kingdom", "Nintendo Switch", "Kirbymimi's Mod", ""),

    # ── SONY PLAYSTATION 4 ──────────────────────────────────────────────────────
    ("Bloodborne", "Sony PlayStation 4", "The Hunter's Dream", "Enables online play through shadPS4 emulator; brings co-op features to PC"),

    # ── NINTENDO Wii ────────────────────────────────────────────────────────────
    ("Legend of Zelda: Skyward Sword", "Nintendo Wii", "Kirbymimi's Mod", ""),
    ("Super Mario Galaxy", "Nintendo Wii", "Multiplayer", "Split-screen"),
    ("Super Mario Galaxy 2", "Nintendo Wii", "Under Mario's Hat's Discord", ""),

    # ── SONY PLAYSTATION PORTABLE ───────────────────────────────────────────────
    ("Tales of Phantasia X", "Sony PSP", "Multiplayer Patch", "Support for up to 4 players"),

    # ── NINTENDO DS ─────────────────────────────────────────────────────────────
    ("Super Mario 64 DS", "Nintendo DS", "Multiplayer", "Single-screen local co-op"),
    ("New Super Mario Bros.", "Nintendo DS", "Co-Op", ""),

    # ── NINTENDO GAMECUBE ───────────────────────────────────────────────────────
    ("Gotcha Force", "Nintendo GameCube", "2P Story Mode", ""),
    ("Legend of Zelda: The Wind Waker", "Nintendo GameCube", "BrandenEK's Mod / Kirbymimi's Mod", ""),
    ("Legend of Zelda: Twilight Princess", "Nintendo GameCube", "Kirbymimi's Mod", ""),
    ("Luigi's Mansion", "Nintendo GameCube", "2-Player Co-Op Mode / Co-Op Mod", ""),
    ("Mario Kart: Double Dash!!", "Nintendo GameCube", "MKDD Online", ""),
    ("Mario Power Tennis", "Nintendo GameCube", "Doubles 2 Player Netplay (Action Replay)", ""),
    ("Pikmin", "Nintendo GameCube", "Multiplayer Edition / Pikmin 1²", ""),
    ("Pikmin 2", "Nintendo GameCube", "Multiplayer Edition / PikHacker's Multiplayer", ""),
    ("Shadow the Hedgehog", "Nintendo GameCube", "2P-ShdTH Multiplayer Mod", ""),
    ("SpongeBob SquarePants: Battle for Bikini Bottom", "Nintendo GameCube", "Multiplayer", "Split-screen"),
    ("Super Mario Sunshine", "Nintendo GameCube", "Multiplayer Patch / Sunshine Co-Op / Eclipse Co-op", "Single-camera multiplayer / Split-screen multiplayer"),
    ("Wario World", "Nintendo GameCube", "Multiplayer", "Split-screen"),

    # ── NINTENDO GAME BOY ADVANCE ───────────────────────────────────────────────
    ("Mega Man Battle Network series", "Nintendo GBA", "Tango", "Play online with rollback netcode"),
    ("Metroid: Zero Mission / Metroid: Fusion", "Nintendo GBA", "Bizhawk", ""),
    ("Pokemon FireRed & LeafGreen", "Nintendo GBA", "PK-GBA Multiplayer", ""),
    ("Pokemon Emerald", "Nintendo GBA", "Pokemon Quetzal", "Support for up to 4 players"),
    ("Sword of Mana", "Nintendo GBA", "Link Cable 2Player Mode / Ultimate Coop Hack", "Restores inactive co-op mode"),

    # ── SONY PLAYSTATION 2 ──────────────────────────────────────────────────────
    (".hack//fragment", "Sony PlayStation 2", "Netslum Server", "Revival project w/ private servers"),
    ("Monster Hunter / Monster Hunter G / Monster Hunter 2", "Sony PlayStation 2", "MH Oldschool", "Revival project w/ private servers"),
    ("Resident Evil Outbreak / File #2", "Sony PlayStation 2", "OBSRV", ""),
    ("Tales of Legendia", "Sony PlayStation 2", "Multiplayer Patch", "2 player support"),

    # ── NINTENDO 64 ─────────────────────────────────────────────────────────────
    ("Banjo Kazooie", "Nintendo 64", "Online Co-op + Character Switcher", ""),
    ("Bomberman 64", "Nintendo 64", "Co-Op Patch", ""),
    ("Duke Nukem 64", "Nintendo 64", "4-Player Coop", ""),
    ("GoldenEye 64", "Nintendo 64", "GoldenEye X / Dual Eyes Cooperative", "Ported to Perfect Dark / Co-op & counter-op"),
    ("Jet Force Gemini", "Nintendo 64", "Trainer and Co-Op Hack", ""),
    ("Legend of Zelda: Ocarina of Time", "Nintendo 64", "OotModLoader w/ OotOnline", ""),
    ("Mystical Ninja 2 Starring Goemon", "Nintendo 64", "4-Player coop unlocked", "Makes 4 players available at the start"),
    ("Paper Mario", "Nintendo 64", "Skelux's Multiplayer", ""),
    ("Super Mario 64", "Nintendo 64", "Splitscreen Multiplayer", ""),

    # ── SONY PLAYSTATION ────────────────────────────────────────────────────────
    ("Crash Team Racing", "Sony PlayStation", "OnlineCTR", "Fan mod with online play"),
    ("Spyro 2: Ripto's Rage!", "Sony PlayStation", "Spyro 2x2", "Split-screen support"),

    # ── SUPER NINTENDO ──────────────────────────────────────────────────────────
    ("Chrono Trigger", "Super Nintendo", "Multiplayer Hack", "Up to 3 players (in combat)"),
    ("Donkey Kong Country", "Super Nintendo", "2P Proof of Concept", ""),
    ("Final Fantasy V", "Super Nintendo", "Coop Controller Sharing Hack", "Choose which player controls the game outside of battles"),
    ("Legend of Zelda: A Link to the Past", "Super Nintendo", "ALttP Online", "8+ players"),
    ("Lost Vikings", "Super Nintendo", "Ragnarok Edition", "3 player support + extras"),
    ("Secret of Evermore", "Super Nintendo", "2 Player Edition", ""),
    ("Seiken Densetsu 3", "Super Nintendo", "3-Player Hack", ""),
    ("Star Fox", "Super Nintendo", "Starfox: EX", ""),
    ("Super Mario RPG", "Super Nintendo", "Multiplayer Hack", ""),
    ("Super Mario World", "Super Nintendo", "Co-Op Hack", ""),
    ("Super Metroid", "Super Nintendo", "Multiroid", ""),

    # ── NINTENDO GAME BOY ───────────────────────────────────────────────────────
    ("Metroid II: Return of Samus", "Nintendo Game Boy", "AM2R Multiroid", "Fan mod for AM2R remake"),

    # ── SEGA GENESIS ────────────────────────────────────────────────────────────
    ("Sonic The Hedgehog", "Sega Genesis", "Sonic 2 co-op Demo / Sonic Classic Heroes", "Full-feature split-screen co-op / 3 player co-op through Sonic 1 & 2"),

    # ── NINTENDO ENTERTAINMENT SYSTEM ──────────────────────────────────────────
    ("Balloon Fight", "NES", "4 Players Hack", ""),
    ("Battle City", "NES", "4 Players Hack", ""),
    ("Battletoads", "NES", "Battletoads 4 Players", ""),
    ("Battletoads & Double Dragon", "NES", "Battletoads & Double Dragon 4 Players", ""),
    ("Bomberman (NES)", "NES", "Bomberman Co-Op", ""),
    ("Double Dragon", "NES", "Real Double Dragon", "2 players"),
    ("DuckTales 2", "NES", "Two Players Hack", ""),
    ("Final Fantasy III (VI)", "NES", "Coop 2 Player Hack", "Players alternate overworld control"),
    ("Final Fight", "NES", "2 Players Hack", ""),
    ("Ice Climbers", "NES", "4 Player Hack", ""),
    ("Legend of Zelda (NES)", "NES", "Kirbymimi's Mod", "2 players"),
    ("Mario Bros.", "NES", "4 players hack", ""),
    ("Mighty Final Fight", "NES", "Mighty Final Fight For 2 Players", "Player 2 controls enemies"),
    ("Nekketsu Fighting Legend", "NES", "4 Player", ""),
    ("New Ghostbusters II", "NES", "2 Players", ""),
    ("P.O.W.: Prisoners of War", "NES", "Two Players Hack", ""),
    ("Super Dodge Ball", "NES", "4 Player Hack", ""),
    ("Super Mario Bros.", "NES", "Two Players Hack / Super Mario Bro-Op", "Both players play together"),
    ("Super Mario Bros. 3", "NES", "smb32p", "Player 2 controls a passive cheep-cheep"),
    ("Popeye (NES)", "NES", "Super Popeye", "Player 2 controls Bluto"),
    ("Wrecking Crew", "NES", "Wrecking Two", "Levels redesigned for co-op"),
    ("Zelda II: The Adventure of Link", "NES", "Z22: The Adventure of Link and Lonk", ""),

    # ── ARCADE ─────────────────────────────────────────────────────────────────
    ("Donkey Kong", "Arcade", "DKBros", ""),
]

BASE_ID = 20_000_000


def sync_megalist():
    """Import all megalist entries into the database."""
    init_db()
    conn = get_connection()

    # Ensure columns exist (migration)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(games)").fetchall()}
    if "platform" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN platform TEXT")
    if "mod_name" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN mod_name TEXT")
    if "mod_notes" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN mod_notes TEXT")
    conn.commit()

    inserted = 0
    updated = 0

    for idx, (title, platform, mod_name, mod_notes) in enumerate(MEGALIST):
        new_id = BASE_ID + idx

        # Check if an existing game (OFME/freetp) matches this title
        existing = conn.execute(
            "SELECT id, sources FROM games WHERE LOWER(title) = LOWER(?) AND sources != 'megalist'",
            (title,)
        ).fetchone()

        if existing:
            # Update existing entry to add megalist info
            old_sources = existing["sources"] or "ofme"
            if "megalist" not in old_sources:
                new_sources = old_sources + ",megalist"
            else:
                new_sources = old_sources
            conn.execute(
                "UPDATE games SET platform=?, mod_name=?, mod_notes=?, sources=? WHERE id=?",
                (platform, mod_name, mod_notes, new_sources, existing["id"])
            )
            updated += 1
        else:
            # Check if megalist entry already exists
            row = conn.execute("SELECT id FROM games WHERE id=?", (new_id,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE games SET title=?, platform=?, mod_name=?, mod_notes=?, sources='megalist', has_multiplayer=1 WHERE id=?",
                    (title, platform, mod_name, mod_notes, new_id)
                )
            else:
                conn.execute(
                    """INSERT INTO games (id, title, platform, mod_name, mod_notes, sources, has_multiplayer,
                                         category, views, comments, has_coop, scraped_at)
                       VALUES (?, ?, ?, ?, ?, 'megalist', 1, 'Multiplayer Mod', 0, 0, 1, datetime('now'))""",
                    (new_id, title, platform, mod_name, mod_notes)
                )
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Megalist sync done: {inserted} inserted/updated as new, {updated} merged into existing games")


if __name__ == "__main__":
    sync_megalist()
