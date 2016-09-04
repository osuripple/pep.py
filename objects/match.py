# TODO: Enqueue all
from constants import gameModes
from constants import matchScoringTypes
from constants import matchTeamTypes
from constants import matchModModes
from constants import slotStatuses
from objects import glob
from constants import serverPackets
from constants import dataTypes
from constants import matchTeams
from helpers import logHelper as log
from helpers import chatHelper as chat
from helpers import generalFunctions
import copy

class slot:
	def __init__(self):
		self.status = slotStatuses.free
		self.team = 0
		self.userID = -1
		self.mods = 0
		self.loaded = False
		self.skip = False
		self.complete = False

class match:
	"""Multiplayer match object"""
	matchID = 0
	inProgress = False
	mods = 0
	matchName = ""
	matchPassword = ""
	beatmapName = ""
	beatmapID = 0
	beatmapMD5 = ""
	slots = []
	hostUserID = 0
	gameMode = gameModes.std
	matchScoringType = matchScoringTypes.score
	matchTeamType = matchTeamTypes.headToHead
	matchModMode = matchModModes.normal
	seed = 0

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
		self.inProgress = False
		self.mods = 0
		self.matchName = matchName
		if matchPassword != "":
			self.matchPassword = generalFunctions.stringMd5(matchPassword)
		else:
			self.matchPassword = ""
		self.beatmapID = beatmapID
		self.beatmapName = beatmapName
		self.beatmapMD5 = beatmapMD5
		self.hostUserID = hostUserID
		self.gameMode = gameMode
		self.matchScoringTypes = matchScoringTypes.score	# default values
		self.matchTeamType = matchTeamTypes.headToHead		# default value
		self.matchModMode = matchModModes.normal			# default value
		self.seed = 0

		# Create all slots and reset them
		self.slots = []
		for _ in range(0,16):
			self.slots.append(slot())

		# Create #multiplayer channel
		glob.channels.addTempChannel("#multi_{}".format(self.matchID))

	def getMatchData(self):
		"""
		Return binary match data structure for packetHelper
		"""
		# General match info
		struct = [
			[self.matchID, dataTypes.UINT16],
			[int(self.inProgress), dataTypes.BYTE],
			[0, dataTypes.BYTE],
			[self.mods, dataTypes.UINT32],
			[self.matchName, dataTypes.STRING],
			[self.matchPassword, dataTypes.STRING],
			[self.beatmapName, dataTypes.STRING],
			[self.beatmapID, dataTypes.UINT32],
			[self.beatmapMD5, dataTypes.STRING],
		]

		# Slots status IDs, always 16 elements
		for i in range(0,16):
			struct.append([self.slots[i].status, dataTypes.BYTE])

		# Slot teams, always 16 elements
		for i in range(0,16):
			struct.append([self.slots[i].team, dataTypes.BYTE])

		# Slot user ID. Write only if slot is occupied
		for i in range(0,16):
			uid = self.slots[i].userID
			if uid > -1:
				struct.append([uid, dataTypes.UINT32])

		# Other match data
		struct.extend([
			[self.hostUserID, dataTypes.SINT32],
			[self.gameMode, dataTypes.BYTE],
			[self.matchScoringType, dataTypes.BYTE],
			[self.matchTeamType, dataTypes.BYTE],
			[self.matchModMode, dataTypes.BYTE],
		])

		# Slot mods if free mod is enabled
		if self.matchModMode == matchModModes.freeMod:
			for i in range(0,16):
				struct.append([self.slots[i].mods, dataTypes.UINT32])

		# Seed idk
		struct.append([self.seed, dataTypes.UINT32])

		return struct

	def setHost(self, newHost):
		"""
		Set room host to newHost and send him host packet

		newHost -- new host userID
		"""
		self.hostUserID = newHost

		# Send host packet to new host
		token = glob.tokens.getTokenFromUserID(newHost)
		if token is not None:
			token.enqueue(serverPackets.matchTransferHost())

		log.info("MPROOM{}: {} is now the host".format(self.matchID, newHost))

	def setSlot(self, slotID, slotStatus = None, slotTeam = None, slotUserID = None, slotMods = None, slotLoaded = None, slotSkip = None, slotComplete = None):
		"""
		Set a slot to a specific userID and status

		slotID -- id of that slot (0-15)
		slotStatus -- see slotStatuses.py
		slotTeam -- team id
		slotUserID -- user ID of user in that slot
		slotMods -- mods enabled in that slot. 0 if not free mod.
		slotLoaded -- loaded status True/False
		slotSkip -- skip status True/False
		slotComplete -- completed status True/False

		If Null is passed, that value won't be edited
		"""
		if slotStatus is not None:
			self.slots[slotID].status = slotStatus

		if slotTeam is not None:
			self.slots[slotID].team = slotTeam

		if slotUserID is not None:
			self.slots[slotID].userID = slotUserID

		if slotMods is not None:
			self.slots[slotID].mods = slotMods

		if slotLoaded is not None:
			self.slots[slotID].loaded = slotLoaded

		if slotSkip is not None:
			self.slots[slotID].skip = slotSkip

		if slotComplete is not None:
			self.slots[slotID].complete = slotComplete

	def setSlotMods(self, slotID, mods):
		"""
		Set slotID mods. Same as calling setSlot and then sendUpdate

		slotID -- slot number
		mods -- new mods
		"""
		# Set new slot data and send update
		self.setSlot(slotID, None, None, None, mods)
		self.sendUpdate()
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
		self.setSlot(slotID, newStatus, None, None, None)
		self.sendUpdate()
		log.info("MPROOM{}: Slot{} changed ready status to {}".format(self.matchID, slotID, self.slots[slotID].status))

	def toggleSlotLock(self, slotID):
		"""
		Lock a slot
		Same as calling setSlot and then sendUpdate

		slotID -- slot number
		"""
		# Get token of user in that slot (if there's someone)
		if self.slots[slotID].userID > -1:
			token = glob.tokens.getTokenFromUserID(self.slots[slotID].userID)
		else:
			token = None

		# Check if slot is already locked
		if self.slots[slotID].status == slotStatuses.locked:
			newStatus = slotStatuses.free
		else:
			newStatus = slotStatuses.locked

		# Set new slot status
		self.setSlot(slotID, newStatus, 0, -1, 0)
		if token is not None:
			# Send updated settings to kicked user, so he returns to lobby
			token.enqueue(serverPackets.updateMatch(self.matchID))

		# Send updates to everyone else
		self.sendUpdate()
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
		for i in range(0,16):
			if self.slots[i].userID > -1 and self.slots[i].status == slotStatuses.playing:
				token = glob.tokens.getTokenFromUserID(self.slots[i].userID)
				if token is not None:
					token.enqueue(serverPackets.allPlayersLoaded())

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
		for i in range(0,16):
			uid = self.slots[i].userID
			if (self.slots[i].status & slotStatuses.playing > 0) and uid > -1:
				token = glob.tokens.getTokenFromUserID(uid)
				if token is not None:
					token.enqueue(serverPackets.playerSkipped(uid))

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
		for i in range(0,16):
			if self.slots[i].userID > -1 and self.slots[i].status == slotStatuses.playing:
				token = glob.tokens.getTokenFromUserID(self.slots[i].userID)
				if token is not None:
					token.enqueue(serverPackets.allPlayersSkipped())

		log.info("MPROOM{}: All players have skipped!".format(self.matchID))

	def playerCompleted(self, userID):
		"""
		Set userID's slot completed to True

		userID -- ID of user
		"""
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return
		self.setSlot(slotID, None, None, None, None, None, None, True)

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
			if self.slots[i].userID > -1 and self.slots[i].status == slotStatuses.playing:
				self.slots[i].status = slotStatuses.notReady
				self.slots[i].loaded = False
				self.slots[i].skip = False
				self.slots[i].complete = False

		# Send match update
		self.sendUpdate()

		# Send match complete
		for i in range(0,16):
			if self.slots[i].userID > -1:
				token = glob.tokens.getTokenFromUserID(self.slots[i].userID)
				if token is not None:
					token.enqueue(serverPackets.matchComplete())

		# Console output
		log.info("MPROOM{}: Match completed".format(self.matchID))

	def getUserSlotID(self, userID):
		"""
		Get slot ID occupied by userID

		return -- slot id if found, None if user is not in room
		"""
		for i in range(0,16):
			if self.slots[i].userID == userID:
				return i
		return None

	def userJoin(self, userID):
		"""
		Add someone to users in match

		userID -- user id of the user
		return -- True if join success, False if fail (room is full)
		"""

		# Make sure we're not in this match
		for i in range(0,16):
			if self.slots[i].userID == userID:
				# Set bugged slot to free
				self.setSlot(i, slotStatuses.free, 0, -1, 0)

		# Find first free slot
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.free:
				# Occupy slot
				self.setSlot(i, slotStatuses.notReady, 0, userID, 0)

				# Send updated match data
				self.sendUpdate()

				# Console output
				log.info("MPROOM{}: {} joined the room".format(self.matchID, userID))

				return True

		return False

	def userLeft(self, userID):
		"""
		Remove someone from users in match

		userID -- user if of the user
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Set that slot to free
		self.setSlot(slotID, slotStatuses.free, 0, -1, 0)

		# Check if everyone left
		if self.countUsers() == 0:
			# Dispose match
			glob.matches.disposeMatch(self.matchID)
			log.info("MPROOM{}: Room disposed".format(self.matchID))
			return

		# Check if host left
		if userID == self.hostUserID:
			# Give host to someone else
			for i in range(0,16):
				uid = self.slots[i].userID
				if uid > -1:
					self.setHost(uid)
					break

		# Send updated match data
		self.sendUpdate()

		# Console output
		log.info("MPROOM{}: {} left the room".format(self.matchID, userID))

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
		if self.slots[newSlotID].userID > -1 and self.slots[newSlotID].status != slotStatuses.free:
			return

		# Get old slot data
		oldData = copy.deepcopy(self.slots[oldSlotID])

		# Free old slot
		self.setSlot(oldSlotID, slotStatuses.free, 0, -1, 0)

		# Occupy new slot
		self.setSlot(newSlotID, oldData.status, oldData.team, oldData.userID, oldData.mods)

		# Send updated match data
		self.sendUpdate()

		# Console output
		log.info("MPROOM{}: {} moved to slot {}".format(self.matchID, userID, newSlotID))

	def changePassword(self, newPassword):
		"""
		Change match password to newPassword

		newPassword -- new password string
		"""
		if newPassword != "":
			self.matchPassword = generalFunctions.stringMd5(newPassword)
		else:
			self.matchPassword = ""

		# Send password change to every user in match
		for i in range(0,16):
			if self.slots[i].userID > -1:
				token = glob.tokens.getTokenFromUserID(self.slots[i].userID)
				if token is not None:
					token.enqueue(serverPackets.changeMatchPassword(self.matchPassword))

		# Send new match settings too
		self.sendUpdate()

		# Console output
		log.info("MPROOM{}: Password changed to {}".format(self.matchID, self.matchPassword))

	def changeMatchMods(self, mods):
		"""
		Set match global mods

		mods -- mods bitwise int thing
		"""
		# Set new mods and send update
		self.mods = mods
		self.sendUpdate()
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
		self.sendUpdate()

	def transferHost(self, slotID):
		"""
		Transfer host to slotID

		slotID -- ID of slot
		"""
		# Make sure there is someone in that slot
		uid = self.slots[slotID].userID
		if uid == -1:
			return

		# Transfer host
		self.setHost(uid)

		# Send updates
		self.sendUpdate()

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
		for i in range(0,16):
			uid = self.slots[i].userID
			if uid > -1:
				token = glob.tokens.getTokenFromUserID(uid)
				if token is not None:
					token.enqueue(serverPackets.playerFailed(slotID))

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
			if self.slots[i].userID > -1:
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
		self.sendUpdate()

	def sendUpdate(self):
		# Send to users in room
		for i in range(0,16):
			if self.slots[i].userID > -1:
				token = glob.tokens.getTokenFromUserID(self.slots[i].userID)
				if token is not None:
					token.enqueue(serverPackets.updateMatch(self.matchID))

		# Send to users in lobby
		for i in glob.matches.usersInLobby:
			token = glob.tokens.getTokenFromUserID(i)
			if token is not None:
				token.enqueue(serverPackets.updateMatch(self.matchID))

	def checkTeams(self):
		"""
		Check if match teams are valid

		return -- True if valid, False if invalid
		"""
		if match.matchTeamType != matchTeamTypes.teamVs or matchTeamTypes != matchTeamTypes.tagTeamVs:
			# Teams are always valid if we have no teams
			return True

		# We have teams, check if they are valid
		firstTeam = -1
		for i in range(0,16):
			if self.slots[i].userID > -1 and (self.slots[i].status&slotStatuses.noMap) == 0:
				if firstTeam == -1:
					firstTeam = self.slots[i].team
				elif firstTeam != self.slots[i].team:
					log.info("MPROOM{}: Teams are valid".format(self.matchID))
					return True

		log.warning("MPROOM{}: Invalid teams!".format(self.matchID))
		return False
