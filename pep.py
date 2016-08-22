"""Hello, pep.py here, ex-owner of ripple and prime minister of Ripwot."""
import sys
import os
import threading

# Bottle
import bottle
from gevent import monkey as brit_monkey
brit_monkey.patch_all()

# pep.py files
from constants import bcolors
from helpers import configHelper
from objects import glob
from objects import fokabot
from objects import banchoConfig
from objects import chatFilters
from helpers import consoleHelper
from helpers import databaseHelperNew
from helpers import generalFunctions
from helpers import logHelper as log

# Raven
from raven import Client
from raven.contrib.bottle import Sentry

# IRC
from irc import ircserver

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
		consoleHelper.printNoNl("> Connecting to MySQL db")
		glob.db = databaseHelperNew.db(glob.conf.config["db"]["host"], glob.conf.config["db"]["username"], glob.conf.config["db"]["password"], glob.conf.config["db"]["database"], int(glob.conf.config["db"]["workers"]))
		consoleHelper.printNoNl(" ")
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

	try:
		consoleHelper.printNoNl("> Loading chat filters... ")
		glob.chatFilters = chatFilters.chatFilters()
		consoleHelper.printDone()
	except:
		consoleHelper.printError()
		consoleHelper.printColored("[!] Error while loading chat filters. Make sure there is a filters.txt file present", bcolors.RED)
		raise

	# Create data folder if needed
	consoleHelper.printNoNl("> Checking folders... ")
	paths = [".data"]
	for i in paths:
		if not os.path.exists(i):
			os.makedirs(i, 0o770)
	consoleHelper.printDone()

	# Initialize chat channels
	print("> Initializing chat channels... ")
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
	glob.localize = generalFunctions.stringToBool(glob.conf.config["localize"]["enable"])
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

	# Make app
	app = bottle.app()
	app.catchall = False
	from handlers import mainHandler
	from handlers import apiIsOnlineHandler
	from handlers import apiOnlineUsersHandler
	from handlers import apiServerStatusHandler
	from handlers import ciTriggerHandler
	from handlers import apiVerifiedStatusHandler
	from handlers import apiFokabotMessageHandler

	# Set up sentry
	try:
		glob.sentry = generalFunctions.stringToBool(glob.conf.config["sentry"]["enable"])
		if glob.sentry == True:
			client = Client(glob.conf.config["sentry"]["banchodns"], release=glob.VERSION)
			app = Sentry(app, client)
		else:
			consoleHelper.printColored("[!] Warning! Sentry logging is disabled!", bcolors.YELLOW)
	except:
		consoleHelper.printColored("[!] Error while starting sentry client! Please check your config.ini and run the server again", bcolors.RED)

	# Cloudflare memes
	glob.cloudflare = generalFunctions.stringToBool(glob.conf.config["server"]["cloudflare"])

	# IRC start message and console output
	glob.irc = generalFunctions.stringToBool(glob.conf.config["irc"]["enable"])
	if glob.irc == True:
		# IRC port
		try:
			ircPort = int(glob.conf.config["irc"]["port"])
		except:
			consoleHelper.printColored("[!] Invalid IRC port! Please check your config.ini and run the server again", bcolors.RED)
		log.logMessage("IRC server started!", discord=True, of="info.txt", stdout=False)
		consoleHelper.printColored("> IRC server listening on 127.0.0.1:{}...".format(ircPort), bcolors.GREEN)
		threading.Thread(target=lambda: ircserver.main(port=ircPort)).start()
	else:
		consoleHelper.printColored("[!] Warning! IRC server is disabled!", bcolors.YELLOW)

	# Server port
	try:
		serverPort = int(glob.conf.config["server"]["port"])
	except:
		consoleHelper.printColored("[!] Invalid server port! Please check your config.ini and run the server again", bcolors.RED)

	# Server start message and console output
	log.logMessage("Server started!", discord=True, stdout=False)
	consoleHelper.printColored("> Bottle listening for HTTP(s) clients on 127.0.0.1:{}...".format(serverPort), bcolors.GREEN)

	# Start bottle
	bottle.run(app=app, host="0.0.0.0", port=serverPort, server="gevent", quiet=True)
