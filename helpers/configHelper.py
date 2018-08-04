import os
import configparser

class config:
	# Check if config.ini exists and load/generate it
	def __init__(self, file):
		"""
		Initialize a config file object

		:param file: file name
		"""
		self.config = configparser.ConfigParser()
		self.default = True
		self.fileName = file
		if os.path.isfile(self.fileName):
			# config.ini found, load it
			self.config.read(self.fileName)
			self.default = False
		else:
			# config.ini not found, generate a default one
			self.generateDefaultConfig()
			self.default = True


	# Check if config.ini has all needed the keys
	def checkConfig(self):
		"""
		Check is the config file has all required keys

		:return: True if valid, False if not valid
		"""
		try:
			# Try to get all the required keys
			self.config.get("db","host")
			self.config.get("db","username")
			self.config.get("db","password")
			self.config.get("db","database")
			self.config.get("db","workers")

			self.config.get("redis","host")
			self.config.get("redis","port")
			self.config.get("redis","database")
			self.config.get("redis","password")

			self.config.get("server","port")
			self.config.get("server","threads")
			self.config.get("server","gzip")
			self.config.get("server","gziplevel")
			self.config.get("server","cikey")

			self.config.get("cheesegull", "apiurl")
			self.config.get("cheesegull", "apikey")

			self.config.get("debug","enable")
			self.config.get("debug","packets")
			self.config.get("debug","time")

			self.config.get("sentry","enable")
			self.config.get("sentry","banchodsn")
			self.config.get("sentry","ircdsn")

			self.config.get("discord","enable")
			self.config.get("discord","boturl")
			self.config.get("discord","devgroup")

			self.config.get("datadog", "enable")
			self.config.get("datadog", "apikey")
			self.config.get("datadog", "appkey")

			self.config.get("irc","enable")
			self.config.get("irc","port")
			self.config.get("irc","hostname")

			self.config.get("localize","enable")
			self.config.get("localize","ipapiurl")
			return True
		except configparser.Error:
			return False

	def generateDefaultConfig(self):
		"""
		Write a default config file to disk

		:return:
		"""
		# Open config.ini in write mode
		f = open(self.fileName, "w")

		# Set keys to config object
		self.config.add_section("db")
		self.config.set("db", "host", "localhost")
		self.config.set("db", "username", "root")
		self.config.set("db", "password", "")
		self.config.set("db", "database", "ripple")
		self.config.set("db", "workers", "4")

		self.config.add_section("redis")
		self.config.set("redis", "host", "localhost")
		self.config.set("redis", "port", "6379")
		self.config.set("redis", "database", "0")
		self.config.set("redis", "password", "")

		self.config.add_section("server")
		self.config.set("server", "port", "5001")
		self.config.set("server", "threads", "16")
		self.config.set("server", "gzip", "1")
		self.config.set("server", "gziplevel", "6")
		self.config.set("server", "cikey", "changeme")

		self.config.add_section("cheesegull")
		self.config.set("cheesegull", "apiurl", "http://cheesegu.ll/api")
		self.config.set("cheesegull", "apikey", "")

		self.config.add_section("debug")
		self.config.set("debug", "enable", "0")
		self.config.set("debug", "packets", "0")
		self.config.set("debug", "time", "0")

		self.config.add_section("sentry")
		self.config.set("sentry", "enable", "0")
		self.config.set("sentry", "banchodsn", "")
		self.config.set("sentry", "ircdsn", "")

		self.config.add_section("discord")
		self.config.set("discord", "enable", "0")
		self.config.set("discord", "boturl", "")
		self.config.set("discord", "devgroup", "")

		self.config.add_section("datadog")
		self.config.set("datadog", "enable", "0")
		self.config.set("datadog", "apikey", "")
		self.config.set("datadog", "appkey", "")

		self.config.add_section("irc")
		self.config.set("irc", "enable", "1")
		self.config.set("irc", "port", "6667")
		self.config.set("irc", "hostname", "ripple")

		self.config.add_section("localize")
		self.config.set("localize", "enable", "1")
		self.config.set("localize", "ipapiurl", "http://ip.zxq.co")

		# Write ini to file and close
		self.config.write(f)
		f.close()
