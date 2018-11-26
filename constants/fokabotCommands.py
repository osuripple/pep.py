import json
import random
import re
import threading

import requests
import time

from common import generalUtils
from common.constants import mods
from common.log import logUtils as log
from common.ripple import userUtils
from constants import exceptions, slotStatuses, matchModModes, matchTeams, matchTeamTypes, matchScoringTypes
from common.constants import gameModes
from common.constants import privileges
from constants import serverPackets
from helpers import systemHelper
from objects import fokabot
from objects import glob
from helpers import chatHelper as chat
from common.web import cheesegull


def bloodcatMessage(beatmapID):
	beatmap = glob.db.fetch("SELECT song_name, beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1", [beatmapID])
	if beatmap is None:
		return "Sorry, I'm not able to provide a download link for this map :("
	return "Download [https://bloodcat.com/osu/s/{} {}] from Bloodcat".format(
		beatmap["beatmapset_id"],
		beatmap["song_name"],
	)

"""
Commands callbacks

Must have fro, chan and messages as arguments
:param fro: username of who triggered the command
:param chan: channel"(or username, if PM) where the message was sent
:param message: list containing arguments passed from the message
				[0] = first argument
				[1] = second argument
				. . .

return the message or **False** if there's no response by the bot
TODO: Change False to None, because False doesn't make any sense
"""
def instantRestart(fro, chan, message):
	glob.streams.broadcast("main", serverPackets.notification("We are restarting Bancho. Be right back!"))
	systemHelper.scheduleShutdown(0, True, delay=5)
	return False

def faq(fro, chan, message):
	# TODO: Unhardcode this
	messages = {
		"rules": "Please make sure to check (Ripple's rules)[https://ripple.moe/doc/rules].",
		"swearing": "Please don't abuse swearing",
		"spam": "Please don't spam",
		"offend": "Please don't offend other players",
		"github": "(Ripple's Github page!)[https://github.com/osuripple/ripple]",
		"discord": "(Join Ripple's Discord!)[https://discord.gg/0rJcZruIsA6rXuIx]",
		"blog": "You can find the latest Ripple news on the (blog)[https://blog.ripple.moe]!",
		"changelog": "Check the (changelog)[https://ripple.moe/changelog] !",
		"status": "Check the server status (here!)[https://status.ripple.moe]",
		"english": "Please keep this channel in english.",
		"topic": "Can you please drop the topic and talk about something else?",
		"lines": "Please try to keep your sentences on a single line to avoid getting silenced."
	}
	key = message[0].lower()
	if key not in messages:
		return False
	return messages[key]

def roll(fro, chan, message):
	maxPoints = 100
	if len(message) >= 1:
		if message[0].isdigit() and int(message[0]) > 0:
			maxPoints = int(message[0])

	points = random.randrange(0,maxPoints)
	return "{} rolls {} points!".format(fro, str(points))

#def ask(fro, chan, message):
#	return random.choice(["yes", "no", "maybe"])

def alert(fro, chan, message):
	msg = ' '.join(message[:]).strip()
	if not msg:
		return False
	glob.streams.broadcast("main", serverPackets.notification(msg))
	return False

def alertUser(fro, chan, message):
	target = message[0].lower()
	targetToken = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
	if targetToken is not None:
		msg = ' '.join(message[1:]).strip()
		if not msg:
			return False
		targetToken.enqueue(serverPackets.notification(msg))
		return False
	else:
		return "User offline."

def moderated(fro, chan, message):
	try:
		# Make sure we are in a channel and not PM
		if not chan.startswith("#"):
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
	with glob.tokens:
		for key, value in glob.tokens.tokens.items():
			if not value.admin:
				toKick.append(key)

	# Loop though users to kick (we can't change dictionary size while iterating)
	for i in toKick:
		if i in glob.tokens.tokens:
			glob.tokens.tokens[i].kick()

	return "Whoops! Rip everyone."

def kick(fro, chan, message):
	# Get parameters
	target = message[0].lower()
	if target == "fokabot":
		return "Nope."

	# Get target token and make sure is connected
	tokens = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True, _all=True)
	if len(tokens) == 0:
		return "{} is not online".format(target)

	# Kick users
	for i in tokens:
		i.kick()

	# Bot response
	return "{} has been kicked from the server.".format(target)

def fokabotReconnect(fro, chan, message):
	# Check if fokabot is already connected
	if glob.tokens.getTokenFromUserID(999) is not None:
		return "Fokabot is already connected to Bancho"

	# Fokabot is not connected, connect it
	fokabot.connect()
	return False

