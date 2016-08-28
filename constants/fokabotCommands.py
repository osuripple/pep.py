from objects import fokabot
import random
from objects import glob
from constants import serverPackets
from constants import exceptions
from helpers import userHelper
from helpers import systemHelper
import requests
import json
from constants import mods
from helpers import generalFunctions
from helpers import logHelper as log
from constants import gameModes
from constants import privileges

"""
Commands callbacks

Must have fro, chan and messages as arguments
fro -- name of who triggered the command
chan -- channel where the message was sent
message -- 	list containing arguments passed from the message
			[0] = first argument
			[1] = second argument
			. . .

return the message or **False** if there's no response by the bot
"""

def instantRestart(fro, chan, message):
	glob.tokens.enqueueAll(serverPackets.notification("We are restarting Bancho. Be right back!"))
	systemHelper.scheduleShutdown(0, True, delay=1)
	return False

def faq(fro, chan, message):
	if message[0] == "rules":
		return "Please make sure to check (Ripple's rules)[http://ripple.moe/?p=23]."
	elif message[0] == "swearing":
		return "Please don't abuse swearing"
	elif message[0] == "spam":
		return "Please don't spam"
	elif message[0] == "offend":
		return "Please don't offend other players"
	elif message[0] == "github":
		return "(Ripple's Github page!)[https://github.com/osuripple/ripple]"
	elif message[0] == "discord":
		return "(Join Ripple's Discord!)[https://discord.gg/0rJcZruIsA6rXuIx]"
	elif message[0] == "blog":
		return "You can find the latest Ripple news on the (blog)[https://ripple.moe/blog/]!"
	elif message[0] == "changelog":
		return "Check the (changelog)[https://ripple.moe/index.php?p=17] !"
	elif message[0] == "status":
		return "Check the server status (here!)[https://ripple.moe/index.php?p=27]"
	elif message[0] == "english":
		return "Please keep this channel in english."
	else:
		return False

def roll(fro, chan, message):
	maxPoints = 100
	if len(message) >= 1:
		if message[0].isdigit() == True and int(message[0]) > 0:
			maxPoints = int(message[0])

	points = random.randrange(0,maxPoints)
	return "{} rolls {} points!".format(fro, str(points))

#def ask(fro, chan, message):
#	return random.choice(["yes", "no", "maybe"])

def alert(fro, chan, message):
	glob.tokens.enqueueAll(serverPackets.notification(' '.join(message[:])))
	return False

def alertUser(fro, chan, message):
	target = message[0].replace("_", " ")

	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken != None:
		targetToken.enqueue(serverPackets.notification(' '.join(message[1:])))
		return False
	else:
		return "User offline."

def moderated(fro, chan, message):
	try:
		# Make sure we are in a channel and not PM
		if chan.startswith("#") == False:
			raise exceptions.moderatedPMException

		# Get on/off
		enable = True
		if len(message) >= 1:
			if message[0] == "off":
				enable = False

		# Turn on/off moderated mode
		glob.channels.channels[chan].moderated = enable
		return "This channel is {} in moderated mode!".format("now" if enable else "no longer")
	except exceptions.moderatedPMException:
		return "You are trying to put a private chat in moderated mode. Are you serious?!? You're fired."

def kickAll(fro, chan, message):
	# Kick everyone but mods/admins
	toKick = []
	for key, value in glob.tokens.tokens.items():
		if value.admin == False:
			toKick.append(key)

	# Loop though users to kick (we can't change dictionary size while iterating)
	for i in toKick:
		if i in glob.tokens.tokens:
			glob.tokens.tokens[i].kick()

	return "Whoops! Rip everyone."

def kick(fro, chan, message):
	# Get parameters
	target = message[0].replace("_", " ")

	# Get target token and make sure is connected
	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken == None:
		return "{} is not online".format(target)

	# Kick user
	targetToken.kick()

	# Bot response
	return "{} has been kicked from the server.".format(target)

def fokabotReconnect(fro, chan, message):
	# Check if fokabot is already connected
	if glob.tokens.getTokenFromUserID(999) != None:
		return "Fokabot is already connected to Bancho"

	# Fokabot is not connected, connect it
	fokabot.connect()
	return False

