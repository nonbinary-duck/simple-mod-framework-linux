from ORES import ORES
import simplejson as json
import sys, os

if not os.path.isfile(sys.argv[1]):
    print("File doesn't exist.")
    sys.exit(2)

if (sys.argv[1].upper().endswith(".ORES")):
    oresFile = ORES(sys.argv[1]) # Sets the ORES file path
    readORES = oresFile.read() # Read the ORES file
    oresDict = readORES[0] # Get the ores dictionary
    noOfEntries = readORES[1] # Get the number of entries (also contains info for unlockables)

    if (noOfEntries == "UNLOCKABLES"):
        with open(sys.argv[1] + ".JSON", "w") as outFile:
            jsonFile = json.loads(oresDict.decode("UTF-8"))
            jsonFile.insert(0, {"_comment": "UNLOCKABLES - DO NOT REMOVE OR MOVE THIS LINE!"})
            json.dump(jsonFile, outFile, indent=4)
            print("Exported " + sys.argv[1] + " as " + sys.argv[1] + ".JSON successfully!")
    else:
        with open(sys.argv[1] + ".JSON", "w") as outFile:
            json.dump(oresDict, outFile, indent=4)
            print("Exported " + sys.argv[1] + " as " + sys.argv[1] + ".JSON successfully!")
            print("There was " + str(noOfEntries - 3) + " entries in the file.")
elif (sys.argv[1].upper().endswith(".JSON")):
    oresFile = ORES(sys.argv[1]) # Sets the ORES file path
    writeORES = oresFile.write()

    if (writeORES):
        print("Successfully converted " + sys.argv[1] + " to " + sys.argv[1].replace(".JSON", "") + "!")
else:
    print("Usage: OREStool.exe <path to ORES/ORES.JSON file>")
    sys.exit(2)