def silence(fro, chan, message):
	message = [x.lower() for x in message]
	target = message[0]
	amount = message[1]
	unit = message[2]
	reason = ' '.join(message[3:]).strip()
	if not reason:
		return "Please provide a valid reason."
	if not amount.isdigit():
		return "The amount must be a number."

	# Get target user ID
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)

	# Make sure the user exists
	if not targetUserID:
		return "{}: user not found".format(target)

	# Calculate silence seconds
	if unit == 's':
		silenceTime = int(amount)
	elif unit == 'm':
		silenceTime = int(amount) * 60
	elif unit == 'h':
		silenceTime = int(amount) * 3600
	elif unit == 'd':
		silenceTime = int(amount) * 86400
	else:
		return "Invalid time unit (s/m/h/d)."

	# Max silence time is 7 days
	if silenceTime > 604800:
		return "Invalid silence time. Max silence time is 7 days."

	# Send silence packet to target if he's connected
	targetToken = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
	if targetToken is not None:
		# user online, silence both in db and with packet
		targetToken.silence(silenceTime, reason, userID)
	else:
		# User offline, silence user only in db
		userUtils.silence(targetUserID, silenceTime, reason, userID)

	# Log message
	msg = "{} has been silenced for the following reason: {}".format(target, reason)
	return msg

def removeSilence(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0]

	# Make sure the user exists
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)
	if not targetUserID:
		return "{}: user not found".format(target)

	# Send new silence end packet to user if he's online
	targetToken = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
	if targetToken is not None:
		# User online, remove silence both in db and with packet
		targetToken.silence(0, "", userID)
	else:
		# user offline, remove islene ofnlt from db
		userUtils.silence(targetUserID, 0, "", userID)

	return "{}'s silence reset".format(target)

def ban(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0]

	# Make sure the user exists
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)
	if not targetUserID:
		return "{}: user not found".format(target)

	# Set allowed to 0
	userUtils.ban(targetUserID)

	# Send ban packet to the user if he's online
	targetToken = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
	if targetToken is not None:
		targetToken.enqueue(serverPackets.loginBanned())

	log.rap(userID, "has banned {}".format(target), True)
	return "RIP {}. You will not be missed.".format(target)

def unban(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0]

	# Make sure the user exists
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)
	if not targetUserID:
		return "{}: user not found".format(target)

	# Set allowed to 1
	userUtils.unban(targetUserID)

	log.rap(userID, "has unbanned {}".format(target), True)
	return "Welcome back {}!".format(target)

def restrict(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0]

	# Make sure the user exists
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)
	if not targetUserID:
		return "{}: user not found".format(target)

	# Put this user in restricted mode
	userUtils.restrict(targetUserID)

	# Send restricted mode packet to this user if he's online
	targetToken = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
	if targetToken is not None:
		targetToken.setRestricted()

	log.rap(userID, "has put {} in restricted mode".format(target), True)
	return "Bye bye {}. See you later, maybe.".format(target)

def unrestrict(fro, chan, message):
	# Get parameters
	for i in message:
		i = i.lower()
	target = message[0]

	# Make sure the user exists
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)
	if not targetUserID:
		return "{}: user not found".format(target)

	# Set allowed to 1
	userUtils.unrestrict(targetUserID)

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
	glob.banchoConf.reload()
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

	if maintenance:
		# We have turned on maintenance mode
		# Users that will be disconnected
		who = []

		# Disconnect everyone but mod/admins
		with glob.tokens:
			for _, value in glob.tokens.tokens.items():
				if not value.admin:
					who.append(value.userID)

		glob.streams.broadcast("main", serverPackets.notification("Our bancho server is in maintenance mode. Please try to login again later."))
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
	letsVersion = glob.redis.get("lets:version")
	if letsVersion is None:
		letsVersion = "\_(xd)_/"
	else:
		letsVersion = letsVersion.decode("utf-8")
	msg = "pep.py bancho server v{}\n".format(glob.VERSION)
	msg += "LETS scores server v{}\n".format(letsVersion)
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
	if data["unix"]:
		msg += "Load average: {}/{}/{}\n".format(data["loadAverage"][0], data["loadAverage"][1], data["loadAverage"][2])

	return msg


