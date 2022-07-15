from binary import BinaryStream
import sys, os, struct
import simplejson as json

# This function allows us to take X amount of bytes from a string
def takeBytes(self, len, skip=False):
    arr = []
    if skip: # Should we skip bytes?
        for i in range(skip, skip + len): # Loop through the bytes we want
            arr.append(struct.pack("B", self[i])) # Append the bytes into the array
        return arr # Return the array
    else:
        for i in range(len): # Loop through the bytes we want
            arr.append(struct.pack("B", self[i])) # Append them properly to the array
        return arr # Return the array

# Thanks to grappiegovert for help with calculating the padding and end of strings.
# This calculates the offset of the string from the start of the file
def offsetOfString(values, curValue):
    offset = 0
    for i in range(curValue): # Loop through until we reach our value
        offset += 4 + len(values[i]) + 1 # 4 is the Int32 for the length and then it's the length of the value including the null byte
        offset += (4 - (len(values[i]) + 1) % 4) % 4 # Adds the padding length on
    return offset

# This decodes a list into a string
def decodeList(list):
    str = ""
    for x in list: # Loop through list 
        str += x.hex() # Concat the hex of the string
    return str

def readBLOBS(self):
    with open(self.file, "rb") as file:
        stream = BinaryStream(file)
        # Gets number of entries in the file
        stream.seek(self.endOfStrings + 24) # This goes to where the number of entries is stored
        noOfEntries = stream.readInt32() # Reads the integer

        # Gets the offsets for where hashes are stored
        offsets = [] # Array to store the offsets
        for i in range(noOfEntries): # This runs through and gathers all offsets
            offsets.append(stream.readInt32()) # This reads the integer stored at the position

        ORESArr = {} # Dictionary to store the hashes and data
        ORESArr["_comment"] = "BLOBS - DO NOT REMOVE, CHANGE OR MOVE THIS LINE!"
        
        for i in range(3, noOfEntries): # First 3 offsets are not valid so we skip.
            # Get the offset of the data
            stream.seek(offsets[i] + 16) # This goes to the start of the offset where the data is stored for this hash
            offsetOfData = stream.readInt32() # Reads the integer stored here

            # Get the hash
            stream.seek(4, "current") # This skips past the 4 null bytes
            hashBytes = stream.readBytes(8) # This reads the 8 bytes which makes up the hash
            hash = decodeList(takeBytes(hashBytes, 4)[::-1] + takeBytes(hashBytes, 4, 4)[::-1]).upper() # This takes the first 4 bytes and flips them and does the same for the last 4
            
            # Get the data
            stream.seek(offsetOfData + 12) # This goes to the where the length of the string is stored
            lengthOfString = stream.readInt32() - 1 # This gets reads the length of the string (-1 because there is a null byte)
            data = stream.readBytes(lengthOfString).decode("utf-8") # This reads the bytes that make up the data and decodes to it to utf-8
            ORESArr[hash] = data # This adds it to the dictionary "hash": "data"

        return [ORESArr, noOfEntries]

def writeBLOBS(self):
    with open(self.file, "r") as jsonFile: # Loads in the JSON file
        jsonData = json.loads(jsonFile.read()) # Parses the JSON
        jsonData.pop("_comment") # Removes the comment
        hashes = list(jsonData.keys()) # Gets the hashes from the JSON file
        values = list(jsonData.values()) # Gets the values from the JSON file
        startOfStrings = 0x30 + 0x18 * len(values) # 0x30 - offset from top of the file | 0x18 - block size when storing hashes | len(values) - number of values
        endOfStrings = startOfStrings + offsetOfString(values, len(values)) # Calculates where the end of strings are
        endOfStrings -= (4 - (len(values[-1]) + 1) % 4) % 4
        
        with open(self.file.upper().replace(".JSON", ""), "wb") as file:
            # Writes the start of the file
            stream = BinaryStream(file) # Starts a binary stream
            stream.writeBytes(b"\x42\x49\x4E\x31\x00\x08\x01\x00") # Writes BIN1 header
            stream.writeInt32(endOfStrings - 0x10, True) # Writes where the list of hashes will end
            stream.writeBytes(b"\x00\x00\x00\x00\x20\x00\x00\x00\x00\x00\x00\x00") # Writes rest of header
            stream.writeInt32(startOfStrings - 0x10) # Writes the offset for start of strings
            stream.writeBytes(b"\x00\x00\x00\x00") # Writes padding
            stream.writeInt32(startOfStrings - 0x10) # Writes the offset for start of strings
            stream.writeBytes(b"\x00\x00\x00\x00\x00\x00\x00\x00") # Write padding
            stream.writeInt32(len(values)) # Writes how many values are in the file

            # Write hashes to file
            for i in range(len(values)): # Iterate through all values
                stream.writeInt32(len(values[i])) # Write how long the value is
                stream.seek(-1, "current") # Curse you python for not having Int24 readily available!
                stream.writeBytes(b"\x40\x00\x00\x00\x00") # Writes some padding
                stream.writeInt32(startOfStrings - 12 + offsetOfString(values, i)) # Calculates the offset for the value
                stream.writeBytes(b"\x00\x00\x00\x00") # Writes some padding
                hash = bytearray.fromhex(hashes[i]) # Converts the hash into a byte array we can easily manipulate
                stream.writeBytes(b"".join(takeBytes(hash, 4)[::-1] + takeBytes(hash, 4, 4)[::-1])) # This takes the first 4 bytes and flips them and does the same for the last 4

            # Write values to file
            for i in range(len(values)): # Iterate through all values again
                value = values[i] # Get the actual value
                stream.writeInt32(len(value) + 1) # Writes the length of the value (+1 for the extra null byte)
                stream.writeBytes(value.encode("utf-8")) # Encodes the value as hex from UTF-8 and writes it
                stream.writeBytes(b"\x00") # Adds the extra null byte
                if(i != len(values) - 1): # If it's not the final value
                    stream.writeBytes((b"\x00" * ((4 - (len(value) + 1) % 4) % 4))) # Writes padding | calculates how much padding we need
            
            # Write the final parts before the pointer table
            stream.writeBytes(b"\xED\xA5\xEB\x12") # Write the ORES signature (magic)
            stream.writeInt32(4 + (len(values) + 3) * 4) # (length + 3) because of the 3 invalid offsets
            stream.writeInt32(len(values) + 3) # Writes number of values (+3 to account for invalid offsets)
            stream.writeBytes(b"\x00\x00\x00\x00\x08\x00\x00\x00\x10\x00\x00\x00") # Writes first 3 invalid offsets

            # Write pointer table
            for i in range(len(values)): # Loops through all values
                stream.writeInt32(40 + i * 24) # Writes pointer to value

            return True



