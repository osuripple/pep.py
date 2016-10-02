from common.log import logUtils as log
from objects import channel
from objects import glob


class channelList:
	"""
	Channel list

	channels -- dictionary. key: channel name, value: channel object
	"""
	channels = {}

	def loadChannels(self):
		"""
		Load chat channels from db and add them to channels dictionary
		"""

		# Get channels from DB
		channels = glob.db.fetchAll("SELECT * FROM bancho_channels")

		# Add each channel if needed
		for i in channels:
			if i["name"] not in self.channels:
				publicRead = True if i["public_read"] == 1 else False
				publicWrite = True if i["public_write"] == 1 else False
				self.addChannel(i["name"], i["description"], publicRead, publicWrite)

	def addChannel(self, name, description, publicRead, publicWrite, temp = False, hidden = False):
		"""
		Add a channel object to channels dictionary

		name -- channel name
		description -- channel description
		publicRead -- bool, if true channel can be read by everyone, if false it can be read only by mods/admins
		publicWrite -- bool, same as public read but relative to write permissions
		temp -- if True, channel will be deleted when there's no one in the channel. Optional. Default = False.
		hidden -- if True, channel will be hidden in channels list. Optional. Default = False.
		"""
		self.channels[name] = channel.channel(name, description, publicRead, publicWrite, temp, hidden)
		log.info("Created channel {}".format(name))

	def addTempChannel(self, name):
		"""
		Add a temporary channel (like #spectator or #multiplayer), gets deleted when there's no one in the channel
		and it's hidden in channels list

		name -- channel name
		return -- True if channel was created, False if failed
		"""
		if name in self.channels:
			return False
		self.channels[name] = channel.channel(name, "Chat", True, True, True, True)
		log.info("Created temp channel {}".format(name))

	def removeChannel(self, name):
		"""
		Removes a channel from channels list

		name -- channel name
		"""
		if name not in self.channels:
			log.debug("{} is not in channels list".format(name))
			return
		self.channels.pop(name)
		log.info("Removed channel {}".format(name))