def getPPMessage(userID, just_data = False):
	try:
		# Get user token
		token = glob.tokens.getTokenFromUserID(userID)
		if token is None:
			return False

		currentMap = token.tillerino[0]
		currentMods = token.tillerino[1]
		currentAcc = token.tillerino[2]

		# Send request to LETS api
		url = "{}/v1/pp?b={}&m={}".format(glob.conf.config["server"]["letsapiurl"].rstrip("/"), currentMap, currentMods)
		resp = requests.get(url, timeout=10)
		try:
			assert resp is not None
			data = json.loads(resp.text)
		except (json.JSONDecodeError, AssertionError):
			raise exceptions.apiException()

		# Make sure status is in response data
		if "status" not in data:
			raise exceptions.apiException()

		# Make sure status is 200
		if data["status"] != 200:
			if "message" in data:
				return "Error in LETS API call ({}).".format(data["message"])
			else:
				raise exceptions.apiException()

		if just_data:
			return data

		# Return response in chat
		# Song name and mods
		msg = "{song}{plus}{mods}  ".format(song=data["song_name"], plus="+" if currentMods > 0 else "", mods=generalUtils.readableMods(currentMods))

		# PP values
		if currentAcc == -1:
			msg += "95%: {pp95}pp | 98%: {pp98}pp | 99% {pp99}pp | 100%: {pp100}pp".format(pp100=data["pp"][0], pp99=data["pp"][1], pp98=data["pp"][2], pp95=data["pp"][3])
		else:
			msg += "{acc:.2f}%: {pp}pp".format(acc=token.tillerino[2], pp=data["pp"][0])
		
		originalAR = data["ar"]
		# calc new AR if HR/EZ is on
		if (currentMods & mods.EASY) > 0:
			data["ar"] = max(0, data["ar"] / 2)
		if (currentMods & mods.HARDROCK) > 0:
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
		return "Unknown error in LETS API call."
	#except:
		# Unknown exception
		# TODO: print exception
	#	return False

def tillerinoNp(fro, chan, message):
	try:
		# Bloodcat trigger for #spect_
		if chan.startswith("#spect_"):
			spectatorHostUserID = getSpectatorHostUserIDFromChannel(chan)
			spectatorHostToken = glob.tokens.getTokenFromUserID(spectatorHostUserID, ignoreIRC=True)
			if spectatorHostToken is None:
				return False
			return bloodcatMessage(spectatorHostToken.beatmapID)

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
			"-Easy": mods.EASY,
			"-NoFail": mods.NOFAIL,
			"+Hidden": mods.HIDDEN,
			"+HardRock": mods.HARDROCK,
			"+Nightcore": mods.NIGHTCORE,
			"+DoubleTime": mods.DOUBLETIME,
			"-HalfTime": mods.HALFTIME,
			"+Flashlight": mods.FLASHLIGHT,
			"-SpunOut": mods.SPUNOUT
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
		if token is not None:
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
		if token is None:
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
				modsEnum += mods.NOFAIL
			elif i == "EZ":
				modsEnum += mods.EASY
			elif i == "HD":
				modsEnum += mods.HIDDEN
			elif i == "HR":
				modsEnum += mods.HARDROCK
			elif i == "DT":
				modsEnum += mods.DOUBLETIME
			elif i == "HT":
				modsEnum += mods.HALFTIME
			elif i == "NC":
				modsEnum += mods.NIGHTCORE
			elif i == "FL":
				modsEnum += mods.FLASHLIGHT
			elif i == "SO":
				modsEnum += mods.SPUNOUT

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
		if token is None:
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
		# Run the command in PM only
		if chan.startswith("#"):
			return False

		data = glob.db.fetch("""SELECT beatmaps.song_name as sn, scores.*,
			beatmaps.beatmap_id as bid, beatmaps.difficulty_std, beatmaps.difficulty_taiko, beatmaps.difficulty_ctb, beatmaps.difficulty_mania, beatmaps.max_combo as fc
		FROM scores
		LEFT JOIN beatmaps ON beatmaps.beatmap_md5=scores.beatmap_md5
		LEFT JOIN users ON users.id = scores.userid
		WHERE users.username = %s
		ORDER BY scores.time DESC
		LIMIT 1""", [fro])
		if data is None:
			return False

		diffString = "difficulty_{}".format(gameModes.getGameModeForDB(data["play_mode"]))
		rank = generalUtils.getRank(data["play_mode"], data["mods"], data["accuracy"],
									data["300_count"], data["100_count"], data["50_count"], data["misses_count"])

		ifPlayer = "{0} | ".format(fro) if chan != "FokaBot" else ""
		ifFc = " (FC)" if data["max_combo"] == data["fc"] else " {0}x/{1}x".format(data["max_combo"], data["fc"])
		beatmapLink = "[http://osu.ppy.sh/b/{1} {0}]".format(data["sn"], data["bid"])

		hasPP = data["play_mode"] != gameModes.CTB

		msg = ifPlayer
		msg += beatmapLink
		if data["play_mode"] != gameModes.STD:
			msg += " <{0}>".format(gameModes.getGameModeForPrinting(data["play_mode"]))

		if data["mods"]:
			msg += ' +' + generalUtils.readableMods(data["mods"])

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
			if token is None:
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

