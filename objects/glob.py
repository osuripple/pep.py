"""Global objects and variables"""

from objects import tokenList
from objects import channelList
from objects import matchList
from objects import fileLocks
from objects import fileBuffer
import time

try:
	with open("version") as f:
		VERSION = f.read()
	if VERSION == "":
		raise
except:
	VERSION = "¯\_(xd)_/¯"

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
verifiedCache = {}
cloudflare = False
chatFilters = None
userIDCache = {}
pool = None
busyThreads = 0

debug = False
outputRequestTime = False
outputPackets = False
discord = False
gzip = False
localize = False
sentry = False
irc = False

startTime = int(time.time())
