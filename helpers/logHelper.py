from constants import bcolors
from helpers import discordBotHelper
from helpers import generalFunctions

def logMessage(message, alertType, messageColor, discord = False, alertDev = False, of = None):
	if alertType == "INFO":
		typeColor = bcolors.GREEN
	elif alertType == "WARNING":
		typeColor = bcolors.YELLOW
	elif typeColor == "ERROR":
		typeColor = bcolors.RED
	else:
		typeColor = bcolors.ENDC

	finalMessage = "[{time}] {type} - {message}".format(time=generalFunctions.getTimestamp(), type=alertType, message=message)
	finalMessageConsole = "{typeColor}[{time}] {type}{endc} - {messageColor}{message}{endc}".format(
		time=generalFunctions.getTimestamp(),
		type=alertType,
		message=message,

		typeColor=typeColor,
		messageColor=messageColor,
		endc=bcolors.ENDC)

	# Always log to console
	print(finalMessageConsole)

	# Log to discord if needed
	if discord == True:
		discordBotHelper.sendConfidential(message, alertDev)

	# Log to file if needed
	if of != None:
		with open(".data/{}".format(of), "a") as f:
			f.write(finalMessage)

def warning(message, discord = False, alertDev = False):
	logMessage(message, "WARNING", bcolors.YELLOW, discord, alertDev, "warnings.txt")

def error(message, discord = False, alertDev = True):
	logMessage(message, "ERROR", bcolors.RED, discord, alertDev, "errors.txt")
