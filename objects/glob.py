"""Global objects and variables"""

import time

from common.ddog import datadogClient
from common.files import fileBuffer, fileLocks
from objects import channelList
from objects import matchList
from objects import streamList
from objects import tokenList
from common.web import schiavo

try:
	with open("version") as f:
		VERSION = f.read()
	if VERSION == "":
		raise
except:
	VERSION = "¯\_(xd)_/¯"

DATADOG_PREFIX = "peppy"
application = None
db = None
conf = None
banchoConf = None
tokens = tokenList.tokenList()
channels = channelList.channelList()
matches = matchList.matchList()
restarting = False
fLocks = fileLocks.fileLocks()
fileBuffers = fileBuffer.buffersList()
schiavo = schiavo.schiavo()
dog = datadogClient.datadogClient()
verifiedCache = {}
chatFilters = None
userIDCache = {}
pool = None
ircServer = None
busyThreads = 0

debug = False
outputRequestTime = False
outputPackets = False
gzip = False
localize = False
sentry = False
irc = False

startTime = int(time.time())


streams = streamList.streamList()
