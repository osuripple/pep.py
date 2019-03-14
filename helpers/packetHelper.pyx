import struct
from constants import dataTypes

cpdef bytearray uleb128Encode(int num):
	"""
	Encode an int to uleb128

	:param num: int to encode
	:return: bytearray with encoded number
	"""
	cdef bytearray arr = bytearray()
	cdef int length = 0

	if num == 0:
		return bytearray(b"\x00")

	while num > 0:
		arr.append(num & 127)
		num >>= 7
		if num != 0:
			arr[length] |= 128
		length+=1

	return arr

cpdef list uleb128Decode(bytes num):
	"""
	Decode a uleb128 to int

	:param num: encoded uleb128 int
	:return: (total, length)
	"""
	cdef int shift = 0
	cdef list arr = [0,0]	#total, length
	cdef int b

	while True:
		b = num[arr[1]]
		arr[1]+=1
		arr[0] |= int(b & 127) << shift
		if b & 128 == 0:
			break
		shift += 7

	return arr

cpdef unpackData(bytes data, int dataType):
	"""
	Unpacks a single section of a packet.

	:param data: bytes to unpack
	:param dataType: data type
	:return: unpacked bytes
	"""
	# Get right pack Type
	if dataType == dataTypes.UINT16:
		unpackType = "<H"
	elif dataType == dataTypes.SINT16:
		unpackType = "<h"
	elif dataType == dataTypes.UINT32:
		unpackType = "<L"
	elif dataType == dataTypes.SINT32:
		unpackType = "<l"
	elif dataType == dataTypes.UINT64:
		unpackType = "<Q"
	elif dataType == dataTypes.SINT64:
		unpackType = "<q"
	elif dataType == dataTypes.STRING:
		unpackType = "<s"
	elif dataType == dataTypes.FFLOAT:
		unpackType = "<f"
	else:
		unpackType = "<B"

	# Unpack
	return struct.unpack(unpackType, bytes(data))[0]

cpdef bytes packData(__data, int dataType):
	"""
	Packs a single section of a packet.

	:param __data: data to pack
	:param dataType: data type
	:return: packed bytes
	"""
	cdef bytes data = bytes()	# data to return
	cdef bint pack = True		# if True, use pack. False only with strings
	cdef str packType

	# Get right pack Type
	if dataType == dataTypes.BBYTES:
		# Bytes, do not use pack, do manually
		pack = False
		data = __data
	elif dataType == dataTypes.INT_LIST:
		# Pack manually
		pack = False
		# Add length
		data = packData(len(__data), dataTypes.UINT16)
		# Add all elements
		for i in __data:
			data += packData(i, dataTypes.SINT32)
	elif dataType == dataTypes.STRING:
		# String, do not use pack, do manually
		pack = False
		if len(__data) == 0:
			# Empty string
			data += b"\x00"
		else:
			# Non empty string
			data += b"\x0B"
			data += uleb128Encode(len(__data))
			data += str.encode(__data, "latin_1", "ignore")
	elif dataType == dataTypes.UINT16:
		packType = "<H"
	elif dataType == dataTypes.SINT16:
		packType = "<h"
	elif dataType == dataTypes.UINT32:
		packType = "<L"
	elif dataType == dataTypes.SINT32:
		packType = "<l"
	elif dataType == dataTypes.UINT64:
		packType = "<Q"
	elif dataType == dataTypes.SINT64:
		packType = "<q"
	elif dataType == dataTypes.STRING:
		packType = "<s"
	elif dataType == dataTypes.FFLOAT:
		packType = "<f"
	else:
		packType = "<B"

	# Pack if needed
	if pack:
		data += struct.pack(packType, __data)

	return data

cpdef bytes buildPacket(int __packet, list __packetData = None):
	"""
	Builds a packet

	:param __packet: packet ID
	:param __packetData: packet structure [[data, dataType], [data, dataType], ...]
	:return: packet bytes
	"""
	# Default argument
	if __packetData is None:
		__packetData = []
	# Set some variables
	cdef bytes packetData = bytes()
	cdef int packetLength = 0
	cdef bytes packetBytes = bytes()

	# Pack packet data
	cdef list i
	for i in __packetData:
		packetData += packData(i[0], i[1])

	# Set packet length
	packetLength = len(packetData)

	# Return packet as bytes
	packetBytes += struct.pack("<h", __packet)		# packet id (int16)
	packetBytes += bytes(b"\x00")					# unused byte
	packetBytes += struct.pack("<l", packetLength)	# packet lenght (iint32)
	packetBytes += packetData						# packet data
	return packetBytes

cpdef int readPacketID(bytes stream):
	"""
	Read packetID (first two bytes) from a packet

	:param stream: packet bytes
	:return: packet ID
	"""
	return unpackData(stream[0:2], dataTypes.UINT16)

cpdef int readPacketLength(bytes stream):
	"""
	Read packet data length (3:7 bytes) from a packet

	:param stream: packet bytes
	:return: packet data length
	"""
	return unpackData(stream[3:7], dataTypes.UINT32)


cpdef readPacketData(bytes stream, list structure=None, bint hasFirstBytes = True):
	"""
	Read packet data from `stream` according to `structure`
	:param stream: packet bytes
	:param structure: packet structure: [[name, dataType], [name, dataType], ...]
	:param hasFirstBytes: 	if True, `stream` has packetID and length bytes.
							if False, `stream` has only packet data. Default: True
	:return: {name: unpackedValue, ...}
	"""
	# Default list argument
	if structure is None:
		structure = []

	# Read packet ID (first 2 bytes)
	cdef dict data = {}

	# Skip packet ID and packet length if needed
	cdef start, end
	if hasFirstBytes:
		end = 7
		start = 7
	else:
		end = 0
		start = 0

	# Read packet
	cdef list i
	cdef bint unpack
	for i in structure:
		start = end
		unpack = True
		if i[1] == dataTypes.INT_LIST:
			# sInt32 list.
			# Unpack manually with for loop
			unpack = False

			# Read length (uInt16)
			length = unpackData(stream[start:start+2], dataTypes.UINT16)

			# Read all int inside list
			data[i[0]] = []
			for j in range(0,length):
				data[i[0]].append(unpackData(stream[start+2+(4*j):start+2+(4*(j+1))], dataTypes.SINT32))

			# Update end
			end = start+2+(4*length)
		elif i[1] == dataTypes.STRING:
			# String, don't unpack
			unpack = False

			# Check empty string
			if stream[start] == 0:
				# Empty string
				data[i[0]] = ""
				end = start+1
			else:
				# Non empty string
				# Read length and calculate end
				length = uleb128Decode(stream[start+1:])
				end = start+length[0]+length[1]+1

				# Read bytes
				#data[i[0]] = ''.join(chr(j) for j in stream[start+1+length[1]:end])
				data[i[0]] = ""
				for j in stream[start+1+length[1]:end]:
					data[i[0]] += chr(j)
		elif i[1] == dataTypes.BYTE:
			end = start+1
		elif i[1] in (dataTypes.UINT16, dataTypes.SINT16):
			end = start+2
		elif i[1] in (dataTypes.UINT32, dataTypes.SINT32, dataTypes.FFLOAT):
			end = start+4
		elif i[1] in (dataTypes.UINT64, dataTypes.SINT64):
			end = start+8

		# Unpack if needed
		if unpack:
			data[i[0]] = unpackData(stream[start:end], i[1])

	return data