def pp(fro, chan, message):
	if chan.startswith("#"):
		return False

	gameMode = None
	if len(message) >= 1:
		gm = {
			"standard": 0,
			"std": 0,
			"taiko": 1,
			"ctb": 2,
			"mania": 3
		}
		if message[0].lower() not in gm:
			return "What's that game mode? I've never heard of it :/"
		else:
			gameMode = gm[message[0].lower()]

	token = glob.tokens.getTokenFromUsername(fro)
	if token is None:
		return False
	if gameMode is None:
		gameMode = token.gameMode
	if gameMode == gameModes.TAIKO or gameMode == gameModes.CTB:
		return "PP for your current game mode is not supported yet."
	pp = userUtils.getPP(token.userID, gameMode)
	return "You have {:,} pp".format(pp)

def updateBeatmap(fro, chan, message):
	try:
		# Run the command in PM only
		if chan.startswith("#"):
			return False

		# Get token and user ID
		token = glob.tokens.getTokenFromUsername(fro)
		if token is None:
			return False

		# Make sure the user has triggered the bot with /np command
		if token.tillerino[0] == 0:
			return "Please give me a beatmap first with /np command."

		# Send the request to cheesegull
		ok, message = cheesegull.updateBeatmap(token.tillerino[0])
		if ok:
			return "An update request for that beatmap has been queued. Check back in a few minutes and the beatmap should be updated!"
		else:
			return "Error in beatmap mirror API request: {}".format(message)
	except:
		return False

def report(fro, chan, message):
	msg = ""
	try:
		# TODO: Rate limit
		# Regex on message
		reportRegex = re.compile("^(.+) \((.+)\)\:(?: )?(.+)?$")
		result = reportRegex.search(" ".join(message))

		# Make sure the message matches the regex
		if result is None:
			raise exceptions.invalidArgumentsException()

		# Get username, report reason and report info
		target, reason, additionalInfo = result.groups()
		target = chat.fixUsernameForBancho(target)

		# Make sure the target is not foka
		if target.lower() == "fokabot":
			raise exceptions.invalidUserException()

		# Make sure the user exists
		targetID = userUtils.getID(target)
		if targetID == 0:
			raise exceptions.userNotFoundException()

		# Make sure that the user has specified additional info if report reason is 'Other'
		if reason.lower() == "other" and additionalInfo is None:
			raise exceptions.missingReportInfoException()

		# Get the token if possible
		chatlog = ""
		token = glob.tokens.getTokenFromUsername(userUtils.safeUsername(target), safe=True)
		if token is not None:
			chatlog = token.getMessagesBufferString()

		# Everything is fine, submit report
		glob.db.execute("INSERT INTO reports (id, from_uid, to_uid, reason, chatlog, time) VALUES (NULL, %s, %s, %s, %s, %s)", [userUtils.getID(fro), targetID, "{reason} - ingame {info}".format(reason=reason, info="({})".format(additionalInfo) if additionalInfo is not None else ""), chatlog, int(time.time())])
		msg = "You've reported {target} for {reason}{info}. A Community Manager will check your report as soon as possible. Every !report message you may see in chat wasn't sent to anyone, so nobody in chat, but admins, know about your report. Thank you for reporting!".format(target=target, reason=reason, info="" if additionalInfo is None else " (" + additionalInfo + ")")
		adminMsg = "{user} has reported {target} for {reason} ({info})".format(user=fro, target=target, reason=reason, info=additionalInfo)

		# Log report in #admin and on discord
		chat.sendMessage("FokaBot", "#admin", adminMsg)
		log.warning(adminMsg, discord="cm")
	except exceptions.invalidUserException:
		msg = "Hello, FokaBot here! You can't report me. I won't forget what you've tried to do. Watch out."
	except exceptions.invalidArgumentsException:
		msg = "Invalid report command syntax. To report an user, click on it and select 'Report user'."
	except exceptions.userNotFoundException:
		msg = "The user you've tried to report doesn't exist."
	except exceptions.missingReportInfoException:
		msg = "Please specify the reason of your report."
	except:
		raise
	finally:
		if msg != "":
			token = glob.tokens.getTokenFromUsername(fro)
			if token is not None:
				if token.irc:
					chat.sendMessage("FokaBot", fro, msg)
				else:
					token.enqueue(serverPackets.notification(msg))
	return False

