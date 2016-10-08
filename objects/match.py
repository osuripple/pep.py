import copy
import dill

from common import generalUtils
from common.constants import gameModes
from common.log import logUtils as log
from constants import dataTypes
from constants import matchModModes
from constants import matchScoringTypes
from constants import matchTeamTypes
from constants import matchTeams
from constants import serverPackets
from constants import slotStatuses
from helpers import chatHelper as chat
from objects import glob


class slot:
	def __init__(self):
		self.status = slotStatuses.free
		self.team = 0
		self.userID = -1
		self.user = None
		self.mods = 0
		self.loaded = False
		self.skip = False
		self.complete = False

class match:
	"""Multiplayer match object"""
	def __init__(self, matchID, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID):
		"""
		Create a new match object

		matchID -- match progressive identifier
		matchName -- match name, string
		matchPassword -- match md5 password. Leave empty for no password
		beatmapID -- beatmap ID
		beatmapName -- beatmap name, string
		beatmapMD5 -- beatmap md5 hash, string
		gameMode -- game mode ID. See gameModes.py
		hostUserID -- user id of the host
		"""
		self.matchID = matchID
		self.streamName = "multi/{}".format(self.matchID)
		self.playingStreamName = "{}/playing".format(self.streamName)
		self.inProgress = False
		self.mods = 0
		self.matchName = matchName
		self.matchPassword = matchPassword
		# NOTE: Password used to be md5-hashed, but the client doesn't like that.
		# So we're back to plain text passwords, like in normal osu!
		#if matchPassword != "":
		#	self.matchPassword = generalUtils.stringMd5(matchPassword)
		#else:
		#	self.matchPassword = ""
		self.beatmapID = beatmapID
		self.beatmapName = beatmapName
		self.beatmapMD5 = beatmapMD5
		self.hostUserID = hostUserID
		self.gameMode = gameMode
		self.matchScoringType = matchScoringTypes.score	# default values
		self.matchTeamType = matchTeamTypes.headToHead		# default value
		self.matchModMode = matchModModes.normal			# default value
		self.seed = 0
		self.matchDataCache = bytes()

		# Create all slots and reset them
		self.slots = []
		for _ in range(0,16):
			self.slots.append(slot())

		# Create streams
		glob.streams.add(self.streamName)
		glob.streams.add(self.playingStreamName)

		# Create #multiplayer channel
		glob.channels.addTempChannel("#multi_{}".format(self.matchID))

	def getMatchData(self):
		"""
		Return binary match data structure for packetHelper
		"""
		# General match info
		safeMatch = copy.deepcopy(self)
		struct = [
			[safeMatch.matchID, dataTypes.UINT16],
			[int(safeMatch.inProgress), dataTypes.BYTE],
			[0, dataTypes.BYTE],
			[safeMatch.mods, dataTypes.UINT32],
			[safeMatch.matchName, dataTypes.STRING],
			[safeMatch.matchPassword, dataTypes.STRING],
			[safeMatch.beatmapName, dataTypes.STRING],
			[safeMatch.beatmapID, dataTypes.UINT32],
			[safeMatch.beatmapMD5, dataTypes.STRING],
		]

		# Slots status IDs, always 16 elements
		for i in range(0,16):
			struct.append([safeMatch.slots[i].status, dataTypes.BYTE])

		# Slot teams, always 16 elements
		for i in range(0,16):
			struct.append([safeMatch.slots[i].team, dataTypes.BYTE])

		# Slot user ID. Write only if slot is occupied
		for i in range(0,16):
			if safeMatch.slots[i].user is not None and safeMatch.slots[i].user in glob.tokens.tokens:
				struct.append([glob.tokens.tokens[safeMatch.slots[i].user].userID, dataTypes.UINT32])

		# Other match data
		struct.extend([
			[safeMatch.hostUserID, dataTypes.SINT32],
			[safeMatch.gameMode, dataTypes.BYTE],
			[safeMatch.matchScoringType, dataTypes.BYTE],
			[safeMatch.matchTeamType, dataTypes.BYTE],
			[safeMatch.matchModMode, dataTypes.BYTE],
		])

		# Slot mods if free mod is enabled
		if safeMatch.matchModMode == matchModModes.freeMod:
			for i in range(0,16):
				struct.append([safeMatch.slots[i].mods, dataTypes.UINT32])

		# Seed idk
		struct.append([safeMatch.seed, dataTypes.UINT32])

		return struct

	def setHost(self, newHost):
		"""
		Set room host to newHost and send him host packet

		newHost -- new host userID
		"""
		slotID = self.getUserSlotID(newHost)
		if slotID is None or self.slots[slotID].user not in glob.tokens.tokens:
			return
		token = glob.tokens.tokens[self.slots[slotID].user]
		self.hostUserID = newHost
		token.enqueue(serverPackets.matchTransferHost())
		self.sendUpdates()
		log.info("MPROOM{}: {} is now the host".format(self.matchID, token.username))

	def setSlot(self, slotID, status = None, team = None, user = "", mods = None, loaded = None, skip = None, complete = None):
		#self.setSlot(i, slotStatuses.notReady, 0, user, 0)
		if status is not None:
			self.slots[slotID].status = status

		if team is not None:
			self.slots[slotID].team = team

		if user is not "":
			self.slots[slotID].user = user

		if mods is not None:
			self.slots[slotID].mods = mods

		if loaded is not None:
			self.slots[slotID].loaded = loaded

		if skip is not None:
			self.slots[slotID].skip = skip

		if complete is not None:
			self.slots[slotID].complete = complete

	def setSlotMods(self, slotID, mods):
		"""
		Set slotID mods. Same as calling setSlot and then sendUpdate

		slotID -- slot number
		mods -- new mods
		"""
		# Set new slot data and send update
		self.setSlot(slotID, mods=mods)
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} mods changed to {}".format(self.matchID, slotID, mods))

	def toggleSlotReady(self, slotID):
		"""
		Switch slotID ready/not ready status
		Same as calling setSlot and then sendUpdate

		slotID -- slot number
		"""
		# Update ready status and setnd update
		oldStatus = self.slots[slotID].status
		if oldStatus == slotStatuses.ready:
			newStatus = slotStatuses.notReady
		else:
			newStatus = slotStatuses.ready
		self.setSlot(slotID, newStatus)
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} changed ready status to {}".format(self.matchID, slotID, self.slots[slotID].status))

	def toggleSlotLock(self, slotID):
		"""
		Lock a slot
		Same as calling setSlot and then sendUpdate

		slotID -- slot number
		"""
		# Check if slot is already locked
		if self.slots[slotID].status == slotStatuses.locked:
			newStatus = slotStatuses.free
		else:
			newStatus = slotStatuses.locked

		# Send updated settings to kicked user, so he returns to lobby
		if self.slots[slotID].user is not None and self.slots[slotID].user in glob.tokens.tokens:
			glob.tokens.tokens[self.slots[slotID].user].enqueue(serverPackets.updateMatch(self.matchID))

		# Set new slot status
		self.setSlot(slotID, status=newStatus, team=0, user=None, mods=0)

		# Send updates to everyone else
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} {}".format(self.matchID, slotID, "locked" if newStatus == slotStatuses.locked else "unlocked"))

	def playerLoaded(self, userID):
		"""
		Set a player loaded status to True

		userID -- ID of user
		"""
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Set loaded to True
		self.slots[slotID].loaded = True
		log.info("MPROOM{}: User {} loaded".format(self.matchID, userID))

		# Check all loaded
		total = 0
		loaded = 0
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.playing:
				total+=1
				if self.slots[i].loaded:
					loaded+=1

		if total == loaded:
			self.allPlayersLoaded()

	def allPlayersLoaded(self):
		"""Send allPlayersLoaded packet to every playing usr in match"""
		glob.streams.broadcast(self.playingStreamName, serverPackets.allPlayersLoaded())
		log.info("MPROOM{}: All players loaded! Match starting...".format(self.matchID))

	def playerSkip(self, userID):
		"""
		Set a player skip status to True

		userID -- ID of user
		"""
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Set skip to True
		self.slots[slotID].skip = True
		log.info("MPROOM{}: User {} skipped".format(self.matchID, userID))

		# Send skip packet to every playing user
		#glob.streams.broadcast(self.playingStreamName, serverPackets.playerSkipped(glob.tokens.tokens[self.slots[slotID].user].userID))
		glob.streams.broadcast(self.playingStreamName, serverPackets.playerSkipped(slotID))

		# Check all skipped
		total = 0
		skipped = 0
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.playing:
				total+=1
				if self.slots[i].skip:
					skipped+=1

		if total == skipped:
			self.allPlayersSkipped()

	def allPlayersSkipped(self):
		"""Send allPlayersSkipped packet to every playing usr in match"""
		glob.streams.broadcast(self.playingStreamName, serverPackets.allPlayersSkipped())
		log.info("MPROOM{}: All players have skipped!".format(self.matchID))

	def playerCompleted(self, userID):
		"""
		Set userID's slot completed to True

		userID -- ID of user
		"""
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return
		self.setSlot(slotID, complete=True)

		# Console output
		log.info("MPROOM{}: User {} has completed his play".format(self.matchID, userID))

		# Check all completed
		total = 0
		completed = 0
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.playing:
				total+=1
				if self.slots[i].complete:
					completed+=1

		if total == completed:
			self.allPlayersCompleted()

	def allPlayersCompleted(self):
		"""Cleanup match stuff and send match end packet to everyone"""

		# Reset inProgress
		self.inProgress = False

		# Reset slots
		for i in range(0,16):
			if self.slots[i].user is not None and self.slots[i].status == slotStatuses.playing:
				self.slots[i].status = slotStatuses.notReady
				self.slots[i].loaded = False
				self.slots[i].skip = False
				self.slots[i].complete = False

		# Send match update
		self.sendUpdates()

		# Send match complete
		glob.streams.broadcast(self.streamName, serverPackets.matchComplete())

		# Destroy playing stream
		glob.streams.remove(self.playingStreamName)

		# Console output
		log.info("MPROOM{}: Match completed".format(self.matchID))

	def getUserSlotID(self, userID):
		"""
		Get slot ID occupied by userID

		return -- slot id if found, None if user is not in room
		"""
		for i in range(0,16):
			if self.slots[i].user is not None and self.slots[i].user in glob.tokens.tokens and glob.tokens.tokens[self.slots[i].user].userID == userID:
				return i
		return None

	def userJoin(self, user):
		"""
		Add someone to users in match

		userID -- user id of the user
		return -- True if join success, False if fail (room is full)
		"""

		# Make sure we're not in this match
		for i in range(0,16):
			if self.slots[i].user == user.token:
				# Set bugged slot to free
				self.setSlot(i, slotStatuses.free, 0, None, 0)

		# Find first free slot
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.free:
				# Occupy slot
				self.setSlot(i, slotStatuses.notReady, 0, user.token, 0)

				# Send updated match data
				self.sendUpdates()

				# Console output
				log.info("MPROOM{}: {} joined the room".format(self.matchID, user.username))
				return True

		return False

	def userLeft(self, user):
		"""
		Remove someone from users in match

		userID -- user if of the user
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(user.userID)
		if slotID is None:
			return

		# Set that slot to free
		self.setSlot(slotID, slotStatuses.free, 0, None, 0)

		# Check if everyone left
		if self.countUsers() == 0:
			# Dispose match
			glob.matches.disposeMatch(self.matchID)
			log.info("MPROOM{}: Room disposed".format(self.matchID))
			return

		# Check if host left
		if user.userID == self.hostUserID:
			# Give host to someone else
			for i in range(0,16):
				if self.slots[i].user is not None and self.slots[i].user in glob.tokens.tokens:
					self.setHost(glob.tokens.tokens[self.slots[i].user].userID)
					break

		# Send updated match data
		self.sendUpdates()

		# Console output
		log.info("MPROOM{}: {} left the room".format(self.matchID, user.username))

	def userChangeSlot(self, userID, newSlotID):
		"""
		Change userID slot to newSlotID

		userID -- user that changed slot
		newSlotID -- slot id of new slot
		"""
		# Make sure the user is in room
		oldSlotID = self.getUserSlotID(userID)
		if oldSlotID is None:
			return

		# Make sure there is no one inside new slot
		if self.slots[newSlotID].user is not None and self.slots[newSlotID].status != slotStatuses.free:
			return

		# Get old slot data
		#oldData = dill.copy(self.slots[oldSlotID])
		oldData = copy.deepcopy(self.slots[oldSlotID])

		# Free old slot
		self.setSlot(oldSlotID, slotStatuses.free, 0, None, 0, False, False, False)

		# Occupy new slot
		self.setSlot(newSlotID, oldData.status, oldData.team, oldData.user, oldData.mods)

		# Send updated match data
		self.sendUpdates()

		# Console output
		log.info("MPROOM{}: {} moved to slot {}".format(self.matchID, userID, newSlotID))

	def changePassword(self, newPassword):
		"""
		Change match password to newPassword

		newPassword -- new password string
		"""
		self.matchPassword = newPassword
		#if newPassword != "":
		#	self.matchPassword = generalUtils.stringMd5(newPassword)
		#else:
		#	self.matchPassword = ""

		# Send password change to every user in match
		glob.streams.broadcast(self.streamName, serverPackets.changeMatchPassword(self.matchPassword))

		# Send new match settings too
		self.sendUpdates()

		# Console output
		log.info("MPROOM{}: Password changed to {}".format(self.matchID, self.matchPassword))

	def changeMatchMods(self, mods):
		"""
		Set match global mods

		mods -- mods bitwise int thing
		"""
		# Set new mods and send update
		self.mods = mods
		self.sendUpdates()
		log.info("MPROOM{}: Mods changed to {}".format(self.matchID, self.mods))

	def userHasBeatmap(self, userID, has = True):
		"""
		Set no beatmap status for userID

		userID -- ID of user
		has -- True if has beatmap, false if not
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Set slot
		self.setSlot(slotID, slotStatuses.noMap if not has else slotStatuses.notReady)

		# Send updates
		self.sendUpdates()

	def transferHost(self, slotID):
		"""
		Transfer host to slotID

		slotID -- ID of slot
		"""
		# Make sure there is someone in that slot
		if self.slots[slotID].user is None or self.slots[slotID].user not in glob.tokens.tokens:
			return

		# Transfer host
		self.setHost(glob.tokens.tokens[self.slots[slotID].user].userID)

		# Send updates
		self.sendUpdates()

	def playerFailed(self, userID):
		"""
		Send userID's failed packet to everyone in match

		userID -- ID of user
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Send packet to everyone
		glob.streams.broadcast(self.playingStreamName, serverPackets.playerFailed(slotID))

		# Console output
		log.info("MPROOM{}: {} has failed!".format(self.matchID, userID))

	def invite(self, fro, to):
		"""
		Fro invites to in this match.

		fro -- sender userID
		to -- receiver userID
		"""

		# Get tokens
		froToken = glob.tokens.getTokenFromUserID(fro)
		toToken = glob.tokens.getTokenFromUserID(to)
		if froToken is None or toToken is None:
			return

		# FokaBot is too busy
		if to == 999:
			chat.sendMessage("FokaBot", froToken.username, "I would love to join your match, but I'm busy keeping ripple up and running. Sorry. Beep Boop.")

		# Send message
		message = "Come join my multiplayer match: \"[osump://{}/{} {}]\"".format(self.matchID, self.matchPassword.replace(" ", "_"), self.matchName)
		chat.sendMessage(token=froToken, to=toToken.username, message=message)

	def countUsers(self):
		"""
		Return how many players are in that match

		return -- number of users
		"""
		c = 0
		for i in range(0,16):
			if self.slots[i].user is not None:
				c+=1
		return c

	def changeTeam(self, userID):
		"""
		Change userID's team

		userID -- id of user
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Update slot and send update
		newTeam = matchTeams.blue if self.slots[slotID].team == matchTeams.red else matchTeams.red
		self.setSlot(slotID, None, newTeam)
		self.sendUpdates()

	def sendUpdates(self):
		self.matchDataCache = serverPackets.updateMatch(self.matchID)
		glob.streams.broadcast(self.streamName, self.matchDataCache)
		glob.streams.broadcast("lobby", self.matchDataCache)

	def checkTeams(self):
		"""
		Check if match teams are valid

		return -- True if valid, False if invalid
		"""
		if self.matchTeamType != matchTeamTypes.teamVs or self.matchTeamType != matchTeamTypes.tagTeamVs:
			# Teams are always valid if we have no teams
			return True

		# We have teams, check if they are valid
		firstTeam = -1
		for i in range(0,16):
			if self.slots[i].user is not None and (self.slots[i].status & slotStatuses.noMap) == 0:
				if firstTeam == -1:
					firstTeam = self.slots[i].team
				elif firstTeam != self.slots[i].team:
					log.info("MPROOM{}: Teams are valid".format(self.matchID))
					return True

		log.warning("MPROOM{}: Invalid teams!".format(self.matchID))
		return False

	def start(self):
		# Make sure we have enough players
		if self.countUsers() < 2 or not self.checkTeams():
			return

		# Create playing channel
		glob.streams.add(self.playingStreamName)

		# Change inProgress value
		match.inProgress = True

		# Set playing to ready players and set load, skip and complete to False
		# Make clients join playing stream
		for i in range(0, 16):
			if (self.slots[i].status & slotStatuses.ready) > 0 and self.slots[i].user in glob.tokens.tokens:
				self.slots[i].status = slotStatuses.playing
				self.slots[i].loaded = False
				self.slots[i].skip = False
				self.slots[i].complete = False
				glob.tokens.tokens[self.slots[i].user].joinStream(self.playingStreamName)

		# Send match start packet
		glob.streams.broadcast(self.playingStreamName, serverPackets.matchStart(self.matchID))

		# Send updates
		self.sendUpdates()