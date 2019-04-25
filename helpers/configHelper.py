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

	def reload(self):
		tempConfig = configparser.ConfigParser()
		tempConfig.read(self.fileName)
		if not self.checkConfig(tempConfig):
			return False
		self.config = tempConfig
		return True


	# Check if config.ini has all needed the keys
	def checkConfig(self, parsedConfig=None):
		"""
		Check is the config file has all required keys

		:return: True if valid, False if not valid
		"""
		if parsedConfig is None:
			parsedConfig = self.config
		try:
			# Try to get all the required keys
			parsedConfig.get("db", "host")
			parsedConfig.get("db", "username")
			parsedConfig.get("db", "password")
			parsedConfig.get("db", "database")
			parsedConfig.get("db", "workers")

			parsedConfig.get("redis", "host")
			parsedConfig.get("redis", "port")
			parsedConfig.get("redis", "database")
			parsedConfig.get("redis", "password")

			parsedConfig.get("server", "port")
			parsedConfig.get("server", "threads")
			parsedConfig.get("server", "gzip")
			parsedConfig.get("server", "gziplevel")
			parsedConfig.get("server", "cikey")
			parsedConfig.get("server", "letsapiurl")
			parsedConfig.get("server", "deltaurl")
			parsedConfig.get("server", "publicdelta")

			parsedConfig.get("cheesegull", "apiurl")
			parsedConfig.get("cheesegull", "apikey")

			parsedConfig.get("debug", "enable")
			parsedConfig.get("debug", "packets")
			parsedConfig.get("debug", "time")

			parsedConfig.get("sentry", "enable")
			parsedConfig.get("sentry", "banchodsn")
			parsedConfig.get("sentry", "ircdsn")

			parsedConfig.get("discord", "enable")
			parsedConfig.get("discord", "boturl")
			parsedConfig.get("discord", "devgroup")

			parsedConfig.get("datadog", "enable")
			parsedConfig.get("datadog", "apikey")
			parsedConfig.get("datadog", "appkey")

			parsedConfig.get("irc", "enable")
			parsedConfig.get("irc", "port")
			parsedConfig.get("irc", "hostname")

			parsedConfig.get("localize", "enable")
			parsedConfig.get("localize", "ipapiurl")
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
		self.config.set("server", "letsapiurl", "http://.../letsapi")
		self.config.set("server", "deltaurl", "delta.ppy.sh")
		self.config.set("server", "publicdelta", "0")

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
