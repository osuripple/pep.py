import random
import time

from common.log import logUtils as log
from objects import glob

class channel:
	def __init__(self, name, description, publicRead, publicWrite, temp, hidden):
		"""
		Create a new chat channel object

		:param name: channel name
		:param description: channel description
		:param publicRead: if True, this channel can be read by everyone. If False, it can be read only by mods/admins
		:param publicWrite: same as public read, but regards writing permissions
		:param temp: if True, this channel will be deleted when there's no one in this channel
		:param hidden: if True, thic channel won't be shown in channels list
		"""
		self.name = name
		self.description = description
		self.publicRead = publicRead
		self.publicWrite = publicWrite
		self.moderated = False
		self.temp = temp
		self.hidden = hidden

		self.activity = 0.
		self._lastActivityTime = time.time()
		self._lastMashinLrningTime = 0
		self.lastSender = ""

		# Client name (#spectator/#multiplayer)
		self.clientName = self.name
		if self.name.startswith("#spect_"):
			self.clientName = "#spectator"
		elif self.name.startswith("#multi_"):
			self.clientName = "#multiplayer"

		# Make Foka join the channel
		fokaToken = glob.tokens.getTokenFromUserID(999)
		if fokaToken is not None:
			fokaToken.joinChannel(self)

	def increaseActivity(self, increment=1.0):
		if time.time() - self._lastActivityTime > 10:
			self.activity = 0
		self.activity += increment
		self._lastActivityTime = time.time()
		log.debug("{} activity is now {} (inc {}), time is {}".format(
			self.name, self.activity, increment, self._lastActivityTime
		))

	@property
	def isInactive(self):
		return self._lastActivityTime < time.time() - 60

	@property
	def isMashinLrnable(self):
		return self.activity >= 5 and time.time() > self._lastMashinLrningTime - 20

	def mashinLrn(self):
		self.activity = 0
		self._lastMashinLrningTime = time.time()
		idx = glob.lastMashin
		while idx == glob.lastMashin:
			idx = random.randrange(0, len(glob.mashin))
		glob.lastMashin = idx
		return glob.mashin[idx]