# Thank you to Atampy26 for parts of the reading and writing below
def readJSON(self):
    with open(sys.argv[1], "rb") as file:
        outData = file.read()[36:-17]
        return [outData, "UNLOCKABLES"]

def writeJSON(self):
    with open(self.file, "r") as jsonFile: # Loads in the JSON file
        jsonData = json.loads(jsonFile.read()) # Parses the JSON
        jsonData.pop(0) # Removes the comment
        jsonData = bytes(json.dumps(jsonData, separators=(',', ':')), "UTF-8")
        jsonLength = len(jsonData)
        size1Value = str(hex(jsonLength + 21))[2:].zfill(8)
        size2Value = str(hex(jsonLength | 0x40000000))[2:].zfill(8)
        size3Value = str(hex(jsonLength + 1))[2:].zfill(8)
        size2Value = size2Value[6:8] + size2Value[4:6] + size2Value[2:4] + size2Value[0:2]
        size3Value = size3Value[6:8] + size3Value[4:6] + size3Value[2:4] + size3Value[0:2]
        
        with open(self.file[:-5],"wb") as file2:
            file2.write(b'\x42\x49\x4E\x31\x00\x08\x01\x00')
            file2.write(bytes.fromhex(size1Value))
            file2.write(b'\x00\x00\x00\x00')
            file2.write(bytes.fromhex(size2Value))
            file2.write(b'\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00')
            file2.write(bytes.fromhex(size3Value))
            file2.write(jsonData)
            file2.write(b'\x00\xED\xA5\xEB\x12\x08\x00\x00\x00\x01\x00\x00\x00\x08\x00\x00\x00')

            return True

class ORES:
    def __init__(self, file):
        self.file = file
        self.endOfStrings = None
        self.type = "UNKNOWN"

    def check(self):
        with open(self.file, "rb") as file:
            stream = BinaryStream(file)
            if stream.readBytes(4) != b"BIN1":  # Reads first 4 bytes to check header
                print("File is not a valid BIN1 file!")
                sys.exit(2)
            
            # Check ORES signature
            stream.seek(8) # This says where the end of strings are
            endOfStrings = stream.readInt32(True) # Reads where end of strings are (True indicates Big endian)
            stream.seek(endOfStrings + 4, "current") # Reads here for the signature that is always here
            if (b"\xED\xA5\xEB\x12" != stream.readBytes(4)): # This is always the same on ORES files!
                print("File is not a valid ORES file!")
                sys.exit(2)

            self.endOfStrings = endOfStrings

            return True

    def identify(self):
        if (not self.endOfStrings):
            self.check()

        with open(self.file, "rb") as file:
            stream = BinaryStream(file)
            stream.seek(36)
            identifier = stream.readBytes(1)
            
            if (identifier ==  b"["):
                self.type = "JSON"
            elif (identifier == b"\x00"):
                self.type = "BLOBS"
            else:
                self.type = "UNKNOWN"

            return self.type

    def read(self):
        if (self.type == "UNKNOWN"):
            self.identify()

        if (self.type == "UNKNOWN"):
            print("Unknown ORES type, please make sure it is the correct file!")
            sys.exit(2)

        if (self.type == "JSON"):
            return readJSON(self)
        elif (self.type == "BLOBS"):
            return readBLOBS(self)

    def write(self):
        try:
            with open(self.file, "r") as file:
                testJSON = json.loads(file.read())
                if type(testJSON) is dict:
                    if (testJSON["_comment"].startswith("BLOBS")):
                        return writeBLOBS(self)
                    else:
                        print("Unknown ORES type. Please make sure the comment at the top of the file is intact.")
                        sys.exit(2)
                elif type(testJSON) is list:
                    if (testJSON[0]["_comment"].startswith("UNLOCKABLES")):
                        return writeJSON(self)
                    else:
                        print("Unknown ORES type. Please make sure the comment at the top of the file is intact.")
                        sys.exit(2)
                else:
                    print("Unknown ORES type. Please make sure the comment at the top of the file is intact.")
                    sys.exit(2)
        except ValueError as e:
            print("Invalid JSON, please make sure it is the correct file!")
            sys.exit(2)
