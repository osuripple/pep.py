# TODO: Rewrite this shit
from common import generalUtils
from constants import serverPackets
from objects import glob
from common.log import logUtils as log


class banchoConfig:
	"""
	Class that loads settings from bancho_settings db table
	"""

	config = {"banchoMaintenance": False, "freeDirect": True, "menuIcon": "", "loginNotification": ""}

	def __init__(self, loadFromDB = True):
		"""
		Initialize a banchoConfig object (and load bancho_settings from db)

		loadFromDB -- if True, load values from db. If False, don't load values. Optional.
		"""
		if loadFromDB:
			try:
				self.loadSettings()
			except:
				raise


	def loadSettings(self):
		"""
		(re)load bancho_settings from DB and set values in config array
		"""
		self.config["banchoMaintenance"] = generalUtils.stringToBool(glob.db.fetch("SELECT value_int FROM bancho_settings WHERE name = 'bancho_maintenance'")["value_int"])
		self.config["freeDirect"] = generalUtils.stringToBool(glob.db.fetch("SELECT value_int FROM bancho_settings WHERE name = 'free_direct'")["value_int"])
		mainMenuIcon = glob.db.fetch("SELECT file_id, url FROM main_menu_icons WHERE is_current = 1 LIMIT 1")
		if mainMenuIcon is None:
			self.config["menuIcon"] = ""
		else:
			imageURL = "https://i.ppy.sh/{}.png".format(mainMenuIcon["file_id"])
			self.config["menuIcon"] = "{}|{}".format(imageURL, mainMenuIcon["url"])
		self.config["loginNotification"] = glob.db.fetch("SELECT value_string FROM bancho_settings WHERE name = 'login_notification'")["value_string"]


	def setMaintenance(self, maintenance):
		"""
		Turn on/off bancho maintenance mode. Write new value to db too

		maintenance -- if True, turn on maintenance mode. If false, turn it off
		"""
		self.config["banchoMaintenance"] = maintenance
		glob.db.execute("UPDATE bancho_settings SET value_int = %s WHERE name = 'bancho_maintenance'", [int(maintenance)])

	def reload(self):
		# Reload settings from bancho_settings
		glob.banchoConf.loadSettings()

		# Reload channels too
		glob.channels.loadChannels()

		# And chat filters
		glob.chatFilters.loadFilters()

		# Send new channels and new bottom icon to everyone
		glob.streams.broadcast("main", serverPackets.mainMenuIcon(glob.banchoConf.config["menuIcon"]))
		glob.streams.broadcast("main", serverPackets.channelInfoEnd())
		for key, value in glob.channels.channels.items():
			if value.publicRead and not value.hidden:
				glob.streams.broadcast("main", serverPackets.channelInfo(key))