def silence(fro, chan, message):
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")
	amount = message[1]
	unit = message[2]
	reason = ' '.join(message[3:])

	# Get target user ID
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)

	# Make sure the user exists
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Calculate silence seconds
	if unit == 's':
		silenceTime = int(amount)
	elif unit == 'm':
		silenceTime = int(amount)*60
	elif unit == 'h':
		silenceTime = int(amount)*3600
	elif unit == 'd':
		silenceTime = int(amount)*86400
	else:
		return "Invalid time unit (s/m/h/d)."

	# Max silence time is 7 days
	if silenceTime > 604800:
		return "Invalid silence time. Max silence time is 7 days."

	# Send silence packet to target if he's connected
	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken != None:
		# user online, silence both in db and with packet
		targetToken.silence(silenceTime, reason, userID)
	else:
		# User offline, silence user only in db
		userHelper.silence(targetUserID, silenceTime, reason, userID)

	# Log message
	msg = "{} has been silenced for the following reason: {}".format(target, reason)
	return msg

def removeSilence(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")

	# Make sure the user exists
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Send new silence end packet to user if he's online
	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken != None:
		# User online, remove silence both in db and with packet
		targetToken.silence(0, "", userID)
	else:
		# user offline, remove islene ofnlt from db
		userHelper.silence(targetUserID, 0, "", userID)

	return "{}'s silence reset".format(target)

def ban(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")

	# Make sure the user exists
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Set allowed to 0
	userHelper.ban(targetUserID)

	# Send ban packet to the user if he's online
	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken != None:
		targetToken.enqueue(serverPackets.loginBanned())

	log.rap(userID, "has banned {}".format(target), True)
	return "RIP {}. You will not be missed.".format(target)

def unban(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")

	# Make sure the user exists
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Set allowed to 1
	userHelper.unban(targetUserID)

	log.rap(userID, "has unbanned {}".format(target), True)
	return "Welcome back {}!".format(target)

def restrict(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")

	# Make sure the user exists
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Put this user in restricted mode
	userHelper.restrict(targetUserID)

	# Send restricted mode packet to this user if he's online
	targetToken = glob.tokens.getTokenFromUsername(target)
	if targetToken != None:
		targetToken.setRestricted()

	log.rap(userID, "has put {} in restricted mode".format(target), True)
	return "Bye bye {}. See you later, maybe.".format(target)

def unrestrict(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0].replace("_", " ")

	# Make sure the user exists
	targetUserID = userHelper.getID(target)
	userID = userHelper.getID(fro)
	if targetUserID == False:
		return "{}: user not found".format(target)

	# Set allowed to 1
	userHelper.unrestrict(targetUserID)

	log.rap(userID, "has removed restricted mode from {}".format(target), True)
	return "Welcome back {}!".format(target)

def restartShutdown(restart):
	"""Restart (if restart = True) or shutdown (if restart = False) pep.py safely"""
	msg = "We are performing some maintenance. Bancho will {} in 5 seconds. Thank you for your patience.".format("restart" if restart else "shutdown")
	systemHelper.scheduleShutdown(5, restart, msg)
	return msg

def systemRestart(fro, chan, message):
	return restartShutdown(True)

def systemShutdown(fro, chan, message):
	return restartShutdown(False)

def systemReload(fro, chan, message):
	# Reload settings from bancho_settings
	glob.banchoConf.loadSettings()

	# Reload channels too
	glob.channels.loadChannels()

	# And chat filters
	glob.chatFilters.loadFilters()

	# Send new channels and new bottom icon to everyone
	glob.tokens.enqueueAll(serverPackets.mainMenuIcon(glob.banchoConf.config["menuIcon"]))
	glob.tokens.enqueueAll(serverPackets.channelInfoEnd())
	for key, value in glob.channels.channels.items():
		if value.publicRead == True and value.hidden == False:
			glob.tokens.enqueueAll(serverPackets.channelInfo(key))

	return "Bancho settings reloaded!"

def systemMaintenance(fro, chan, message):
	# Turn on/off bancho maintenance
	maintenance = True

	# Get on/off
	if len(message) >= 2:
		if message[1] == "off":
			maintenance = False

	# Set new maintenance value in bancho_settings table
	glob.banchoConf.setMaintenance(maintenance)

	if maintenance == True:
		# We have turned on maintenance mode
		# Users that will be disconnected
		who = []

		# Disconnect everyone but mod/admins
		for _, value in glob.tokens.tokens.items():
			if value.admin == False:
				who.append(value.userID)

		glob.tokens.enqueueAll(serverPackets.notification("Our bancho server is in maintenance mode. Please try to login again later."))
		glob.tokens.multipleEnqueue(serverPackets.loginError(), who)
		msg = "The server is now in maintenance mode!"
	else:
		# We have turned off maintenance mode
		# Send message if we have turned off maintenance mode
		msg = "The server is no longer in maintenance mode!"

	# Chat output
	return msg

def systemStatus(fro, chan, message):
	# Print some server info
	data = systemHelper.getSystemInfo()

	# Final message
	msg = "pep.py bancho server v{}\n".format(glob.VERSION)
	msg += "made by the Ripple team\n"
	msg += "\n"
	msg += "=== BANCHO STATS ===\n"
	msg += "Connected users: {}\n".format(data["connectedUsers"])
	msg += "Multiplayer matches: {}\n".format(data["matches"])
	msg += "Uptime: {}\n".format(data["uptime"])
	msg += "\n"
	msg += "=== SYSTEM STATS ===\n"
	msg += "CPU: {}%\n".format(data["cpuUsage"])
	msg += "RAM: {}GB/{}GB\n".format(data["usedMemory"], data["totalMemory"])
	if data["unix"] == True:
		msg += "Load average: {}/{}/{}\n".format(data["loadAverage"][0], data["loadAverage"][1], data["loadAverage"][2])

	return msg


def getPPMessage(userID, just_data = False):
	try:
		# Get user token
		token = glob.tokens.getTokenFromUserID(userID)
		if token == None:
			return False

		currentMap = token.tillerino[0]
		currentMods = token.tillerino[1]
		currentAcc = token.tillerino[2]

		# Send request to LETS api
		resp = requests.get("http://127.0.0.1:5002/api/v1/pp?b={}&m={}&a={}".format(currentMap, currentMods, currentAcc), timeout=10).text
		data = json.loads(resp)

		# Make sure status is in response data
		if "status" not in data:
			raise exceptions.apiException

		# Make sure status is 200
		if data["status"] != 200:
			if "message" in data:
				return "Error in LETS API call ({}). Please tell this to a dev.".format(data["message"])
			else:
				raise exceptions.apiException

		if just_data:
			return data

		# Return response in chat
		# Song name and mods
		msg = "{song}{plus}{mods}  ".format(song=data["song_name"], plus="+" if currentMods > 0 else "", mods=generalFunctions.readableMods(currentMods))

		# PP values
		if currentAcc == -1:
			msg += "95%: {pp95}pp | 98%: {pp98}pp | 99% {pp99}pp | 100%: {pp100}pp".format(pp100=data["pp"][0], pp99=data["pp"][1], pp98=data["pp"][2], pp95=data["pp"][3])
		else:
			msg += "{acc:.2f}%: {pp}pp".format(acc=token.tillerino[2], pp=data["pp"][0])

		originalAR = data["ar"]
		# calc new AR if HR/EZ is on
		if (currentMods & mods.Easy) > 0:
			data["ar"] = max(0, data["ar"] / 2)
		if (currentMods & mods.HardRock) > 0:
			data["ar"] = min(10, data["ar"] * 1.4)

		arstr = " ({})".format(originalAR) if originalAR != data["ar"] else ""

		# Beatmap info
		msg += " | {bpm} BPM | AR {ar}{arstr} | {stars:.2f} stars".format(bpm=data["bpm"], stars=data["stars"], ar=data["ar"], arstr=arstr)

		# Return final message
		return msg
	except requests.exceptions.RequestException:
		# RequestException
		return "API Timeout. Please try again in a few seconds."
	except exceptions.apiException:
		# API error
		return "Unknown error in LETS API call. Please tell this to a dev."
	except:
		# Unknown exception
		# TODO: print exception
		return False

def tillerinoNp(fro, chan, message):
	try:
		# Run the command in PM only
		if chan.startswith("#"):
			return False

		playWatch = message[1] == "playing" or message[1] == "watching"
		# Get URL from message
		if message[1] == "listening":
			beatmapURL = str(message[3][1:])
		elif playWatch:
			beatmapURL = str(message[2][1:])
		else:
			return False

		modsEnum = 0
		mapping = {
			"-Easy": mods.Easy,
			"-NoFail": mods.NoFail,
			"+Hidden": mods.Hidden,
			"+HardRock": mods.HardRock,
			"+Nightcore": mods.Nightcore,
			"+DoubleTime": mods.DoubleTime,
			"-HalfTime": mods.HalfTime,
			"+Flashlight": mods.Flashlight,
			"-SpunOut": mods.SpunOut
		}

		if playWatch:
			for part in message:
				part = part.replace("\x01", "")
				if part in mapping.keys():
					modsEnum += mapping[part]

		# Get beatmap id from URL
		beatmapID = fokabot.npRegex.search(beatmapURL).groups(0)[0]

		# Update latest tillerino song for current token
		token = glob.tokens.getTokenFromUsername(fro)
		if token != None:
			token.tillerino = [int(beatmapID), modsEnum, -1.0]
		userID = token.userID

		# Return tillerino message
		return getPPMessage(userID)
	except:
		return False


def tillerinoMods(fro, chan, message):
	try:
		# Run the command in PM only
		if chan.startswith("#"):
			return False

		# Get token and user ID
		token = glob.tokens.getTokenFromUsername(fro)
		if token == None:
			return False
		userID = token.userID

		# Make sure the user has triggered the bot with /np command
		if token.tillerino[0] == 0:
			return "Please give me a beatmap first with /np command."

		# Check passed mods and convert to enum
		modsList = [message[0][i:i+2].upper() for i in range(0, len(message[0]), 2)]
		modsEnum = 0
		for i in modsList:
			if i not in ["NO", "NF", "EZ", "HD", "HR", "DT", "HT", "NC", "FL", "SO"]:
				return "Invalid mods. Allowed mods: NO, NF, EZ, HD, HR, DT, HT, NC, FL, SO. Do not use spaces for multiple mods."
			if i == "NO":
				modsEnum = 0
				break
			elif i == "NF":
				modsEnum += mods.NoFail
			elif i == "EZ":
				modsEnum += mods.Easy
			elif i == "HD":
				modsEnum += mods.Hidden
			elif i == "HR":
				modsEnum += mods.HardRock
			elif i == "DT":
				modsEnum += mods.DoubleTime
			elif i == "HT":
				modsEnum += mods.HalfTime
			elif i == "NC":
				modsEnum += mods.Nightcore
			elif i == "FL":
				modsEnum += mods.Flashlight
			elif i == "SO":
				modsEnum += mods.SpunOut

		# Set mods
		token.tillerino[1] = modsEnum

		# Return tillerino message for that beatmap with mods
		return getPPMessage(userID)
	except:
		return False

def tillerinoAcc(fro, chan, message):
	try:
		# Run the command in PM only
		if chan.startswith("#"):
			return False

		# Get token and user ID
		token = glob.tokens.getTokenFromUsername(fro)
		if token == None:
			return False
		userID = token.userID

		# Make sure the user has triggered the bot with /np command
		if token.tillerino[0] == 0:
			return "Please give me a beatmap first with /np command."

		# Convert acc to float
		acc = float(message[0])

		# Set new tillerino list acc value
		token.tillerino[2] = acc

		# Return tillerino message for that beatmap with mods
		return getPPMessage(userID)
	except ValueError:
		return "Invalid acc value"
	except:
		return False

def tillerinoLast(fro, chan, message):
	try:
		data = glob.db.fetch("""SELECT beatmaps.song_name as sn, scores.*,
			beatmaps.beatmap_id as bid, beatmaps.difficulty_std, beatmaps.difficulty_taiko, beatmaps.difficulty_ctb, beatmaps.difficulty_mania, beatmaps.max_combo as fc
		FROM scores
		LEFT JOIN beatmaps ON beatmaps.beatmap_md5=scores.beatmap_md5
		LEFT JOIN users ON users.id = scores.userid
		WHERE users.username = %s
		ORDER BY scores.time DESC
		LIMIT 1""", [fro])
		if data == None:
			return False

		diffString = "difficulty_{}".format(gameModes.getGameModeForDB(data["play_mode"]))
		rank = generalFunctions.getRank(data["play_mode"], data["mods"], data["accuracy"],\
			data["300_count"], data["100_count"], data["50_count"], data["misses_count"])

		ifPlayer = "{0} | ".format(fro) if chan != "FokaBot" else ""
		ifFc = " (FC)" if data["max_combo"] == data["fc"] else " {0}x/{1}x".format(data["max_combo"], data["fc"])
		beatmapLink = "[http://osu.ppy.sh/b/{1} {0}]".format(data["sn"], data["bid"])

		hasPP = data["play_mode"] == gameModes.std or data["play_mode"] == gameModes.mania

		msg = ifPlayer
		msg += beatmapLink
		if data["play_mode"] != gameModes.std:
			msg += " <{0}>".format(gameModes.getGameModeForPrinting(data["play_mode"]))

		if data["mods"]:
			msg += ' +' + generalFunctions.readableMods(data["mods"])

		if not hasPP:
			msg += " | {0:,}".format(data["score"])
			msg += ifFc
			msg += " | {0:.2f}%, {1}".format(data["accuracy"], rank.upper())
			msg += " {{ {0} / {1} / {2} / {3} }}".format(data["300_count"], data["100_count"], data["50_count"], data["misses_count"])
			msg += " | {0:.2f} stars".format(data[diffString])
			return msg

		msg += " ({0:.2f}%, {1})".format(data["accuracy"], rank.upper())
		msg += ifFc
		msg += " | {0:.2f}pp".format(data["pp"])

		stars = data[diffString]
		if data["mods"]:
			token = glob.tokens.getTokenFromUsername(fro)
			if token == None:
				return False
			userID = token.userID
			token.tillerino[0] = data["bid"]
			token.tillerino[1] = data["mods"]
			token.tillerino[2] = data["accuracy"]
			oppaiData = getPPMessage(userID, just_data=True)
			if "stars" in oppaiData:
				stars = oppaiData["stars"]

		msg += " | {0:.2f} stars".format(stars)
		return msg
	except Exception as a:
		log.error(a)
		return False

def mm00(fro, chan, message):
	random.seed()
	return random.choice(["meme", "MA MAURO ESISTE?"])

"""
Commands list

trigger: message that triggers the command
callback: function to call when the command is triggered. Optional.
response: text to return when the command is triggered. Optional.
syntax: command syntax. Arguments must be separated by spaces (eg: <arg1> <arg2>)
privileges: privileges needed to execute the command. Optional.

NOTES:
- You CAN'T use both rank and minRank at the same time.
- If both rank and minrank are **not** present, everyone will be able to run that command.
- You MUST set trigger and callback/response, or the command won't work.
"""
commands = [
	{
		"trigger": "!roll",
		"callback": roll
	}, {
		"trigger": "!faq",
		"syntax": "<name>",
		"callback": faq
	}, {
		"trigger": "!report",
		"response": "Report command isn't here yet :c"
	}, {
		"trigger": "!help",
		"response": "Click (here)[https://ripple.moe/index.php?p=16&id=4] for FokaBot's full command list"
	}, #{
		#"trigger": "!ask",
		#"syntax": "<question>",
		#"callback": ask
	#}, {
	{
		"trigger": "!mm00",
		"callback": mm00
	}, {
		"trigger": "!alert",
		"syntax": "<message>",
		"privileges": privileges.ADMIN_SEND_ALERTS,
		"callback": alert
	}, {
		"trigger": "!alertuser",
		"syntax": "<username> <message>",
		"privileges": privileges.ADMIN_SEND_ALERTS,
		"callback": alertUser,
	}, {
		"trigger": "!moderated",
		"privileges": privileges.ADMIN_CHAT_MOD,
		"callback": moderated
	}, {
		"trigger": "!kickall",
		"privileges": privileges.ADMIN_KICK_USERS,
		"callback": kickAll
	}, {
		"trigger": "!kick",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_KICK_USERS,
		"callback": kick
	}, {
		"trigger": "!fokabot reconnect",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": fokabotReconnect
	}, {
		"trigger": "!silence",
		"syntax": "<target> <amount> <unit(s/m/h/d)> <reason>",
		"privileges": privileges.ADMIN_SILENCE_USERS,
		"callback": silence
	}, {
		"trigger": "!removesilence",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_SILENCE_USERS,
		"callback": removeSilence
	}, {
		"trigger": "!system restart",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": systemRestart
	}, {
		"trigger": "!system shutdown",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": systemShutdown
	}, {
		"trigger": "!system reload",
		"privileges": privileges.ADMIN_MANAGE_SETTINGS,
		"callback": systemReload
	}, {
		"trigger": "!system maintenance",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": systemMaintenance
	}, {
		"trigger": "!system status",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": systemStatus
	}, {
		"trigger": "!ban",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_BAN_USERS,
		"callback": ban
	}, {
		"trigger": "!unban",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_BAN_USERS,
		"callback": unban
	}, {
		"trigger": "!restrict",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_BAN_USERS,
		"callback": restrict
	}, {
		"trigger": "!unrestrict",
		"syntax": "<target>",
		"privileges": privileges.ADMIN_BAN_USERS,
		"callback": unrestrict
	}, {
		"trigger": "\x01ACTION is listening to",
		"callback": tillerinoNp
	}, {
		"trigger": "\x01ACTION is playing",
		"callback": tillerinoNp
	}, {
		"trigger": "\x01ACTION is watching",
		"callback": tillerinoNp
	}, {
		"trigger": "!with",
		"callback": tillerinoMods,
		"syntax": "<mods>"
	}, {
		"trigger": "!last",
		"callback": tillerinoLast
	}, {
		"trigger": "!ir",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"callback": instantRestart
	}
	#
	#	"trigger": "!acc",
	#	"callback": tillerinoAcc,
	#	"syntax": "<accuarcy>"
	#}
]

# Commands list default values
for cmd in commands:
	cmd.setdefault("syntax", "")
	cmd.setdefault("privileges", None)
	cmd.setdefault("callback", None)
	cmd.setdefault("response", "u w0t m8?")
