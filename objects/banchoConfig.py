# TODO: Rewrite this shit
from objects import glob
from helpers import generalFunctions

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
		self.config["banchoMaintenance"] = generalFunctions.stringToBool(glob.db.fetch("SELECT value_int FROM bancho_settings WHERE name = 'bancho_maintenance'")["value_int"])
		self.config["freeDirect"] = generalFunctions.stringToBool(glob.db.fetch("SELECT value_int FROM bancho_settings WHERE name = 'free_direct'")["value_int"])
		self.config["menuIcon"] = glob.db.fetch("SELECT value_string FROM bancho_settings WHERE name = 'menu_icon'")["value_string"]
		self.config["loginNotification"] = glob.db.fetch("SELECT value_string FROM bancho_settings WHERE name = 'login_notification'")["value_string"]


	def setMaintenance(self, maintenance):
		"""
		Turn on/off bancho maintenance mode. Write new value to db too

		maintenance -- if True, turn on maintenance mode. If false, turn it off
		"""
		self.config["banchoMaintenance"] = maintenance
		glob.db.execute("UPDATE bancho_settings SET value_int = %s WHERE name = 'bancho_maintenance'", [int(maintenance)])
