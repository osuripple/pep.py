from helpers import userHelper
from constants import serverPackets
from constants import exceptions
from objects import glob
from helpers import consoleHelper
from constants import bcolors
from helpers import locationHelper
from helpers import countryHelper
import time
from helpers import generalFunctions
import sys
import traceback
from helpers import requestHelper
from helpers import discordBotHelper
from helpers import logHelper as log
from helpers import chatHelper as chat
from constants import privileges

def handle(tornadoRequest):
	# Data to return
	responseTokenString = "ayy"
	responseData = bytes()

	# Get IP from tornado request
	requestIP = tornadoRequest.getRequestIP()

	# Avoid exceptions
	clientData = ["unknown", "unknown", "unknown", "unknown", "unknown"]
	osuVersion = "unknown"

	# Split POST body so we can get username/password/hardware data
	# 2:-3 thing is because requestData has some escape stuff that we don't need
	loginData = str(tornadoRequest.request.body)[2:-3].split("\\n")
	try:
		# If true, print error to console
		err = False

		# Make sure loginData is valid
		if len(loginData) < 3:
			raise exceptions.haxException()

		# Get HWID, MAC address and more
		# Structure (new line = "|", already split)
		# [0] osu! version
		# [1] plain mac addressed, separated by "."
		# [2] mac addresses hash set
		# [3] unique ID
		# [4] disk ID
		splitData = loginData[2].split("|")
		osuVersion = splitData[0]
		timeOffset = int(splitData[1])
		print(str(timeOffset))
		clientData = splitData[3].split(":")[:5]
		if len(clientData) < 4:
			raise exceptions.forceUpdateException()

		# Try to get the ID from username
		username = str(loginData[0])
		userID = userHelper.getID(username)

		if userID == False:
			# Invalid username
			raise exceptions.loginFailedException()
		if userHelper.checkLogin(userID, loginData[1]) == False:
			# Invalid password
			raise exceptions.loginFailedException()

		# Make sure we are not banned
		priv = userHelper.getPrivileges(userID)
		if userHelper.isBanned(userID) == True and priv & privileges.USER_PENDING_VERIFICATION == 0:
			raise exceptions.loginBannedException()

		# 2FA check
		if userHelper.check2FA(userID, requestIP) == True:
			log.warning("Need 2FA check for user {}".format(loginData[0]))
			raise exceptions.need2FAException()

		# No login errors!

		# Verify this user (if pending activation)
		firstLogin = False
		if priv & privileges.USER_PENDING_VERIFICATION > 0 or userHelper.hasVerifiedHardware(userID) == False:
			if userHelper.verifyUser(userID, clientData) == True:
				# Valid account
				log.info("Account {} verified successfully!".format(userID))
				glob.verifiedCache[str(userID)] = 1
				firstLogin = True
			else:
				# Multiaccount detected
				log.info("Account {} NOT verified!".format(userID))
				glob.verifiedCache[str(userID)] = 0
				raise exceptions.loginBannedException()


		# Save HWID in db for multiaccount detection
		hwAllowed = userHelper.logHardware(userID, clientData, firstLogin)

		# This is false only if HWID is empty
		# if HWID is banned, we get restricted so there's no
		# need to deny bancho access
		if hwAllowed == False:
			raise exceptions.haxException()

		# Log user IP
		userHelper.logIP(userID, requestIP)

		# Delete old tokens for that user and generate a new one
		glob.tokens.deleteOldTokens(userID)
		responseToken = glob.tokens.addToken(userID, requestIP, timeOffset=timeOffset)
		responseTokenString = responseToken.token

		# Check restricted mode (and eventually send message)
		responseToken.checkRestricted()

		# Set silence end UNIX time in token
		responseToken.silenceEndTime = userHelper.getSilenceEnd(userID)

		# Get only silence remaining seconds
		silenceSeconds = responseToken.getSilenceSecondsLeft()

		# Get supporter/GMT
		userGMT = False
		userSupporter = True
		if responseToken.admin == True:
			userGMT = True

		# Server restarting check
		if glob.restarting == True:
			raise exceptions.banchoRestartingException()

		# Send login notification before maintenance message
		if glob.banchoConf.config["loginNotification"] != "":
			responseToken.enqueue(serverPackets.notification(glob.banchoConf.config["loginNotification"]))

		# Maintenance check
		if glob.banchoConf.config["banchoMaintenance"] == True:
			if userGMT == False:
				# We are not mod/admin, delete token, send notification and logout
				glob.tokens.deleteToken(responseTokenString)
				raise exceptions.banchoMaintenanceException()
			else:
				# We are mod/admin, send warning notification and continue
				responseToken.enqueue(serverPackets.notification("Bancho is in maintenance mode. Only mods/admins have full access to the server.\nType !system maintenance off in chat to turn off maintenance mode."))

		# Send all needed login packets
		responseToken.enqueue(serverPackets.silenceEndTime(silenceSeconds))
		responseToken.enqueue(serverPackets.userID(userID))
		responseToken.enqueue(serverPackets.protocolVersion())
		responseToken.enqueue(serverPackets.userSupporterGMT(userSupporter, userGMT))
		responseToken.enqueue(serverPackets.userPanel(userID, True))
		responseToken.enqueue(serverPackets.userStats(userID, True))

		# Channel info end (before starting!?! wtf bancho?)
		responseToken.enqueue(serverPackets.channelInfoEnd())
		# Default opened channels
		# TODO: Configurable default channels
		chat.joinChannel(token=responseToken, channel="#osu")
		chat.joinChannel(token=responseToken, channel="#announce")

		# Join admin channel if we are an admin
		if responseToken.admin == True:
			chat.joinChannel(token=responseToken, channel="#admin")

		# Output channels info
		for key, value in glob.channels.channels.items():
			if value.publicRead == True and value.hidden == False:
				responseToken.enqueue(serverPackets.channelInfo(key))

		# Send friends list
		responseToken.enqueue(serverPackets.friendList(userID))

		# Send main menu icon
		if glob.banchoConf.config["menuIcon"] != "":
			responseToken.enqueue(serverPackets.mainMenuIcon(glob.banchoConf.config["menuIcon"]))

		# Send online users IDs array
		responseToken.enqueue(serverPackets.onlineUsers())

		# Get location and country from ip.zxq.co or database
		if glob.localize == True:
			# Get location and country from IP
			location = locationHelper.getLocation(requestIP)
			countryLetters = locationHelper.getCountry(requestIP)
			country = countryHelper.getCountryID(countryLetters)
		else:
			# Set location to 0,0 and get country from db
			log.warning("Location skipped")
			location = [0,0]
			countryLetters = "XX"
			country = countryHelper.getCountryID(userHelper.getCountry(userID))

		# Set location and country
		responseToken.setLocation(location)
		responseToken.setCountry(country)

		# Set country in db if user has no country (first bancho login)
		if userHelper.getCountry(userID) == "XX":
			userHelper.setCountry(userID, countryLetters)

		# Send to everyone our userpanel if we are not restricted
		if responseToken.restricted == False:
			glob.tokens.enqueueAll(serverPackets.userPanel(userID))

		# Set reponse data to right value and reset our queue
		responseData = responseToken.queue
		responseToken.resetQueue()
	except exceptions.loginFailedException:
		# Login failed error packet
		# (we don't use enqueue because we don't have a token since login has failed)
		err = True
		responseData += serverPackets.loginFailed()
	except exceptions.haxException:
		# Invalid POST data
		# (we don't use enqueue because we don't have a token since login has failed)
		err = True
		responseData += serverPackets.loginFailed()
		responseData += serverPackets.notification("I see what you're doing...")
	except exceptions.loginBannedException:
		# Login banned error packet
		err = True
		responseData += serverPackets.loginBanned()
	except exceptions.banchoMaintenanceException:
		# Bancho is in maintenance mode
		responseData = responseToken.queue
		responseData += serverPackets.notification("Our bancho server is in maintenance mode. Please try to login again later.")
		responseData += serverPackets.loginFailed()
	except exceptions.banchoRestartingException:
		# Bancho is restarting
		responseData += serverPackets.notification("Bancho is restarting. Try again in a few minutes.")
		responseData += serverPackets.loginFailed()
	except exceptions.need2FAException:
		# User tried to log in from unknown IP
		responseData += serverPackets.needVerification()
	except exceptions.haxException:
		# Using oldoldold client, we don't have client data. Force update.
		# (we don't use enqueue because we don't have a token since login has failed)
		err = True
		responseData += serverPackets.forceUpdate()
		responseData += serverPackets.notification("Hory shitto, your client is TOO old! Nice preistoria! Please turn off the switcher and update it.")
	except:
		log.error("Unknown error!\n```\n{}\n{}```".format(sys.exc_info(), traceback.format_exc()))
	finally:
		# Console and discord log
		if len(loginData) < 3:
			msg = "Invalid bancho login request from **{}** (insufficient POST data)".format(requestIP)
		else:
			msg = "Bancho login request from **{}** for user **{}** ({})".format(requestIP, loginData[0], "failed" if err == True else "success")
		log.info(msg, "bunker")

		# Return token string and data
		return (responseTokenString, responseData)