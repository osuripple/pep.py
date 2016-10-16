import os
import configparser

class config:
	# Check if config.ini exists and load/generate it
	def __init__(self, file):
		"""
		Initialize a config object

		file -- filename
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
		Check if this config has the required keys

		return -- True if valid, False if not
		"""
		try:
			# Try to get all the required keys
			self.config.get("db","host")
			self.config.get("db","username")
			self.config.get("db","password")
			self.config.get("db","database")
			self.config.get("db","workers")

			self.config.get("server","port")
			self.config.get("server","threads")
			self.config.get("server","gzip")
			self.config.get("server","gziplevel")
			self.config.get("server","cikey")
			self.config.get("server","cloudflare")

			self.config.get("mirror","url")
			self.config.get("mirror","apikey")

			self.config.get("debug","enable")
			self.config.get("debug","packets")
			self.config.get("debug","time")

			self.config.get("sentry","enable")
			self.config.get("sentry","banchodns")
			self.config.get("sentry","ircdns")

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
		except:
			return False

	def generateDefaultConfig(self):
		"""
		Open and set default keys for that config file
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

		self.config.add_section("server")
		self.config.set("server", "port", "5001")
		self.config.set("server", "threads", "16")
		self.config.set("server", "gzip", "1")
		self.config.set("server", "gziplevel", "6")
		self.config.set("server", "cikey", "changeme")
		self.config.set("server", "cloudflare", "0")

		self.config.add_section("mirror")
		self.config.set("mirror", "url", "http://storage.ripple.moe")
		self.config.set("mirror", "apikey", "anotherkey")

		self.config.add_section("debug")
		self.config.set("debug", "enable", "0")
		self.config.set("debug", "packets", "0")
		self.config.set("debug", "time", "0")

		self.config.add_section("sentry")
		self.config.set("sentry", "enable", "0")
		self.config.set("sentry", "banchodns", "")
		self.config.set("sentry", "ircdns", "")

		self.config.add_section("discord")
		self.config.set("discord", "enable", "0")
		self.config.set("discord", "boturl", "")
		self.config.set("discord", "devgroup", "")

		self.config.add_section("datadog")
		self.config.set("datadog", "enable")
		self.config.set("datadog", "apikey")
		self.config.set("datadog", "appkey")

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
