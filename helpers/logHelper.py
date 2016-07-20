from constants import bcolors
from helpers import discordBotHelper
from helpers import generalFunctions
from objects import glob
from helpers import userHelper
import time
import os
ENDL = "\n" if os.name == "posix" else "\r\n"

def logMessage(message, alertType = "INFO", messageColor = bcolors.ENDC, discord = None, alertDev = False, of = None, stdout = True):
	"""
	Logs a message to stdout/discord/file

	message -- message to log
	alertType -- can be any string. Standard types: INFO, WARNING and ERRORS. Defalt: INFO
	messageColor -- message color (see constants.bcolors). Default = bcolots.ENDC (no color)
	discord -- discord channel (bunker/cm/staff/general). Optional. Default = None
	alertDev -- if True, devs will receive an hl on discord. Default: False
	of -- if not None but a string, log the message to that file (inside .data folder). Eg: "warnings.txt" Default: None (don't log to file)
	stdout -- if True, print the message to stdout. Default: True
	"""
	# Get type color from alertType
	if alertType == "INFO":
		typeColor = bcolors.GREEN
	elif alertType == "WARNING":
		typeColor = bcolors.YELLOW
	elif alertType == "ERROR":
		typeColor = bcolors.RED
	elif alertType == "CHAT":
		typeColor = bcolors.BLUE
	elif alertType == "DEBUG":
		typeColor = bcolors.PINK
	else:
		typeColor = bcolors.ENDC

	# Message without colors
	finalMessage = "[{time}] {type} - {message}".format(time=generalFunctions.getTimestamp(), type=alertType, message=message)

	# Message with colors
	finalMessageConsole = "{typeColor}[{time}] {type}{endc} - {messageColor}{message}{endc}".format(
		time=generalFunctions.getTimestamp(),
		type=alertType,
		message=message,

		typeColor=typeColor,
		messageColor=messageColor,
		endc=bcolors.ENDC)

	# Log to console
	if stdout == True:
		print(finalMessageConsole)

	# Log to discord if needed
	if discord != None:
		if discord == "bunker":
			discordBotHelper.sendConfidential(message, alertDev)
		elif discord == "cm":
			discordBotHelper.sendCM(message)
		elif discord == "staff":
			discordBotHelper.sendStaff(message)
		elif discord == "general":
			discordBotHelper.sendGeneral(message)

	# Log to file if needed
	if of != None:
		try:
			glob.fLocks.lockFile(of)
			with open(".data/{}".format(of), "a") as f:
				f.write(finalMessage+ENDL)
		finally:
			glob.fLocks.unlockFile(of)

def warning(message, discord = None, alertDev = False):
	"""
	Log a warning to stdout, warnings.log (always) and discord (optional)

	message -- warning message
	discord -- if not None, send message to that discord channel through schiavo. Optional. Default = None
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "WARNING", bcolors.YELLOW, discord, alertDev, "warnings.txt")

def error(message, discord = None, alertDev = True):
	"""
	Log an error to stdout, errors.log (always) and discord (optional)

	message -- error message
	discord -- if not None, send message to that discord channel through schiavo. Optional. Default = None
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "ERROR", bcolors.RED, discord, alertDev, "errors.txt")

def info(message, discord = None, alertDev = False):
	"""
	Log an error to stdout (and info.log)

	message -- info message
	discord -- if not None, send message to that discord channel through schiavo. Optional. Default = None
	alertDev -- if True, send al hl to devs on discord. Optional. Default = False.
	"""
	logMessage(message, "INFO", bcolors.ENDC, discord, alertDev, "info.txt")

def debug(message):
	"""
	Log a debug message to stdout and debug.log if server is running in debug mode

	message -- debug message
	"""
	if glob.debug == True:
		logMessage(message, "DEBUG", bcolors.PINK, of="debug.txt")

def chat(message):
	"""
	Log public messages to stdout and chatlog_public.txt

	message -- chat message
	"""
	logMessage(message, "CHAT", bcolors.BLUE, of="chatlog_public.txt")

def pm(message):
	"""
	Log private messages to stdout and chatlog_private.txt

	message -- chat message
	"""
	logMessage(message, "CHAT", bcolors.BLUE, of="chatlog_private.txt")

def rap(userID, message, discord=False, through="FokaBot"):
	"""
	Log a private message to Admin logs

	userID -- userID of who made the action
	message -- message without subject (eg: "is a meme" becomes "user is a meme")
	discord -- if True, send message to discord
	through -- "through" thing string. Optional. Default: "FokaBot"
	"""
	glob.db.execute("INSERT INTO rap_logs (id, userid, text, datetime, through) VALUES (NULL, %s, %s, %s, %s)", [userID, message, int(time.time()), through])
	if discord == True:
		username = userHelper.getUsername(userID)
		logMessage("{} {}".format(username, message), discord=True)
