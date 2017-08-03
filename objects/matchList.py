from objects import match
from objects import glob
from constants import serverPackets
from common.log import logUtils as log

class matchList:
	def __init__(self):
		"""Initialize a matchList object"""
		self.matches = {}
		self.lastID = 1

	def createMatch(self, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID, isTourney=False):
		"""
		Add a new match to matches list

		:param matchName: match name, string
		:param matchPassword: match md5 password. Leave empty for no password
		:param beatmapID: beatmap ID
		:param beatmapName: beatmap name, string
		:param beatmapMD5: beatmap md5 hash, string
		:param gameMode: game mode ID. See gameModes.py
		:param hostUserID: user id of who created the match
		:return: match ID
		"""
		# Add a new match to matches list and create its stream
		matchID = self.lastID
		self.lastID+=1
		self.matches[matchID] = match.match(matchID, matchName, matchPassword, beatmapID, beatmapName, beatmapMD5, gameMode, hostUserID, isTourney)
		return matchID

	def disposeMatch(self, matchID):
		"""
		Destroy match object with id = matchID

		:param matchID: ID of match to dispose
		:return:
		"""
		# Make sure the match exists
		if matchID not in self.matches:
			return

		# Get match and disconnect all players
		_match = self.matches[matchID]
		for slot in _match.slots:
			_token = glob.tokens.getTokenFromUserID(slot.userID, ignoreIRC=True)
			if _token is None:
				continue
			_match.userLeft(_token, disposeMatch=False)	# don't dispose the match twice when we remove all players

		# Delete chat channel
		glob.channels.removeChannel("#multi_{}".format(_match.matchID))

		# Send matchDisposed packet before disposing streams
		glob.streams.broadcast(_match.streamName, serverPackets.disposeMatch(_match.matchID))

		# Dispose all streams
		glob.streams.dispose(_match.streamName)
		glob.streams.dispose(_match.playingStreamName)
		glob.streams.remove(_match.streamName)
		glob.streams.remove(_match.playingStreamName)

		# Send match dispose packet to everyone in lobby
		glob.streams.broadcast("lobby", serverPackets.disposeMatch(matchID))
		del self.matches[matchID]
		log.info("MPROOM{}: Room disposed manually".format(_match.matchID))