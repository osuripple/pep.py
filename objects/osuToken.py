import threading
import time
import uuid

from common.constants import gameModes, actions
from common.log import logUtils as log
from common.ripple import userUtils
from constants import serverPackets
from events import logoutEvent
from helpers import chatHelper as chat
from objects import glob


class token:

	def __init__(self, userID, token_ = None, ip ="", irc = False, timeOffset = 0, tournament = False):
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
		self.username = userUtils.getUsername(self.userID)
		self.privileges = userUtils.getPrivileges(self.userID)
		self.admin = userUtils.isInPrivilegeGroup(self.userID, "developer") or userUtils.isInPrivilegeGroup(self.userID, "community manager")
		self.irc = irc
		self.restricted = userUtils.isRestricted(self.userID)
		self.loginTime = int(time.time())
		self.pingTime = self.loginTime
		self.timeOffset = timeOffset
		self.lock = threading.Lock()	# Sync primitive
		self.streams = []
		self.tournament = tournament

		# Default variables
		self.spectators = []

		# TODO: Move those two vars to a class
		self.spectating = None
		self.spectatingUserID = 0	# we need this in case we the host gets DCed

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
		self.gameMode = gameModes.STD
		self.beatmapID = 0
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
			userUtils.saveBanchoSession(self.userID, self.ip)

		# Join main stream
		self.joinStream("main")

	def enqueue(self, bytes_):
		"""
		Add bytes (packets) to queue

		bytes -- (packet) bytes to enqueue
		"""
		if not self.irc:
			if len(bytes_) < 10 * 10 ** 6:
				self.queue += bytes_
			else:
				log.warning("{}'s packets buffer is above 10M!! Lost some data!".format(self.username))


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

	def startSpectating(self, host):
		"""
		Set the spectating user to userID

		user -- user object
		"""
		# Stop spectating old client
		self.stopSpectating()

		# Set new spectator host
		self.spectating = host.token
		self.spectatingUserID = host.userID

		# Add us to host's spectator list
		host.spectators.append(self.token)

		# Create and join spectator stream
		streamName = "spect/{}".format(host.userID)
		glob.streams.add(streamName)
		self.joinStream(streamName)
		host.joinStream(streamName)

		# Send spectator join packet to host
		host.enqueue(serverPackets.addSpectator(self.userID))

		# Create and join #spectator (#spect_userid) channel
		glob.channels.addTempChannel("#spect_{}".format(host.userID))
		chat.joinChannel(token=self, channel="#spect_{}".format(host.userID))
		if len(host.spectators) == 1:
			# First spectator, send #spectator join to host too
			chat.joinChannel(token=host, channel="#spect_{}".format(host.userID))

		# Send fellow spectator join to all clients
		glob.streams.broadcast(streamName, serverPackets.fellowSpectatorJoined(self.userID))

		# Get current spectators list
		for i in host.spectators:
			if i != self.token and i in glob.tokens.tokens:
				self.enqueue(serverPackets.fellowSpectatorJoined(glob.tokens.tokens[i].userID))

		# Log
		log.info("{} is spectating {}".format(self.username, userUtils.getUsername(host.username)))

	def stopSpectating(self):
		# Remove our userID from host's spectators
		if self.spectating is None:
			return
		if self.spectating in glob.tokens.tokens:
			hostToken = glob.tokens.tokens[self.spectating]
		else:
			hostToken = None
		streamName = "spect/{}".format(self.spectatingUserID)

		# Remove us from host's spectators list,
		# leave spectator stream
		# and end the spectator left packet to host
		self.leaveStream(streamName)
		if hostToken is not None:
			hostToken.spectators.remove(self.token)
			hostToken.enqueue(serverPackets.removeSpectator(self.userID))

			# and to all other spectators
			for i in hostToken.spectators:
				if i in glob.tokens.tokens:
					glob.tokens.tokens[i].enqueue(serverPackets.fellowSpectatorLeft(self.userID))

			# If nobody is spectating the host anymore, close #spectator channel
			# and remove host from spect stream too
			if len(hostToken.spectators) == 0:
				chat.partChannel(token=hostToken, channel="#spect_{}".format(hostToken.userID), kick=True)
				hostToken.leaveStream(streamName)

		# Part #spectator channel
		chat.partChannel(token=self, channel="#spect_{}".format(self.spectatingUserID), kick=True)

		# Console output
		log.info("{} is no longer spectating {}".format(self.username, self.spectatingUserID))

		# Set our spectating user to 0
		self.spectating = None
		self.spectatingUserID = 0

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
		Set match to matchID, join match stream and channel

		matchID -- new match ID
		"""
		# Make sure the match exists
		if matchID not in glob.matches.matches:
			return

		# Match exists, get object
		match = glob.matches.matches[matchID]

		# Stop spectating
		self.stopSpectating()

		# Leave other matches
		if self.matchID > -1 and self.matchID != matchID:
			self.leaveMatch()

		# Try to join match
		joined = match.userJoin(self)
		if not joined:
			self.enqueue(serverPackets.matchJoinFail())
			return

		# Set matchID, join stream, channel and send packet
		self.matchID = matchID
		self.joinStream(match.streamName)
		chat.joinChannel(token=self, channel="#multi_{}".format(self.matchID))
		self.enqueue(serverPackets.matchJoinSuccess(matchID))

	def leaveMatch(self):
		"""
		Leave joined match, match stream and match channel

		:return:
		"""
		# Make sure we are in a match
		if self.matchID == -1:
			return

		# Part #multiplayer channel and streams (/ and /playing)
		chat.partChannel(token=self, channel="#multi_{}".format(self.matchID), kick=True)
		self.leaveStream("multi/{}".format(self.matchID))
		self.leaveStream("multi/{}/playing".format(self.matchID))	# optional

		# Make sure the match exists
		if self.matchID not in glob.matches.matches:
			return

		# The match exists, get object
		match = glob.matches.matches[self.matchID]

		# Set slot to free
		match.userLeft(self)

		# Set usertoken match to -1
		self.matchID = -1

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
		userUtils.silence(self.userID, seconds, reason, author)

		# Send silence packet to target
		self.enqueue(serverPackets.silenceEndTime(seconds))

		# Send silenced packet to everyone else
		glob.streams.broadcast("main", serverPackets.userSilenced(self.userID))

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
		stats = userUtils.getUserStats(self.userID, self.gameMode)
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
			self.restricted = userUtils.isRestricted(self.userID)
		if self.restricted:
			self.setRestricted()

	def setRestricted(self):
		"""
		Set this token as restricted, send FokaBot message to user
		and send offline packet to everyone
		"""
		self.restricted = True
		chat.sendMessage("FokaBot",self.username, "Your account is currently in restricted mode. Please visit ripple's website for more information.")

	def joinStream(self, name):
		glob.streams.join(name, token=self.token)
		if name not in self.streams:
			self.streams.append(name)

	def leaveStream(self, name):
		glob.streams.leave(name, token=self.token)
		if name in self.streams:
			self.streams.remove(name)

	def leaveAllStreams(self):
		for i in self.streams:
			self.leaveStream(i)