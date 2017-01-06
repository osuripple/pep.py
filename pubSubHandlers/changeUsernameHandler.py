from common.redis import generalPubSubHandler
from common.ripple import userUtils
from common.log import logUtils as log
from common.constants import actions
from objects import glob

def handleUsernameChange(userID, newUsername, targetToken=None):
	try:
		userUtils.appendNotes(userID, "Username change: '{}' -> '{}'".format(userUtils.getUsername(userID), newUsername))
		userUtils.changeUsername(userID, newUsername=newUsername)
		if targetToken is not None:
			targetToken.kick("Your username has been changed to {}. Please log in again.".format(newUsername), "username_change")
	except userUtils.usernameAlreadyInUseError:
		log.rap(999, "Username change: {} is already in use!", through="Bancho")
		if targetToken is not None:
			targetToken.kick("There was a critical error while trying to change your username. Please contact a developer.", "username_change_fail")
	except userUtils.invalidUsernameError:
		log.rap(999, "Username change: {} is not a valid username!", through="Bancho")
		if targetToken is not None:
			targetToken.kick("There was a critical error while trying to change your username. Please contact a developer.", "username_change_fail")

class handler(generalPubSubHandler.generalPubSubHandler):
	def __init__(self):
		super().__init__()
		self.structure = {
			"userID": 0,
			"newUsername": ""
		}

	def handle(self, data):
		data = super().parseData(data)
		if data is None:
			return
		# Get the user's token
		targetToken = glob.tokens.getTokenFromUserID(data["userID"])
		if targetToken is None:
			# If the user is offline change username immediately
			handleUsernameChange(data["userID"], data["newUsername"])
		else:
			if targetToken.irc or (targetToken.actionID != actions.PLAYING and targetToken.actionID != actions.MULTIPLAYING):
				# If the user is online and he's connected through IRC or he's not playing,
				# change username and kick the user immediately
				handleUsernameChange(data["userID"], data["newUsername"], targetToken)
			else:
				# If the user is playing, delay the username change until he submits the score
				# On submit modular, lets will send the username change request again
				# through redis once the score has been submitted
				# The check is performed on bancho logout too, so if the user disconnects
				# without submitting a score, the username gets changed on bancho logout
				glob.redis.set("ripple:change_username_pending:{}".format(data["userID"]), data["newUsername"])