"""Global objects and variables"""

from objects import tokenList
from objects import channelList
from objects import matchList
from objects import fileLocks

VERSION = "1.2"

db = None
conf = None
banchoConf = None
tokens = tokenList.tokenList()
channels = channelList.channelList()
matches = matchList.matchList()
restarting = False
pool = None
fLocks = fileLocks.fileLocks()


debug = False
outputRequestTime = False
outputPackets = False
discord = False
gzip = False
localize = False
