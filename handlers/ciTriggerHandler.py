from constants import exceptions
import json
from objects import glob
from helpers import systemHelper
from helpers import logHelper as log
import bottle

@bottle.route("/api/v1/ciTrigger")
def GETCiTrigger():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Check arguments
		if "k" not in bottle.request.query:
			raise exceptions.invalidArgumentsException()

		# Check ci key
		key = bottle.request.query["k"]
		if key != glob.conf.config["server"]["cikey"]:
			raise exceptions.invalidArgumentsException()

		log.info("Ci event triggered!!")
		systemHelper.scheduleShutdown(5, False, "A new Bancho update is available and the server will be restarted in 5 seconds. Thank you for your patience.")

		# Status code and message
		statusCode = 200
		data["message"] = "ok"
	except exceptions.invalidArgumentsException:
		statusCode = 403
		data["message"] = "invalid ci key"
	finally:
		# Add status code to data
		data["status"] = statusCode

		# Send response
		bottle.response.status = statusCode
		bottle.response.add_header("Content-Type", "application/json")
		yield json.dumps(data)
