from objects import glob

def getRequestIP(bottleRequest):
	realIP = bottleRequest.headers.get("X-Forwarded-For") if glob.cloudflare == True else bottleRequest.headers.get("X-Real-IP")
	if realIP != None:
		return realIP
	return bottleRequest.environ.get("REMOTE_ADDR")