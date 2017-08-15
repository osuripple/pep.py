class chatFilters:
	def __init__(self, fileName="filters.txt"):
		"""
		Initialize chat filters

		:param fileName: name of the file containing filters. Default: filters.txt
		"""
		self.filters = {}
		self.loadFilters(fileName)

	def loadFilters(self, fileName="filters.txt"):
		"""
		Load filters from a file

		:param fileName: name of the file containing filters. Default: filters.txt
		:return:
		"""
		# Reset chat filters
		self.filters = {}

		# Open filters file
		with open(fileName, "r") as f:
			# Read all lines
			data = f.readlines()

			# Process each line
			for line in data:
				# Get old/new word and save it in dictionary
				lineSplit = line.split("=")
				self.filters[lineSplit[0].lower()] = lineSplit[1].replace("\n", "")

	def filterMessage(self, message):
		"""
		Replace forbidden words with filtered ones

		:param message: normal message
		:return: filtered message
		"""
		return message
		"""
		# Split words by spaces
		messageTemp = message.split(" ")

		# Check each word
		for word in messageTemp:
			lowerWord = word.lower()

			# If the word is filtered, replace it
			if lowerWord in self.filters:
				message = message.replace(word, self.filters[lowerWord])

		# Return filtered message
		return message
		"""
