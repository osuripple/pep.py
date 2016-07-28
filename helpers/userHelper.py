from helpers import passwordHelper
from constants import gameModes
from helpers import generalFunctions
from objects import glob
from helpers import logHelper as log
import time
from constants import privileges

def getID(username):
	"""
	Get username's user ID

	db -- database connection
	username -- user
	return -- user id or False
	"""

	# Get user ID from db
	userID = glob.db.fetch("SELECT id FROM users WHERE username = %s", [username])

	# Make sure the query returned something
	if userID == None:
		return False

	# Return user ID
	return userID["id"]


def checkLogin(userID, password):
	"""
	Check userID's login with specified password

	db -- database connection
	userID -- user id
	password -- plain md5 password
	return -- True or False
	"""

	# Get password data
	passwordData = glob.db.fetch("SELECT password_md5, salt, password_version FROM users WHERE id = %s", [userID])

	# Make sure the query returned something
	if passwordData == None:
		return False


	# Return valid/invalid based on the password version.
	if passwordData["password_version"] == 2:
		return passwordHelper.checkNewPassword(password, passwordData["password_md5"])
	if passwordData["password_version"] == 1:
		ok = passwordHelper.checkOldPassword(password, passwordData["salt"], passwordData["password_md5"])
		if not ok: return False
		newpass = passwordHelper.genBcrypt(password)
		glob.db.execute("UPDATE users SET password_md5=%s, salt='', password_version='2' WHERE id = %s", [newpass, userID])


def exists(userID):
	"""
	Check if userID exists

	userID -- user ID to check
	return -- bool
	"""

	result = glob.db.fetch("SELECT id FROM users WHERE id = %s", [userID])
	if result == None:
		return False
	else:
		return True

def getSilenceEnd(userID):
	"""
	Get userID's **ABSOLUTE** silence end UNIX time
	Remember to subtract time.time() to get the actual silence time

	userID -- userID
	return -- UNIX time
	"""

	return glob.db.fetch("SELECT silence_end FROM users WHERE id = %s", [userID])["silence_end"]


def silence(userID, seconds, silenceReason, author = 999):
	"""
	Silence someone

	userID -- userID
	seconds -- silence length in seconds
	silenceReason -- Silence reason shown on website
	author -- userID of who silenced the user. Default: 999
	"""
	# db qurey
	silenceEndTime = int(time.time())+seconds
	glob.db.execute("UPDATE users SET silence_end = %s, silence_reason = %s WHERE id = %s", [silenceEndTime, silenceReason, userID])

	# Loh
	targetUsername = getUsername(userID)
	# TODO: exists check im drunk rn i need to sleep (stampa piede ubriaco confirmed)
	if seconds > 0:
		log.rap(author, "has silenced {} for {} seconds for the following reason: \"{}\"".format(targetUsername, seconds, silenceReason), True)
	else:
		log.rap(author, "has removed {}'s silence".format(targetUsername), True)

def getRankedScore(userID, gameMode):
	"""
	Get userID's ranked score relative to gameMode

	userID -- userID
	gameMode -- int value, see gameModes
	return -- ranked score
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	return glob.db.fetch("SELECT ranked_score_"+modeForDB+" FROM users_stats WHERE id = %s", [userID])["ranked_score_"+modeForDB]


def getTotalScore(userID, gameMode):
	"""
	Get userID's total score relative to gameMode

	userID -- userID
	gameMode -- int value, see gameModes
	return -- total score
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	return glob.db.fetch("SELECT total_score_"+modeForDB+" FROM users_stats WHERE id = %s", [userID])["total_score_"+modeForDB]