def getMatchIDFromChannel(chan):
	if not chan.lower().startswith("#multi_"):
		raise exceptions.wrongChannelException()
	parts = chan.lower().split("_")
	if len(parts) < 2 or not parts[1].isdigit():
		raise exceptions.wrongChannelException()
	matchID = int(parts[1])
	if matchID not in glob.matches.matches:
		raise exceptions.matchNotFoundException()
	return matchID

def getSpectatorHostUserIDFromChannel(chan):
	if not chan.lower().startswith("#spect_"):
		raise exceptions.wrongChannelException()
	parts = chan.lower().split("_")
	if len(parts) < 2 or not parts[1].isdigit():
		raise exceptions.wrongChannelException()
	userID = int(parts[1])
	return userID

def multiplayer(fro, chan, message):
	def mpMake():
		if len(message) < 2:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp make <name>")
		matchName = " ".join(message[1:]).strip()
		if not matchName:
			raise exceptions.invalidArgumentsException("Match name must not be empty!")
		matchID = glob.matches.createMatch(matchName, generalUtils.stringMd5(generalUtils.randomString(32)), 0, "Tournament", "", 0, -1, isTourney=True)
		glob.matches.matches[matchID].sendUpdates()
		return "Tourney match #{} created!".format(matchID)

	def mpJoin():
		if len(message) < 2 or not message[1].isdigit():
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp join <id>")
		matchID = int(message[1])
		userToken = glob.tokens.getTokenFromUsername(fro, ignoreIRC=True)
		if userToken is None:
			raise exceptions.invalidArgumentsException(
				"No game clients found for {}, can't join the match. "
			    "If you're a referee and you want to join the chat "
				"channel from IRC, use /join #multi_{} instead.".format(fro, matchID)
			)
		userToken.joinMatch(matchID)
		return "Attempting to join match #{}!".format(matchID)

	def mpClose():
		matchID = getMatchIDFromChannel(chan)
		glob.matches.disposeMatch(matchID)
		return "Multiplayer match #{} disposed successfully".format(matchID)

	def mpLock():
		matchID = getMatchIDFromChannel(chan)
		glob.matches.matches[matchID].isLocked = True
		return "This match has been locked"

	def mpUnlock():
		matchID = getMatchIDFromChannel(chan)
		glob.matches.matches[matchID].isLocked = False
		return "This match has been unlocked"

	def mpSize():
		if len(message) < 2 or not message[1].isdigit() or int(message[1]) < 2 or int(message[1]) > 16:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp size <slots(2-16)>")
		matchSize = int(message[1])
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.forceSize(matchSize)
		return "Match size changed to {}".format(matchSize)

	def mpMove():
		if len(message) < 3 or not message[2].isdigit() or int(message[2]) < 0 or int(message[2]) > 16:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp move <username> <slot>")
		username = message[1]
		newSlotID = int(message[2])
		userID = userUtils.getIDSafe(username)
		if userID is None:
			raise exceptions.userNotFoundException("No such user")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		success = _match.userChangeSlot(userID, newSlotID)
		if success:
			result = "Player {} moved to slot {}".format(username, newSlotID)
		else:
			result = "You can't use that slot: it's either already occupied by someone else or locked"
		return result

	def mpHost():
		if len(message) < 2:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp host <username>")
		username = message[1].strip()
		if not username:
			raise exceptions.invalidArgumentsException("Please provide a username")
		userID = userUtils.getIDSafe(username)
		if userID is None:
			raise exceptions.userNotFoundException("No such user")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		success = _match.setHost(userID)
		return "{} is now the host".format(username) if success else "Couldn't give host to {}".format(username)

	def mpClearHost():
		matchID = getMatchIDFromChannel(chan)
		glob.matches.matches[matchID].removeHost()
		return "Host has been removed from this match"

	def mpStart():
		def _start():
			matchID = getMatchIDFromChannel(chan)
			success = glob.matches.matches[matchID].start()
			if not success:
				chat.sendMessage("FokaBot", chan, "Couldn't start match. Make sure there are enough players and "
												  "teams are valid. The match has been unlocked.")
			else:
				chat.sendMessage("FokaBot", chan, "Have fun!")


		def _decreaseTimer(t):
			if t <= 0:
				_start()
			else:
				if t % 10 == 0 or t <= 5:
					chat.sendMessage("FokaBot", chan, "Match starts in {} seconds.".format(t))
				threading.Timer(1.00, _decreaseTimer, [t - 1]).start()

		if len(message) < 2 or not message[1].isdigit():
			startTime = 0
		else:
			startTime = int(message[1])

		force = False if len(message) < 3 else message[2].lower() == "force"
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]

		# Force everyone to ready
		someoneNotReady = False
		for i, slot in enumerate(_match.slots):
			if slot.status != slotStatuses.READY and slot.user is not None:
				someoneNotReady = True
				if force:
					_match.toggleSlotReady(i)

		if someoneNotReady and not force:
			return "Some users aren't ready yet. Use '!mp start force' if you want to start the match, " \
				   "even with non-ready players."

		if startTime == 0:
			_start()
			return "Starting match"
		else:
			_match.isStarting = True
			threading.Timer(1.00, _decreaseTimer, [startTime - 1]).start()
			return "Match starts in {} seconds. The match has been locked. " \
				   "Please don't leave the match during the countdown " \
				   "or you might receive a penalty.".format(startTime)

	def mpInvite():
		if len(message) < 2:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp invite <username>")
		username = message[1].strip()
		if not username:
			raise exceptions.invalidArgumentsException("Please provide a username")
		userID = userUtils.getIDSafe(username)
		if userID is None:
			raise exceptions.userNotFoundException("No such user")
		token = glob.tokens.getTokenFromUserID(userID, ignoreIRC=True)
		if token is None:
			raise exceptions.invalidUserException("That user is not connected to bancho right now.")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.invite(999, userID)
		token.enqueue(serverPackets.notification("Please accept the invite you've just received from FokaBot to "
												 "enter your tourney match."))
		return "An invite to this match has been sent to {}".format(username)

	def mpMap():
		if len(message) < 2 or not message[1].isdigit() or (len(message) == 3 and not message[2].isdigit()):
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp map <beatmapid> [<gamemode>]")
		beatmapID = int(message[1])
		gameMode = int(message[2]) if len(message) == 3 else 0
		if gameMode < 0 or gameMode > 3:
			raise exceptions.invalidArgumentsException("Gamemode must be 0, 1, 2 or 3")
		beatmapData = glob.db.fetch("SELECT * FROM beatmaps WHERE beatmap_id = %s LIMIT 1", [beatmapID])
		if beatmapData is None:
			raise exceptions.invalidArgumentsException("The beatmap you've selected couldn't be found in the database."
													   "If the beatmap id is valid, please load the scoreboard first in "
													   "order to cache it, then try again.")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.beatmapID = beatmapID
		_match.beatmapName = beatmapData["song_name"]
		_match.beatmapMD5 = beatmapData["beatmap_md5"]
		_match.gameMode = gameMode
		_match.resetReady()
		_match.sendUpdates()
		return "Match map has been updated"

	def mpSet():
		if len(message) < 2 or not message[1].isdigit() or \
				(len(message) >= 3 and not message[2].isdigit()) or \
				(len(message) >= 4 and not message[3].isdigit()):
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp set <teammode> [<scoremode>] [<size>]")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		matchTeamType = int(message[1])
		matchScoringType = int(message[2]) if len(message) >= 3 else _match.matchScoringType
		if not 0 <= matchTeamType <= 3:
			raise exceptions.invalidArgumentsException("Match team type must be between 0 and 3")
		if not 0 <= matchScoringType <= 3:
			raise exceptions.invalidArgumentsException("Match scoring type must be between 0 and 3")
		oldMatchTeamType = _match.matchTeamType
		_match.matchTeamType = matchTeamType
		_match.matchScoringType = matchScoringType
		if len(message) >= 4:
			_match.forceSize(int(message[3]))
		if _match.matchTeamType != oldMatchTeamType:
			_match.initializeTeams()
		if _match.matchTeamType == matchTeamTypes.TAG_COOP or _match.matchTeamType == matchTeamTypes.TAG_TEAM_VS:
			_match.matchModMode = matchModModes.NORMAL

		_match.sendUpdates()
		return "Match settings have been updated!"

	def mpAbort():
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.abort()
		return "Match aborted!"

	def mpKick():
		if len(message) < 2:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp kick <username>")
		username = message[1].strip()
		if not username:
			raise exceptions.invalidArgumentsException("Please provide a username")
		userID = userUtils.getIDSafe(username)
		if userID is None:
			raise exceptions.userNotFoundException("No such user")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		slotID = _match.getUserSlotID(userID)
		if slotID is None:
			raise exceptions.userNotFoundException("The specified user is not in this match")
		for i in range(0, 2):
			_match.toggleSlotLocked(slotID)
		return "{} has been kicked from the match.".format(username)

	def mpPassword():
		password = "" if len(message) < 2 or not message[1].strip() else message[1]
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.changePassword(password)
		return "Match password has been changed!"

	def mpRandomPassword():
		password = generalUtils.stringMd5(generalUtils.randomString(32))
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.changePassword(password)
		return "Match password has been changed to a random one"

	def mpMods():
		if len(message) < 2:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp <mod1> [<mod2>] ...")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		newMods = 0
		freeMod = False
		for _mod in message[1:]:
			if _mod.lower().strip() == "hd":
				newMods |= mods.HIDDEN
			elif _mod.lower().strip() == "hr":
				newMods |= mods.HARDROCK
			elif _mod.lower().strip() == "dt":
				newMods |= mods.DOUBLETIME
			elif _mod.lower().strip() == "fl":
				newMods |= mods.FLASHLIGHT
			elif _mod.lower().strip() == "fi":
				newMods |= mods.FADEIN
			elif _mod.lower().strip() == "ez":
				newMods |= mods.EASY
			if _mod.lower().strip() == "none":
				newMods = 0

			if _mod.lower().strip() == "freemod":
				freeMod = True

		_match.matchModMode = matchModModes.FREE_MOD if freeMod else matchModModes.NORMAL
		_match.resetReady()
		if _match.matchModMode == matchModModes.FREE_MOD:
			_match.resetMods()
		_match.changeMods(newMods)
		return "Match mods have been updated!"

	def mpTeam():
		if len(message) < 3:
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp team <username> <colour>")
		username = message[1].strip()
		if not username:
			raise exceptions.invalidArgumentsException("Please provide a username")
		colour = message[2].lower().strip()
		if colour not in ["red", "blue"]:
			raise exceptions.invalidArgumentsException("Team colour must be red or blue")
		userID = userUtils.getIDSafe(username)
		if userID is None:
			raise exceptions.userNotFoundException("No such user")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.changeTeam(userID, matchTeams.BLUE if colour == "blue" else matchTeams.RED)
		return "{} is now in {} team".format(username, colour)

	def mpSettings():
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		single = False if len(message) < 2 else message[1].strip().lower() == "single"
		msg = "PLAYERS IN THIS MATCH "
		if not single:
			msg += "(use !mp settings single for a single-line version):"
			msg += "\n"
		else:
			msg += ": "
		empty = True
		for slot in _match.slots:
			if slot.user is None:
				continue
			readableStatuses = {
				slotStatuses.READY: "ready",
				slotStatuses.NOT_READY: "not ready",
				slotStatuses.NO_MAP: "no map",
				slotStatuses.PLAYING: "playing",
			}
			if slot.status not in readableStatuses:
				readableStatus = "???"
			else:
				readableStatus = readableStatuses[slot.status]
			empty = False
			msg += "* [{team}] <{status}> ~ {username}{mods}{nl}".format(
				team="red" if slot.team == matchTeams.RED else "blue" if slot.team == matchTeams.BLUE else "!! no team !!",
				status=readableStatus,
				username=glob.tokens.tokens[slot.user].username,
				mods=" (+ {})".format(generalUtils.readableMods(slot.mods)) if slot.mods > 0 else "",
				nl=" | " if single else "\n"
			)
		if empty:
			msg += "Nobody.\n"
		msg = msg.rstrip(" | " if single else "\n")
		return msg

	def mpScoreV():
		if len(message) < 2 or message[1] not in ("1", "2"):
			raise exceptions.invalidArgumentsException("Wrong syntax: !mp scorev <1|2>")
		_match = glob.matches.matches[getMatchIDFromChannel(chan)]
		_match.matchScoringType = matchScoringTypes.SCORE_V2 if message[1] == "2" else matchScoringTypes.SCORE
		_match.sendUpdates()
		return "Match scoring type set to scorev{}".format(message[1])

	def mpHelp():
		return "Supported subcommands: !mp <{}>".format("|".join(k for k in subcommands.keys()))

	try:
		subcommands = {
			"make": mpMake,
			"close": mpClose,
			"join": mpJoin,
			"lock": mpLock,
			"unlock": mpUnlock,
			"size": mpSize,
			"move": mpMove,
			"host": mpHost,
			"clearhost": mpClearHost,
			"start": mpStart,
			"invite": mpInvite,
			"map": mpMap,
			"set": mpSet,
			"abort": mpAbort,
			"kick": mpKick,
			"password": mpPassword,
			"randompassword": mpRandomPassword,
			"mods": mpMods,
			"team": mpTeam,
			"settings": mpSettings,
            "scorev": mpScoreV,
			"help": mpHelp
		}
		requestedSubcommand = message[0].lower().strip()
		if requestedSubcommand not in subcommands:
			raise exceptions.invalidArgumentsException("Invalid subcommand")
		return subcommands[requestedSubcommand]()
	except (exceptions.invalidArgumentsException, exceptions.userNotFoundException, exceptions.invalidUserException) as e:
		return str(e)
	except exceptions.wrongChannelException:
		return "This command only works in multiplayer chat channels"
	except exceptions.matchNotFoundException:
		return "Match not found"
	except:
		raise

