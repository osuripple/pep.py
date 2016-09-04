from constants import actions
from constants import gameModes
from helpers import userHelper
from constants import serverPackets
from events import logoutEvent
from helpers import logHelper as log
from objects import glob
import uuid
import time
import threading
from helpers import chatHelper as chat

class token:

	def __init__(self, userID, token_ = None, ip ="", irc = False, timeOffset = 0):
		"""
		Create a token object and set userID and token

		userID -- user associated to this token
		token -- 	if passed, set token to that value
					if not passed, token will be generated
		ip		--	client ip. optional.
		irc 	--	if True, set this token as IRC client. optional.
		timeOffset -- the time offset from UTC for this user. optional.
		"""
		# Set stuff
		self.userID = userID
		self.username = userHelper.getUsername(self.userID)
		self.privileges = userHelper.getPrivileges(self.userID)
		self.admin = userHelper.isInPrivilegeGroup(self.userID, "developer") or userHelper.isInPrivilegeGroup(self.userID, "community manager")
		self.irc = irc
		self.restricted = userHelper.isRestricted(self.userID)
		self.loginTime = int(time.time())
		self.pingTime = self.loginTime
		self.timeOffset = timeOffset
		self.lock = threading.Lock()	# Sync primitive

		# Default variables
		self.spectators = []
		self.spectating = 0
		self.location = [0,0]
		self.joinedChannels = []
		self.ip = ip
		self.country = 0
		self.location = [0,0]
		self.awayMessage = ""
		self.matchID = -1
		self.tillerino = [0,0,-1.0]	# beatmap, mods, acc
		self.silenceEndTime = 0
		self.queue = bytes()

		# Spam protection
		self.spamRate = 0

		# Stats cache
		self.actionID = actions.IDLE
		self.actionText = ""
		self.actionMd5 = ""
		self.actionMods = 0
		self.gameMode = gameModes.std
		self.rankedScore = 0
		self.accuracy = 0.0
		self.playcount = 0
		self.totalScore = 0
		self.gameRank = 0
		self.pp = 0

		# Generate/set token
		if token_ is not None:
			self.token = token_
		else:
			self.token = str(uuid.uuid4())

		# Set stats
		self.updateCachedStats()

		# If we have a valid ip, save bancho session in DB so we can cache LETS logins
		if ip != "":
			userHelper.saveBanchoSession(self.userID, self.ip)

	def enqueue(self, bytes_):
		"""
		Add bytes (packets) to queue

		bytes -- (packet) bytes to enqueue
		"""
		if not self.irc:
			self.queue += bytes_


	def resetQueue(self):
		"""Resets the queue. Call when enqueued packets have been sent"""
		self.queue = bytes()


	def joinChannel(self, channel):
		"""
		Add channel to joined channels list

		channel -- channel name
		"""
		if channel not in self.joinedChannels:
			self.joinedChannels.append(channel)

	def partChannel(self, channel):
		"""
		Remove channel from joined channels list

		channel -- channel name
		"""
		if channel in self.joinedChannels:
			self.joinedChannels.remove(channel)

	def setLocation(self, location):
		"""
		Set location (latitude and longitude)

		location -- [latitude, longitude]
		"""
		self.location = location

	def getLatitude(self):
		"""
		Get latitude

		return -- latitude
		"""
		return self.location[0]

	def getLongitude(self):
		"""
		Get longitude

		return -- longitude
		"""
		return self.location[1]

	def startSpectating(self, userID):
		"""
		Set the spectating user to userID

		userID -- target userID
		"""
		self.spectating = userID

	def stopSpectating(self):
		# Remove our userID from host's spectators
		target = self.spectating
		targetToken = glob.tokens.getTokenFromUserID(target)
		if targetToken is not None:
			# Remove us from host's spectators list
			targetToken.removeSpectator(self.userID)

			# Send the spectator left packet to host
			targetToken.enqueue(serverPackets.removeSpectator(self.userID))
			for c in targetToken.spectators:
				spec = glob.tokens.getTokenFromUserID(c)
				spec.enqueue(serverPackets.fellowSpectatorLeft(self.userID))

			# If nobody is spectating the host anymore, close #spectator channel
			if len(targetToken.spectators) == 0:
				chat.partChannel(token=targetToken, channel="#spect_{}".format(target), kick=True)

		# Part #spectator channel
		chat.partChannel(token=self, channel="#spect_{}".format(target), kick=True)

		# Set our spectating user to 0
		self.spectating = 0

		# Console output
		log.info("{} are no longer spectating {}".format(self.username, target))

	def partMatch(self):
		# Make sure we are in a match
		if self.matchID == -1:
			return

		# Part #multiplayer channel
		chat.partChannel(token=self, channel="#multi_{}".format(self.matchID), kick=True)

		# Make sure the match exists
		if self.matchID not in glob.matches.matches:
			return

		# The match exists, get object
		match = glob.matches.matches[self.matchID]

		# Set slot to free
		match.userLeft(self.userID)

		# Set usertoken match to -1
		self.matchID = -1

	def addSpectator(self, userID):
		"""
		Add userID to our spectators

		userID -- new spectator userID
		"""
		# Add userID to spectators if not already in
		if userID not in self.spectators:
			self.spectators.append(userID)

	def removeSpectator(self, userID):
		"""
		Remove userID from our spectators

		userID -- old spectator userID
		"""
		# Remove spectator
		if userID in self.spectators:
			self.spectators.remove(userID)

	def setCountry(self, countryID):
		"""
		Set country to countryID

		countryID -- numeric country ID. See countryHelper.py
		"""
		self.country = countryID

	def getCountry(self):
		"""
		Get numeric country ID

		return -- numeric country ID. See countryHelper.py
		"""
		return self.country

	def updatePingTime(self):
		"""Update latest ping time"""
		self.pingTime = int(time.time())

	def setAwayMessage(self, __awayMessage):
		"""Set a new away message"""
		self.awayMessage = __awayMessage

	def joinMatch(self, matchID):
		"""
		Set match to matchID

		matchID -- new match ID
		"""
		self.matchID = matchID

	def kick(self, message="You have been kicked from the server. Please login again."):
		"""
		Kick this user from the server
		
		message -- Notification message to send to this user. Optional.
		"""
		# Send packet to target
		log.info("{} has been disconnected. (kick)".format(self.username))
		if message != "":
			self.enqueue(serverPackets.notification(message))
		self.enqueue(serverPackets.loginFailed())

		# Logout event
		logoutEvent.handle(self, None)

	def silence(self, seconds, reason, author = 999):
		"""
		Silences this user (db, packet and token)

		seconds -- silence length in seconds
		reason -- silence reason
		author -- userID of who has silenced the target. Optional. Default: 999 (fokabot)
		"""
		# Silence in db and token
		self.silenceEndTime = int(time.time())+seconds
		userHelper.silence(self.userID, seconds, reason, author)

		# Send silence packet to target
		self.enqueue(serverPackets.silenceEndTime(seconds))

		# Send silenced packet to everyone else
		glob.tokens.enqueueAll(serverPackets.userSilenced(self.userID))

	def spamProtection(self, increaseSpamRate = True):
		"""
		Silences the user if is spamming.

		increaseSpamRate -- pass True if the user has sent a new message. Optional. Default: True
		"""
		# Increase the spam rate if needed
		if increaseSpamRate:
			self.spamRate += 1

		# Silence the user if needed
		if self.spamRate > 10:
			self.silence(1800, "Spamming (auto spam protection)")

	def isSilenced(self):
		"""
		Returns True if this user is silenced, otherwise False

		return -- True/False
		"""
		return self.silenceEndTime-int(time.time()) > 0

	def getSilenceSecondsLeft(self):
		"""
		Returns the seconds left for this user's silence
		(0 if user is not silenced)

		return -- silence seconds left
		"""
		return max(0, self.silenceEndTime-int(time.time()))

	def updateCachedStats(self):
		"""Update all cached stats for this token"""
		stats = userHelper.getUserStats(self.userID, self.gameMode)
		log.debug(str(stats))
		if stats is None:
			log.warning("Stats query returned None")
			return
		self.rankedScore = stats["rankedScore"]
		self.accuracy = stats["accuracy"]/100
		self.playcount = stats["playcount"]
		self.totalScore = stats["totalScore"]
		self.gameRank = stats["gameRank"]
		self.pp = stats["pp"]

	def checkRestricted(self, force=False):
		"""
		Check if this token is restricted. If so, send fokabot message

		force --	If True, get restricted value from db.
					If false, get the cached one. Optional. Default: False
		"""
		if force:
			self.restricted = userHelper.isRestricted(self.userID)
		if self.restricted:
			self.setRestricted()

	def setRestricted(self):
		"""
		Set this token as restricted, send FokaBot message to user
		and send offline packet to everyone
		"""
		self.restricted = True
		chat.sendMessage("FokaBot",self.username, "Your account is currently in restricted mode. Please visit ripple's website for more information.")
