"""Hello, pep.py here, ex-owner of ripple and prime minister of Ripwot."""
import sys
import os
from multiprocessing.pool import ThreadPool

# Tornado
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen

# Raven
from raven.contrib.tornado import AsyncSentryClient

# pep.py files
from constants import bcolors
from helpers import configHelper
from objects import glob
from objects import fokabot
from objects import banchoConfig
from helpers import consoleHelper
from helpers import databaseHelperNew
from helpers import generalFunctions
from helpers import logHelper as log


from handlers import mainHandler
from handlers import apiIsOnlineHandler
from handlers import apiOnlineUsersHandler
from handlers import apiServerStatusHandler
from handlers import ciTriggerHandler


def make_app():
	return tornado.web.Application([
		(r"/", mainHandler.handler),
		(r"/api/v1/isOnline", apiIsOnlineHandler.handler),
		(r"/api/v1/onlineUsers", apiOnlineUsersHandler.handler),
		(r"/api/v1/serverStatus", apiServerStatusHandler.handler),
		(r"/api/v1/ciTrigger", ciTriggerHandler.handler),
	])

if __name__ == "__main__":
	# Server start
	consoleHelper.printServerStartHeader(True)

	# Read config.ini
	consoleHelper.printNoNl("> Loading config file... ")
	glob.conf = configHelper.config("config.ini")

	if glob.conf.default == True:
		# We have generated a default config.ini, quit server
		consoleHelper.printWarning()
		consoleHelper.printColored("[!] config.ini not found. A default one has been generated.", bcolors.YELLOW)
		consoleHelper.printColored("[!] Please edit your config.ini and run the server again.", bcolors.YELLOW)
		sys.exit()

	# If we haven't generated a default config.ini, check if it's valid
	if glob.conf.checkConfig() == False:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Invalid config.ini. Please configure it properly", bcolors.RED)
		consoleHelper.printColored("[!] Delete your config.ini to generate a default one", bcolors.RED)
		sys.exit()
	else:
		consoleHelper.printDone()


	# Connect to db
	try:
		print("> Connecting to MySQL db... ")
		glob.db = databaseHelperNew.db(glob.conf.config["db"]["host"], glob.conf.config["db"]["username"], glob.conf.config["db"]["password"], glob.conf.config["db"]["database"], int(glob.conf.config["db"]["workers"]))
		consoleHelper.printDone()
	except:
		# Exception while connecting to db
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while connection to database. Please check your config.ini and run the server again", bcolors.RED)
		raise

	# Load bancho_settings
	try:
		consoleHelper.printNoNl("> Loading bancho settings from DB... ")
		glob.banchoConf = banchoConfig.banchoConfig()
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while loading bancho_settings. Please make sure the table in DB has all the required rows", bcolors.RED)
		raise

	# Delete old bancho sessions
	consoleHelper.printNoNl("> Deleting cached bancho sessions from DB... ")
	glob.tokens.deleteBanchoSessions()
	consoleHelper.printDone()

	# Create threads pool
	try:
		consoleHelper.printNoNl("> Creating threads pool... ")
		glob.pool = ThreadPool(int(glob.conf.config["server"]["threads"]))
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while creating threads pool. Please check your config.ini and run the server again", bcolors.RED)

	# Create data folder if needed
	consoleHelper.printNoNl("> Checking folders... ")
	paths = [".data"]
	for i in paths:
		if not os.path.exists(i):
			os.makedirs(i, 0o770)
	consoleHelper.printDone()

	# Initialize chat channels
	consoleHelper.printNoNl("> Initializing chat channels... ")
	glob.channels.loadChannels()
	consoleHelper.printDone()

	# Start fokabot
	consoleHelper.printNoNl("> Connecting FokaBot... ")
	fokabot.connect()
	consoleHelper.printDone()

	# Initialize user timeout check loop
	consoleHelper.printNoNl("> Initializing user timeout check loop... ")
	glob.tokens.usersTimeoutCheckLoop()
	consoleHelper.printDone()

	# Initialize spam protection reset loop
	consoleHelper.printNoNl("> Initializing spam protection reset loop... ")
	glob.tokens.spamProtectionResetLoop()
	consoleHelper.printDone()

	# Localize warning
	glob.localize = generalFunctions.stringToBool(glob.conf.config["server"]["localize"])
	if glob.localize == False:
		consoleHelper.printColored("[!] Warning! Users localization is disabled!", bcolors.YELLOW)

	# Discord
	glob.discord = generalFunctions.stringToBool(glob.conf.config["discord"]["enable"])
	if glob.discord == False:
		consoleHelper.printColored("[!] Warning! Discord logging is disabled!", bcolors.YELLOW)

	# Gzip
	glob.gzip = generalFunctions.stringToBool(glob.conf.config["server"]["gzip"])
	glob.gziplevel = int(glob.conf.config["server"]["gziplevel"])
	if glob.gzip == False:
		consoleHelper.printColored("[!] Warning! Gzip compression is disabled!", bcolors.YELLOW)

	# Debug mode
	glob.debug = generalFunctions.stringToBool(glob.conf.config["debug"]["enable"])
	glob.outputPackets = generalFunctions.stringToBool(glob.conf.config["debug"]["packets"])
	glob.outputRequestTime = generalFunctions.stringToBool(glob.conf.config["debug"]["time"])
	if glob.debug == True:
		consoleHelper.printColored("[!] Warning! Server running in debug mode!", bcolors.YELLOW)

	# Server port
	try:
		serverPort = int(glob.conf.config["server"]["port"])
	except:
		consoleHelper.printColored("[!] Invalid server port! Please check your config.ini and run the server again", bcolors.RED)

	# Make app
	#application = tornado.httpserver.HTTPServer(make_app())
	application = make_app()

	# Set up sentry
	try:
		glob.sentry = generalFunctions.stringToBool(glob.conf.config["sentry"]["enable"])
		if glob.sentry == True:
			application.sentry_client = AsyncSentryClient(glob.conf.config["sentry"]["dns"])
		else:
			consoleHelper.printColored("[!] Warning! Sentry logging is disabled!", bcolors.YELLOW)
	except:
		consoleHelper.printColored("[!] Error while starting sentry client! Please check your config.ini and run the server again", bcolors.RED)

	# Server start message and console output
	log.logMessage("Server started!", discord=True, of="info.txt", stdout=False)
	consoleHelper.printColored("> Tornado listening for clients on 127.0.0.1:{}...".format(serverPort), bcolors.GREEN)

	# Start tornado
	application.listen(serverPort)
	tornado.ioloop.IOLoop.instance().start()