def getAccuracy(userID, gameMode):
	"""
	Get userID's average accuracy relative to gameMode

	userID -- userID
	gameMode -- int value, see gameModes
	return -- accuracy
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	return glob.db.fetch("SELECT avg_accuracy_"+modeForDB+" FROM users_stats WHERE id = %s", [userID])["avg_accuracy_"+modeForDB]


def getGameRank(userID, gameMode):
	"""
	Get userID's **in-game rank** (eg: #1337) relative to gameMode

	userID -- userID
	gameMode -- int value, see gameModes
	return -- game rank
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	result = glob.db.fetch("SELECT position FROM leaderboard_"+modeForDB+" WHERE user = %s", [userID])
	if result == None:
		return 0
	else:
		return result["position"]


def getPlaycount(userID, gameMode):
	"""
	Get userID's playcount relative to gameMode

	userID -- userID
	gameMode -- int value, see gameModes
	return -- playcount
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	return glob.db.fetch("SELECT playcount_"+modeForDB+" FROM users_stats WHERE id = %s", [userID])["playcount_"+modeForDB]


def getUsername(userID):
	"""
	Get userID's username

	userID -- userID
	return -- username
	"""

	return glob.db.fetch("SELECT username FROM users WHERE id = %s", [userID])["username"]


def getFriendList(userID):
	"""
	Get userID's friendlist

	userID -- userID
	return -- list with friends userIDs. [0] if no friends.
	"""

	# Get friends from db
	friends = glob.db.fetchAll("SELECT user2 FROM users_relationships WHERE user1 = %s", [userID])

	if friends == None or len(friends) == 0:
		# We have no friends, return 0 list
		return [0]
	else:
		# Get only friends
		friends = [i["user2"] for i in friends]

		# Return friend IDs
		return friends


def addFriend(userID, friendID):
	"""
	Add friendID to userID's friend list

	userID -- user
	friendID -- new friend
	"""

	# Make sure we aren't adding us to our friends
	if userID == friendID:
		return

	# check user isn't already a friend of ours
	if glob.db.fetch("SELECT id FROM users_relationships WHERE user1 = %s AND user2 = %s", [userID, friendID]) != None:
		return

	# Set new value
	glob.db.execute("INSERT INTO users_relationships (user1, user2) VALUES (%s, %s)", [userID, friendID])


def removeFriend(userID, friendID):
	"""
	Remove friendID from userID's friend list

	userID -- user
	friendID -- old friend
	"""

	# Delete user relationship. We don't need to check if the relationship was there, because who gives a shit,
	# if they were not friends and they don't want to be anymore, be it. ¯\_(ツ)_/¯
	glob.db.execute("DELETE FROM users_relationships WHERE user1 = %s AND user2 = %s", [userID, friendID])


def getCountry(userID):
	"""
	Get userID's country **(two letters)**.
	Use countryHelper.getCountryID with what that function returns
	to get osu! country ID relative to that user

	userID -- user
	return -- country code (two letters)
	"""

	return glob.db.fetch("SELECT country FROM users_stats WHERE id = %s", [userID])["country"]

def getPP(userID, gameMode):
	"""
	Get userID's PP relative to gameMode

	userID -- user
	return -- PP
	"""

	modeForDB = gameModes.getGameModeForDB(gameMode)
	return glob.db.fetch("SELECT pp_{} FROM users_stats WHERE id = %s".format(modeForDB), [userID])["pp_{}".format(modeForDB)]

def setCountry(userID, country):
	"""
	Set userID's country (two letters)

	userID -- userID
	country -- country letters
	"""
	glob.db.execute("UPDATE users_stats SET country = %s WHERE id = %s", [country, userID])

def getShowCountry(userID):
	"""
	Get userID's show country status

	userID -- userID
	return -- True if country is shown, False if it's hidden
	"""
	country = glob.db.fetch("SELECT show_country FROM users_stats WHERE id = %s", [userID])
	if country == None:
		return False
	return generalFunctions.stringToBool(country)

def logIP(userID, ip):
	"""
	User IP log
	USED FOR MULTIACCOUNT DETECTION
	"""
	glob.db.execute("""INSERT INTO ip_user (userid, ip, occurencies) VALUES (%s, %s, '1')
						ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""", [userID, ip])

def saveBanchoSession(userID, ip):
	"""
	Save userid and ip of this token in bancho_sessions table.
	Used to cache logins on LETS requests
	"""
	log.debug("Saving bancho session ({}::{}) in db".format(userID, ip))
	glob.db.execute("INSERT INTO bancho_sessions (id, userid, ip) VALUES (NULL, %s, %s)", [userID, ip])

def deleteBanchoSessions(userID, ip):
	"""Delete this bancho session from DB"""
	log.debug("Deleting bancho session ({}::{}) from db".format(userID, ip))
	try:
		glob.db.execute("DELETE FROM bancho_sessions WHERE userid = %s AND ip = %s", [userID, ip])
	except:
		log.warning("Token for user: {} ip: {} doesn't exist".format(userID, ip))

def is2FAEnabled(userID):
	"""Returns True if 2FA is enable for this account"""
	result = glob.db.fetch("SELECT id FROM 2fa_telegram WHERE userid = %s LIMIT 1", [userID])
	return True if result is not None else False

def check2FA(userID, ip):
	"""Returns True if this IP is untrusted"""
	if is2FAEnabled(userID) == False:
		return False

	result = glob.db.fetch("SELECT id FROM ip_user WHERE userid = %s AND ip = %s", [userID, ip])
	return True if result is None else False

def getUserStats(userID, gameMode):
	"""
	Get all user stats relative to gameMode with only two queries

	userID --
	gameMode -- gameMode number
	return -- dictionary with results
	"""
	modeForDB = gameModes.getGameModeForDB(gameMode)

	# Get stats
	stats = glob.db.fetch("""SELECT
						ranked_score_{gm} AS rankedScore,
						avg_accuracy_{gm} AS accuracy,
						playcount_{gm} AS playcount,
						total_score_{gm} AS totalScore,
						pp_{gm} AS pp
						FROM users_stats WHERE id = %s LIMIT 1""".format(gm=modeForDB), [userID])

	# Get game rank
	result = glob.db.fetch("SELECT position FROM leaderboard_{} WHERE user = %s LIMIT 1".format(modeForDB), [userID])
	if result == None:
		stats["gameRank"] = 0
	else:
		stats["gameRank"] = result["position"]

	# Return stats + game rank
	return stats

def isAllowed(userID):
	"""
	Check if userID is not banned or restricted

	userID -- id of the user
	return -- True if not banned or restricted, otherwise false.
	"""
	result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s", [userID])
	if result != None:
		return (result["privileges"] & privileges.USER_NORMAL) and (result["privileges"] & privileges.USER_PUBLIC)
	else:
		return False

def isRestricted(userID):
	"""
	Check if userID is restricted

	userID -- id of the user
	return -- True if not restricted, otherwise false.
	"""
	result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s", [userID])
	if result != None:
		return (result["privileges"] & privileges.USER_NORMAL) and not (result["privileges"] & privileges.USER_PUBLIC)
	else:
		return False

def isBanned(userID):
	"""
	Check if userID is banned

	userID -- id of the user
	return -- True if not banned, otherwise false.
	"""
	result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s", [userID])
	if result != None:
		return not (result["privileges"] & 3 > 0)
	else:
		return True

def ban(userID):
	"""
	Ban userID

	userID -- id of user
	"""
	banDateTime = int(time.time())
	glob.db.execute("UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s", [ ~(privileges.USER_NORMAL | privileges.USER_PUBLIC | privileges.USER_PENDING_VERIFICATION) , banDateTime, userID])

def unban(userID):
	"""
	Unban userID

	userID -- id of user
	"""
	glob.db.execute("UPDATE users SET privileges = privileges | %s, ban_datetime = 0 WHERE id = %s", [ (privileges.USER_NORMAL | privileges.USER_PUBLIC) , userID])

def restrict(userID):
	"""
	Put userID in restricted mode

	userID -- id of user
	"""
	banDateTime = int(time.time())
	glob.db.execute("UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s", [~privileges.USER_PUBLIC, banDateTime, userID])

def unrestrict(userID):
	"""
	Remove restricted mode from userID.
	Same as unban().

	userID -- id of user
	"""
	unban(userID)

def getPrivileges(userID):
	"""
	Return privileges for userID

	userID -- id of user
	return -- privileges number
	"""
	result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s", [userID])
	if result != None:
		return result["privileges"]
	else:
		return 0

def setPrivileges(userID, priv):
	"""
	Set userID's privileges in db

	userID -- id of user
	priv -- privileges number
	"""
	glob.db.execute("UPDATE users SET privileges = %s WHERE id = %s", [priv, userID])

def isInPrivilegeGroup(userID, groupName):
	groupPrivileges = glob.db.fetch("SELECT privileges FROM privileges_groups WHERE name = %s", [groupName])
	if groupPrivileges == None:
		return False
	groupPrivileges = groupPrivileges["privileges"]
	userToken = glob.tokens.getTokenFromUserID(userID)
	if userToken != None:
		userPrivileges = userToken.privileges
	else:
		userPrivileges = getPrivileges(userID)
	return (userPrivileges == groupPrivileges) or (userPrivileges == (groupPrivileges | privileges.USER_DONOR))


def appendNotes(userID, notes, addNl = True):
	"""
	Append "notes" to current userID's "notes for CM"

	userID -- id of user
	notes -- text to append
	addNl -- if True, prepend \n to notes. Optional. Default: True.
	"""
	if addNl == True:
		notes = "\n"+notes
	glob.db.execute("UPDATE users SET notes=CONCAT(COALESCE(notes, ''),%s) WHERE id = %s", [notes, userID])


def logHardware(userID, hashes, activation = False):
	"""
	Hardware log
	USED FOR MULTIACCOUNT DETECTION

	Peppy's botnet (client data) structure (new line = "|", already split)
	[0] osu! version
	[1] plain mac addressed, separated by "."
	[2] mac addresses hash set
	[3] unique ID
	[4] disk ID

	return -- True if hw is not banned, otherwise false
	"""
	# Make sure the strings are not empty
	for i in hashes[2:5]:
		if i == "":
			log.warning("Invalid hash set ({}) for user {} in HWID check".format(hashes, userID), "bunk")
			return False

	# Run some HWID checks on that user if he is not restricted
	if isRestricted(userID) == False:
		# Get username
		username = getUsername(userID)

		# Get the list of banned or restricted users that have logged in from this or similar HWID hash set
		banned = glob.db.fetchAll("""SELECT users.id as userid, hw_user.occurencies, users.username FROM hw_user
						LEFT JOIN users ON users.id = hw_user.userid
						WHERE hw_user.userid != %(userid)s
						AND (IF(%(mac)s!='b4ec3c4334a0249dae95c284ec5983df', hw_user.mac = %(mac)s, 1) AND hw_user.unique_id = %(uid)s AND hw_user.disk_id = %(diskid)s)
						AND (users.privileges & 3 != 3)""", {
							"userid": userID,
							"mac": hashes[2],
							"uid": hashes[3],
							"diskid": hashes[4],
						})

		for i in banned:
			# Get the total numbers of logins
			total = glob.db.fetch("SELECT COUNT(*) AS count FROM hw_user WHERE userid = %s LIMIT 1", [userID])
			# and make sure it is valid
			if total == None:
				continue
			total = total["count"]

			# Calculate 10% of total
			perc = (total*10)/100

			if i["occurencies"] >= perc:
				# If the banned user has logged in more than 10% of the times from this user, restrict this user
				restrict(userID)
				appendNotes(userID, "-- Logged in from HWID ({hwid}) used more than 10% from user {banned} ({bannedUserID}), who is banned/restricted.".format(
					hwid=hashes[2:5],
					banned=i["username"],
					bannedUserID=i["userid"]
				))
				log.warning("**{user}** ({userID}) has been restricted because he has logged in from HWID _({hwid})_ used more than 10% from banned/restricted user **{banned}** ({bannedUserID}), **possible multiaccount**.".format(
					user=username,
					userID=userID,
					hwid=hashes[2:5],
					banned=i["username"],
					bannedUserID=i["userid"]
				), "cm")

	# Update hash set occurencies
	glob.db.execute("""
				INSERT INTO hw_user (id, userid, mac, unique_id, disk_id, occurencies) VALUES (NULL, %s, %s, %s, %s, 1)
				ON DUPLICATE KEY UPDATE occurencies = occurencies + 1
				""", [userID, hashes[2], hashes[3], hashes[4]])

	# Optionally, set this hash as 'used for activation'
	if activation == True:
		glob.db.execute("UPDATE hw_user SET activated = 1 WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s", [userID, hashes[2], hashes[3], hashes[4]])

	# Access granted, abbiamo impiegato 3 giorni
	# We grant access even in case of login from banned HWID
	# because we call restrict() above so there's no need to deny the access.
	return True


def resetPendingFlag(userID, success=True):
	"""
	Remove pending flag from an user.

	userID -- ID of the user
	success -- if True, set USER_PUBLIC and USER_NORMAL flags too
	"""
	glob.db.execute("UPDATE users SET privileges = privileges & %s WHERE id = %s LIMIT 1", [~privileges.USER_PENDING_VERIFICATION, userID])
	if success == True:
		glob.db.execute("UPDATE users SET privileges = privileges | %s WHERE id = %s LIMIT 1", [(privileges.USER_PUBLIC | privileges.USER_NORMAL), userID])

def verifyUser(userID, hashes):
	# Check for valid hash set
	for i in hashes[2:5]:
		if i == "":
			log.warning("Invalid hash set ({}) for user {} while verifying the account".format(str(hashes), userID), "bunk")
			return False

	# Get username
	username = getUsername(userID)

	# Make sure there are no other accounts activated with this exact mac/unique id/hwid
	match = glob.db.fetchAll("SELECT userid FROM hw_user WHERE (IF(%(mac)s != 'b4ec3c4334a0249dae95c284ec5983df', mac = %(mac)s, 1) AND unique_id = %(uid)s AND disk_id = %(diskid)s) AND userid != %(userid)s AND activated = 1 LIMIT 1", {
		"mac": hashes[2],
		"uid": hashes[3],
		"diskid": hashes[4],
		"userid": userID
	})

	if match:
		# This is a multiaccount, restrict other account and ban this account

		# Get original userID and username (lowest ID)
		originalUserID = match[0]["userid"]
		originalUsername = getUsername(originalUserID)

		# Ban this user and append notes
		ban(userID)	# this removes the USER_PENDING_VERIFICATION flag too
		appendNotes(userID, "-- {}'s multiaccount ({}), found HWID match while verifying account ({})".format(originalUsername, originalUserID, hashes[2:5]))
		appendNotes(originalUserID, "-- Has created multiaccount {} ({})".format(username, userID))

		# Restrict the original
		restrict(originalUserID)

		# Discord message
		log.warning("User **{originalUsername}** ({originalUserID}) has been restricted because he has created multiaccount **{username}** ({userID}). The multiaccount has been banned.".format(
			originalUsername=originalUsername,
			originalUserID=originalUserID,
			username=username,
			userID=userID
		), "cm")

		# Disallow login
		return False
	else:
		# No matches found, set USER_PUBLIC and USER_NORMAL flags and reset USER_PENDING_VERIFICATION flag
		resetPendingFlag(userID)
		log.info("User **{}** ({}) has verified his account with hash set _{}_".format(username, userID, hashes[2:5]), "cm")

		# Allow login
		return True

def hasVerifiedHardware(userID):
	"""
	userID -- id of the user
	return -- True if hwid activation data is in db, otherwise false
	"""
	data = glob.db.fetch("SELECT id FROM hw_user WHERE userid = %s AND activated = 1 LIMIT 1", [userID])
	if data != None:
		return True
	return False
