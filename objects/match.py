import copy
import json
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
		self.status = slotStatuses.FREE
		self.team = 0
		self.userID = -1
		self.user = None
		self.mods = 0
		self.loaded = False
		self.skip = False
		self.complete = False
		self.score = 0

class match:
	def __init__(self, matchID, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID, isTourney=False):
		"""
		Create a new match object

		:param matchID: match progressive identifier
		:param matchName: match name, string
		:param matchPassword: match md5 password. Leave empty for no password
		:param beatmapID: beatmap ID
		:param beatmapName: beatmap name, string
		:param beatmapMD5: beatmap md5 hash, string
		:param gameMode: game mode ID. See gameModes.py
		:param hostUserID: user id of the host
		"""
		self.matchID = matchID
		self.streamName = "multi/{}".format(self.matchID)
		self.playingStreamName = "{}/playing".format(self.streamName)
		self.inProgress = False
		self.mods = 0
		self.matchName = matchName
		self.matchPassword = matchPassword
		self.beatmapID = beatmapID
		self.beatmapName = beatmapName
		self.beatmapMD5 = beatmapMD5
		self.hostUserID = hostUserID
		self.gameMode = gameMode
		self.matchScoringType = matchScoringTypes.SCORE	# default values
		self.matchTeamType = matchTeamTypes.HEAD_TO_HEAD		# default value
		self.matchModMode = matchModModes.NORMAL			# default value
		self.seed = 0
		self.matchDataCache = bytes()
		self.isTourney = isTourney
		self.isLocked = False 	# if True, users can't change slots/teams. Used in tourney matches

		# Create all slots and reset them
		self.slots = []
		for _ in range(0,16):
			self.slots.append(slot())

		# Create streams
		glob.streams.add(self.streamName)
		glob.streams.add(self.playingStreamName)

		# Create #multiplayer channel
		glob.channels.addTempChannel("#multi_{}".format(self.matchID))
		log.info("MPROOM{}: {} match created!".format(self.matchID, "Tourney" if self.isTourney else "Normal"))

	def getMatchData(self, censored = False):
		"""
		Return binary match data structure for packetHelper

		:return:
		"""
		# General match info
		# TODO: Test without safe copy, the error might have been caused by outdated python bytecode cache
		safeMatch = copy.deepcopy(self)
		struct = [
			[safeMatch.matchID, dataTypes.UINT16],
			[int(safeMatch.inProgress), dataTypes.BYTE],
			[0, dataTypes.BYTE],
			[safeMatch.mods, dataTypes.UINT32],
			[safeMatch.matchName, dataTypes.STRING]
		]
		if censored and safeMatch.matchPassword:
			struct.append(["redacted", dataTypes.STRING])
		else:
			struct.append([safeMatch.matchPassword, dataTypes.STRING])

		struct.extend([
			[safeMatch.beatmapName, dataTypes.STRING],
			[safeMatch.beatmapID, dataTypes.UINT32],
			[safeMatch.beatmapMD5, dataTypes.STRING]
		])

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
		if safeMatch.matchModMode == matchModModes.FREE_MOD:
			for i in range(0,16):
				struct.append([safeMatch.slots[i].mods, dataTypes.UINT32])

		# Seed idk
		# TODO: Implement this, it should be used for mania "random" mod
		struct.append([safeMatch.seed, dataTypes.UINT32])

		return struct

	def setHost(self, newHost):
		"""
		Set room host to newHost and send him host packet

		:param newHost: new host userID
		:return:
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
		"""
		Set data for a specific slot.
		All fields but slotID are optional.
		Skipped fields won't be edited.

		:param slotID: slot ID
		:param status: new status
		:param team: new team
		:param user: new user id
		:param mods: new mods
		:param loaded: new loaded status
		:param skip: new skip value
		:param complete: new completed value
		:return:
		"""
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

		:param slotID: slot number
		:param mods: new mods
		:return:
		"""
		# Set new slot data and send update
		self.setSlot(slotID, mods=mods)
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} mods changed to {}".format(self.matchID, slotID, mods))

	def toggleSlotReady(self, slotID):
		"""
		Switch slotID ready/not ready status
		Same as calling setSlot and then sendUpdate

		:param slotID: slot number
		:return:
		"""
		# Update ready status and setnd update
		oldStatus = self.slots[slotID].status
		if oldStatus == slotStatuses.READY:
			newStatus = slotStatuses.NOT_READY
		else:
			newStatus = slotStatuses.READY
		self.setSlot(slotID, newStatus)
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} changed ready status to {}".format(self.matchID, slotID, self.slots[slotID].status))

	def toggleSlotLock(self, slotID):
		"""
		Lock a slot
		Same as calling setSlot and then sendUpdate

		:param slotID: slot number
		:return:
		"""
		# Check if slot is already locked
		if self.slots[slotID].status == slotStatuses.LOCKED:
			newStatus = slotStatuses.FREE
		else:
			newStatus = slotStatuses.LOCKED

		# Send updated settings to kicked user, so he returns to lobby
		if self.slots[slotID].user is not None and self.slots[slotID].user in glob.tokens.tokens:
			glob.tokens.tokens[self.slots[slotID].user].enqueue(serverPackets.updateMatch(self.matchID))

		# Set new slot status
		self.setSlot(slotID, status=newStatus, team=0, user=None, mods=0)

		# Send updates to everyone else
		self.sendUpdates()
		log.info("MPROOM{}: Slot{} {}".format(self.matchID, slotID, "locked" if newStatus == slotStatuses.LOCKED else "unlocked"))

	def playerLoaded(self, userID):
		"""
		Set a player loaded status to True

		:param userID: ID of user
		:return:
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
			if self.slots[i].status == slotStatuses.PLAYING:
				total+=1
				if self.slots[i].loaded:
					loaded+=1

		if total == loaded:
			self.allPlayersLoaded()

	def allPlayersLoaded(self):
		"""
		Send allPlayersLoaded packet to every playing usr in match

		:return:
		"""
		glob.streams.broadcast(self.playingStreamName, serverPackets.allPlayersLoaded())
		log.info("MPROOM{}: All players loaded! Match starting...".format(self.matchID))

	def playerSkip(self, userID):
		"""
		Set a player skip status to True

		:param userID: ID of user
		:return:
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
			if self.slots[i].status == slotStatuses.PLAYING:
				total+=1
				if self.slots[i].skip:
					skipped+=1

		if total == skipped:
			self.allPlayersSkipped()

	def allPlayersSkipped(self):
		"""
		Send allPlayersSkipped packet to every playing usr in match

		:return:
		"""
		glob.streams.broadcast(self.playingStreamName, serverPackets.allPlayersSkipped())
		log.info("MPROOM{}: All players have skipped!".format(self.matchID))

	def updateScore(self, slotID, score):
		"""
		Update score for a slot

		:param slotID: the slot that the user that is updating their score is in
		:param score: the new score to update
		:return:
		"""
		self.slots[slotID].score = score

	def playerCompleted(self, userID):
		"""
		Set userID's slot completed to True

		:param userID: ID of user
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
			if self.slots[i].status == slotStatuses.PLAYING:
				total+=1
				if self.slots[i].complete:
					completed+=1

		if total == completed:
			self.allPlayersCompleted()

	def allPlayersCompleted(self):
		"""
		Cleanup match stuff and send match end packet to everyone

		:return:
		"""
		# Collect some info about the match that just ended to send to the api
		infoToSend = {
			"id": self.matchID,
			"name": self.matchName,
			"beatmap_id": self.beatmapID,
			"mods": self.mods,
			"game_mode": self.gameMode,
			"scores": {}
		}

		# Add score info for each player
		for i in range(0,16):
			if self.slots[i].user is not None and self.slots[i].status == slotStatuses.PLAYING:
				infoToSend["scores"][glob.tokens.tokens[self.slots[i].user].userID] = {
					"score": self.slots[i].score,
					"mods": self.slots[i].mods
				}

		# Send the info to the api
		glob.redis.publish("api:mp_complete_match", json.dumps(infoToSend))

		# Reset inProgress
		self.inProgress = False

		# Reset slots
		for i in range(0,16):
			if self.slots[i].user is not None and self.slots[i].status == slotStatuses.PLAYING:
				self.slots[i].status = slotStatuses.NOT_READY
				self.slots[i].loaded = False
				self.slots[i].skip = False
				self.slots[i].complete = False
				self.slots[i].score = 0

		# Send match update
		self.sendUpdates()

		# Send match complete
		glob.streams.broadcast(self.streamName, serverPackets.matchComplete())

		# Destroy playing stream
		glob.streams.dispose(self.playingStreamName)
		glob.streams.remove(self.playingStreamName)

		# Console output
		log.info("MPROOM{}: Match completed".format(self.matchID))

	def getUserSlotID(self, userID):
		"""
		Get slot ID occupied by userID

		:return: slot id if found, None if user is not in room
		"""
		for i in range(0,16):
			if self.slots[i].user is not None and self.slots[i].user in glob.tokens.tokens and glob.tokens.tokens[self.slots[i].user].userID == userID:
				return i
		return None

	def userJoin(self, user):
		"""
		Add someone to users in match

		:param user: user object of the user
		:return: True if join success, False if fail (room is full)
		"""
		# Make sure we're not in this match
		for i in range(0,16):
			if self.slots[i].user == user.token:
				# Set bugged slot to free
				self.setSlot(i, slotStatuses.FREE, 0, None, 0)

		# Find first free slot
		for i in range(0,16):
			if self.slots[i].status == slotStatuses.FREE:
				# Occupy slot
				self.setSlot(i, slotStatuses.NOT_READY, 0, user.token, 0)

				# Send updated match data
				self.sendUpdates()

				# Console output
				log.info("MPROOM{}: {} joined the room".format(self.matchID, user.username))
				return True

		return False

	def userLeft(self, user, disposeMatch=True):
		"""
		Remove someone from users in match

		:param user: user object of the user
		:param disposeMatch: if `True`, will try to dispose match if there are no users in the room
		:return:
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(user.userID)
		if slotID is None:
			return

		# Set that slot to free
		self.setSlot(slotID, slotStatuses.FREE, 0, None, 0)

		# Check if everyone left
		if self.countUsers() == 0 and disposeMatch and not self.isTourney:
			# Dispose match
			glob.matches.disposeMatch(self.matchID)
			log.info("MPROOM{}: Room disposed because all users left".format(self.matchID))
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

		:param userID: user that changed slot
		:param newSlotID: slot id of new slot
		:return:
		"""
		# Make sure the match is not locked
		if self.isLocked:
			return

		# Make sure the user is in room
		oldSlotID = self.getUserSlotID(userID)
		if oldSlotID is None:
			return

		# Make sure there is no one inside new slot
		if self.slots[newSlotID].user is not None and self.slots[newSlotID].status != slotStatuses.FREE:
			return

		# Get old slot data
		#oldData = dill.copy(self.slots[oldSlotID])
		oldData = copy.deepcopy(self.slots[oldSlotID])

		# Free old slot
		self.setSlot(oldSlotID, slotStatuses.FREE, 0, None, 0, False, False, False)

		# Occupy new slot
		self.setSlot(newSlotID, oldData.status, oldData.team, oldData.user, oldData.mods)

		# Send updated match data
		self.sendUpdates()

		# Console output
		log.info("MPROOM{}: {} moved to slot {}".format(self.matchID, userID, newSlotID))

	def changePassword(self, newPassword):
		"""
		Change match password to newPassword

		:param newPassword: new password string
		:return:
		"""
		self.matchPassword = newPassword

		# Send password change to every user in match
		glob.streams.broadcast(self.streamName, serverPackets.changeMatchPassword(self.matchPassword))

		# Send new match settings too
		self.sendUpdates()

		# Console output
		log.info("MPROOM{}: Password changed to {}".format(self.matchID, self.matchPassword))

	def changeMods(self, mods):
		"""
		Set match global mods

		:param mods: mods bitwise int thing
		:return:
		"""
		# Set new mods and send update
		self.mods = mods
		self.sendUpdates()
		log.info("MPROOM{}: Mods changed to {}".format(self.matchID, self.mods))

	def userHasBeatmap(self, userID, has = True):
		"""
		Set no beatmap status for userID

		:param userID: ID of user
		:param has: True if has beatmap, false if not
		:return:
		"""
		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Set slot
		self.setSlot(slotID, slotStatuses.NO_MAP if not has else slotStatuses.NOT_READY)

		# Send updates
		self.sendUpdates()

	def transferHost(self, slotID):
		"""
		Transfer host to slotID

		:param slotID: ID of slot
		:return:
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

		:param userID: ID of user
		:return:
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

		:param fro: sender userID
		:param to: receiver userID
		:return:
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

		:return: number of users
		"""
		c = 0
		for i in range(0,16):
			if self.slots[i].user is not None:
				c+=1
		return c

	def changeTeam(self, userID):
		"""
		Change userID's team

		:param userID: id of user
		:return:
		"""
		# Make sure the match is not locked
		if self.isLocked:
			return

		# Make sure the user is in room
		slotID = self.getUserSlotID(userID)
		if slotID is None:
			return

		# Update slot and send update
		newTeam = matchTeams.BLUE if self.slots[slotID].team == matchTeams.RED else matchTeams.RED
		self.setSlot(slotID, None, newTeam)
		self.sendUpdates()

	def sendUpdates(self):
		"""
		Send match updates packet to everyone in lobby and room streams

		:return:
		"""
		self.matchDataCache = serverPackets.updateMatch(self.matchID)
		censoredDataCache = serverPackets.updateMatch(self.matchID, censored=True)
		if self.matchDataCache is not None:
			glob.streams.broadcast(self.streamName, self.matchDataCache)
		if censoredDataCache is not None:
			glob.streams.broadcast("lobby", censoredDataCache)
		else:
			log.error("MPROOM{}: Can't send match update packet, match data is None!!!".format(self.matchID))

	def checkTeams(self):
		"""
		Check if match teams are valid

		:return: True if valid, False if invalid
		:return:
		"""
		if self.matchTeamType != matchTeamTypes.TEAM_VS or self.matchTeamType != matchTeamTypes.TAG_TEAM_VS:
			# Teams are always valid if we have no teams
			return True

		# We have teams, check if they are valid
		firstTeam = -1
		for i in range(0,16):
			if self.slots[i].user is not None and (self.slots[i].status & slotStatuses.NO_MAP) == 0:
				if firstTeam == -1:
					firstTeam = self.slots[i].team
				elif firstTeam != self.slots[i].team:
					log.info("MPROOM{}: Teams are valid".format(self.matchID))
					return True

		log.warning("MPROOM{}: Invalid teams!".format(self.matchID))
		return False

	def start(self):
		"""
		Start the match

		:return:
		"""
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
			if (self.slots[i].status & slotStatuses.READY) > 0 and self.slots[i].user in glob.tokens.tokens:
				self.slots[i].status = slotStatuses.PLAYING
				self.slots[i].loaded = False
				self.slots[i].skip = False
				self.slots[i].complete = False
				glob.tokens.tokens[self.slots[i].user].joinStream(self.playingStreamName)

		# Send match start packet
		glob.streams.broadcast(self.playingStreamName, serverPackets.matchStart(self.matchID))

		# Send updates
		self.sendUpdates()