def switchServer(fro, chan, message):
	# Get target user ID
	target = message[0]
	newServer = message[1].strip()
	if not newServer:
		return "Invalid server IP"
	targetUserID = userUtils.getIDSafe(target)
	userID = userUtils.getID(fro)

	# Make sure the user exists
	if not targetUserID:
		return "{}: user not found".format(target)

	# Connect the user to the end server
	userToken = glob.tokens.getTokenFromUserID(userID, ignoreIRC=True, _all=False)
	userToken.enqueue(serverPackets.switchServer(newServer))

	# Disconnect the user from the origin server
	# userToken.kick()
	return "{} has been connected to {}".format(target, newServer)

def rtx(fro, chan, message):
	target = message[0]
	message = " ".join(message[1:]).strip()
	if not message:
		return "Invalid message"
	targetUserID = userUtils.getIDSafe(target)
	if not targetUserID:
		return "{}: user not found".format(target)
	userToken = glob.tokens.getTokenFromUserID(targetUserID, ignoreIRC=True, _all=False)
	userToken.enqueue(serverPackets.rtx(message))
	return ":ok_hand:"

def bloodcat(fro, chan, message):
	try:
		matchID = getMatchIDFromChannel(chan)
	except exceptions.wrongChannelException:
		matchID = None
	try:
		spectatorHostUserID = getSpectatorHostUserIDFromChannel(chan)
	except exceptions.wrongChannelException:
		spectatorHostUserID = None

	if matchID is not None:
		if matchID not in glob.matches.matches:
			return "This match doesn't seem to exist... Or does it...?"
		beatmapID = glob.matches.matches[matchID].beatmapID
	else:
		spectatorHostToken = glob.tokens.getTokenFromUserID(spectatorHostUserID, ignoreIRC=True)
		if spectatorHostToken is None:
			return "The spectator host is offline."
		beatmapID = spectatorHostToken.beatmapID
	return bloodcatMessage(beatmapID)


"""
Commands list

trigger: message that triggers the command
callback: function to call when the command is triggered. Optional.
response: text to return when the command is triggered. Optional.
syntax: command syntax. Arguments must be separated by spaces (eg: <arg1> <arg2>)
privileges: privileges needed to execute the command. Optional.
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
		"callback": report
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
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
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
	}, {
		"trigger": "!pp",
		"callback": pp
	}, {
		"trigger": "!update",
		"callback": updateBeatmap
	}, {
		"trigger": "!mp",
		"privileges": privileges.USER_TOURNAMENT_STAFF,
		"syntax": "<subcommand>",
		"callback": multiplayer
	}, {
		"trigger": "!switchserver",
		"privileges": privileges.ADMIN_MANAGE_SERVERS,
		"syntax": "<username> <server_address>",
		"callback": switchServer
	}, {
		"trigger": "!rtx",
		"privileges": privileges.ADMIN_MANAGE_USERS,
		"syntax": "<username> <message>",
		"callback": rtx
	}, {
		"trigger": "!bloodcat",
		"callback": bloodcat
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
