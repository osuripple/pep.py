import json
from objects import glob
import bottle

@bottle.route("/api/v1/onlineUsers")
def GETApiOnlineUsers():
	statusCode = 400
	data = {"message": "unknown error"}
	try:
		# Get online users count
		data["result"] = len(glob.tokens.tokens)

		# Status code and message
		statusCode = 200
		data["message"] = "ok"
	finally:
		# Add status code to data
		data["status"] = statusCode

		# Send response
		bottle.response.status = statusCode
		bottle.response.add_header("Content-Type", "application/json")
		yield json.dumps(data)
