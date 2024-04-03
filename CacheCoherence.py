import numpy as np
import sys

numOfProcessor = 4 #Number of processors
cacheSize = 512 #Cache size
blockSize = 4 #Block size
n = cacheSize / blockSize

#argument check
if len(sys.argv) != 4: 
    print("To run - [CacheCoherence.py] [traceFileName] debugging - ['no', 'yes'] optimisise - ['no', 'yes']")
    sys.exit(1)

#Task 2 enable check. Optimise code if specfied
optimise = False
if sys.argv[3] == "yes": 
    optimise = True

#Creation and initilising of processorsCache
if not optimise: processcorsCache = {"P" + str(i) : [[-1,-1]]*n for i in range(0, numOfProcessor)} #For task 1, processorsCache = {processor : {index of word address : [tag of word address, line state]}}.
                                                                                                   #Initilised with [-1,-1] to start which are not used
else: processcorsCache = {"P" + str(i) : {} for i in range(0, numOfProcessor)} #For task2, initilised being empty. 
                                                                               #But will become processorsCache = {processor : {word address : [When it was last used, line state]}}


directory = {} #directory = {address: [line state, sharingVector]}]

debugging = False
numberOfHits = 0.0
numberOfMisses = 0.0

#For statistics
privateAccessesCycleTime = []
remoteAccessesCycleTime = []
offChipAccessesCycleTime = []
Replacement_writebacks = 0
Coherence_writebacks = 0
Invalidations_sent = 0
cycleTimesOfAll = []

debug = -1
fileName = sys.argv[1]

#Enables debugging
if sys.argv[2] == "yes":
    debug = "debug"
    debugFileName = "debug_" + fileName
    debugFile = open(debugFileName, "wb")

#Runs through trace file    
f = open(fileName)
for line in f:
    cycleTime = 0 #Initilises cycle time

    #If debugging is enabled. Writes debugging to debugFile
    if debug == "debug": 
        #Prints out caches contents for each processor 
        if line[:-1] == 'p':
            debugFile.write("Printing out the cache contents:")
            for i in range(numOfProcessor):
                s = "\nprinting Cache content for Processor " + str(i) + "..."
                debugFile.write("\nprinting Cache content for Processor " + str(i) + "...")
                if not optimise: debugFile.write("".join([("\ncache line" + str(j) + ": tag - " + str(cc[0]) + " , line state - " + str(cc[1]))  for j, cc in enumerate(processcorsCache["P" + str(i)]) if cc[0] != -1]))
                else: 
                    pass
                    #print([cc for cc in [l for l in processcorsCache["P" + str(i)].items()]])
                    #debugFile.write(["Cache line " + str(s) + ": lru - " + str(t[0]) + " , line state - " + str(t[1]) for s, t in [cc for cc in [l for l in processcorsCache["P" + str(i)].items()]]])
            continue
        #Writes hit rate
        elif line[:-1] == 'h': 
            debugFile.write("\nPrinting out the hit rate...")
            debugFile.write("\nNumber of hits is " + str(numberOfHits) + ", Number of misses is " + str(numberOfMisses))
            debugFile.write("\nHit rate is " + str(numberOfHits/numberOfMisses))
            continue
        #Turns on or off line-by-line explanation
        elif line[:-1] == 'v': 
            if debugging: 
                debugFile.write("-------switch off line-by-line explanation-------\n")
                debugging = False
            else: 
                debugFile.write("\n-------switch on line-by-line explanation-------\n")
                debugging = True
            continue
        #Writes normal line
        else: debugFile.write(line + "\n")

    #Skips line if debugging options are in trace file but debugging isn't available
    elif line[:-1] == 'h' or line[:-1] == 'p' or line[:-1] == 'v': continue

    line = line[:-1].split(' ') 
    debuggingOuput = ""

    #If new word address is seen, add to directory.
    if line[2] not in directory: directory[line[2]] = ["NOT_CACHED", [0]*numOfProcessor]
    
    cycleTime += 1 #Probing local cache to match tag and check the state 

    #Index and tag of a word address in a directed mapped cache
    index = int(line[2]) % n #
    tag = int(int(line[2])/n)

    if not optimise:
        #Checks if word address is in processor's cache and replaces it if it isn't
        if processcorsCache[line[0]][index][0] != tag: 
            if processcorsCache[line[0]][index][1] == "MODIFIED": Replacement_writebacks += 1
            processcorsCache[line[0]][index] = [tag, "INVALID"]
    else:
        #Changes tag and index for LRU cache in Task 2 
        index = line[2] #tag = word address
        tag = len(processcorsCache[line[0]]) #Set tag to most recently used
        #When cache is full
        if len(processcorsCache[line[0]]) == n:
            yes = True
            for addr in processcorsCache[line[0]].keys():
                if processcorsCache[line[0]][addr][0] == 0:
                    if processcorsCache[line[0]][addr][1] == "MODIFIED": Replacement_writebacks += 1
                    processcorsCache[line[0]].pop(addr)
                    processcorsCache[line[0]] = {k : [v[0] - 1, v[1]] for k, v in processcorsCache[line[0]].items()}
                    break

            processcorsCache[line[0]][index] = [tag-1, "INVALID"]
        #Adds address word if not in cache and not full
        elif index not in processcorsCache[line[0]]:
            processcorsCache[line[0]][index] = [tag, "INVALID"]
        #Updates word address to most recently used if word address is in cache
        else: 
            processcorsCache[line[0]] = {k : [v[0] - 1, v[1]] if v[0] > processcorsCache[line[0]][index][0] else [v[0], v[1]] for k, v in processcorsCache[line[0]].items()}
            processcorsCache[line[0]][index][0] = tag - 1

    #When is a read line
    if line[1] == "R":
        cacheState = processcorsCache[line[0]][index][1] #Gets word address's cache state 
        debuggingOuput += "A read by processor " + line[0] + " to word " + line[2] + " looked for tag " + str(tag) + " in cacheline/block " + str(index) + " , was found in state "
        if cacheState == "INVALID":
            debuggingOuput += "Invalid (cache miss) in this cache and "
            numberOfMisses += 1 #Adds to cache misses

            #If there is no shares, sharing vector is equal to 0
            if sum(directory[line[2]][1]) == 0:
                debuggingOuput += " wasn't found in state Shared or Modified in any other cache"
                cycleTime += 5 #Send message to directory to request data : 5 cycles
                cycleTime += 1 #Directory access : 1 cycle
                cycleTime += 15 #Directory receives data from memory after finding no on-chip sharers
                cycleTime += 5 #Directory sends data to P

                processcorsCache[line[0]][index] = [tag, "SHARED"] #Updates line state in cache to shared
                directory[line[2]][1][int(line[0][1:])] = 1 #Updates sharing vector
                directory[line[2]][0] = "SHARED" #Updates word address's line state in directory

                cycleTime += 1 #Probing local cache to change the state
                cycleTime += 1 #Reading data from local cache

                offChipAccessesCycleTime.append(cycleTime)
               
            else: 
                #When there are shares
                if directory[line[2]][0] == "SHARED":
                    sharingVector = directory[line[2]][1]

                    cycleTime += 5 #Send message to directory to request data
                    cycleTime += 1 #Directory access
                    cycleTime += 5 #Directory sends message to P (the closest sharer) to forward the line
                    cycleTime += 1 #Probe cache at P to match tag and check the state 
                    cycleTime += 1 #Access cache at P to forward line to other P 
        
                    debuggingOuput += "found in state Shared in the cache(s) of "
                    i = int(line[0][1:]) #Processor number
                    #Words backwords to find closest sharer
                    while(True):
                        i = i - 1
                        cycleTime += 3 #P sends invalidation acknowledgement and data to other P
                        if sharingVector[i % numOfProcessor] == 1: break

                    if debugging:
                        for p in range(0, numOfProcessor):
                            if sharingVector[p] == 1:
                                debuggingOuput += "P" + str(p) + ", "
        
                    debuggingOuput = debuggingOuput[:-2]
                    directory[line[2]][1][int(line[0][1:])] = 1 #Updates sharing vector
                    processcorsCache[line[0]][index] = [tag, "SHARED"] #Updates line state in cache

                    cycleTime += 1 #Probing local cache to change the state 
                    cycleTime += 1 #Reading data from local cache

                    remoteAccessesCycleTime.append(cycleTime)


                elif directory[line[2]][0] == "MODIFIED": 
                    sharingVector = directory[line[2]][1]

                    cycleTime += 5 #Send message to directory to request data
                    cycleTime += 1 #Directory access
                    cycleTime += 5 #Directory sends message to P2 to forward the line
                    cycleTime += 1 #Probe cache at P2 to match tag and check the state
                    cycleTime += 1 #Access cache at P2 to forward line to P0

                    i = int(line[0][1:]) #Processor number
                    #Find the furtherest away processor that needs to send ackowledgement and all other line states in other processors to Shared
                    while(True):
                        i = i - 1
                        cycleTime += 3 #Pi sends invalidation acknowledgement and data to other P
                        if sharingVector[i % numOfProcessor] == 1: 
                            i = i % numOfProcessor
                            if optimise: 
                                if index in processcorsCache["P" + str(i % numOfProcessor)]: processcorsCache["P" + str(i % numOfProcessor)][index][1] = "SHARED"
                            else: processcorsCache["P" + str(i % numOfProcessor)][index][1] = "SHARED"
                            debuggingOuput += "found in state Modified in the cache of P" + str(i)
                            break

                    processcorsCache[line[0]][index][1] = "SHARED" 

                    directory[line[2]][0] == "SHARED" #Updates directory line state
                    directory[line[2]][1][int(line[0][1:])] = 1 #Updates sharing vector
                    remoteAccessesCycleTime.append(cycleTime)

                    Coherence_writebacks += 1 

                    cycleTime += 1 #Probing local cache to change the state : 1 cycle
                    cycleTime += 1 #Reading data from local cache : 1 cycle
                else: print("error")

        #When line state in cache is Modified
        elif cacheState == "MODIFIED":
            debuggingOuput += "Modified (cache hit) in this cache"
            cycleTime += 1
            numberOfHits += 1
            privateAccessesCycleTime.append(cycleTime)

        #When line state in cache is Shared
        elif cacheState == "SHARED":
            debuggingOuput += "Shared (cache hit) in this cache"

            #For debugging
            if sum(directory[line[2]][1]) > 1 and debugging:
                debuggingOuput += "found in state Shared in the cache of "
                for p in range(0, numOfProcessor):
                    if sharingVector[line[2]][p] == 1:
                        debuggingOuput += "P" + str(p) + ", "
                debuggingOuput = debuggingOuput[:-2]
 
            cycleTime += 1 #Reading data from local cache 

            numberOfHits += 1
            privateAccessesCycleTime.append(cycleTime)
        else: print("error")
        

    #When line is a write
    elif line[1] == "W":
        debuggingOuput += "A write by processor " + line[0] + " to word " + line[2] + " looked for tag " + str(tag) + " in cacheline/block " + str(index) + " , was found in state "

        noSharers = [0] * numOfProcessor 
        noSharers[int(line[0][1:])] = 1

        #Check if cache hit or cache miss
        if  processcorsCache[line[0]][index][1] == "SHARED" or processcorsCache[line[0]][index][1] == "MODIFIED": numberOfHits += 1
        else: numberOfMisses += 1

        #When line state in cache is Shared
        if  processcorsCache[line[0]][index][1] == "SHARED":
            debuggingOuput += "Shared (cache hit) in this cache and "
            if sum(directory[line[2]][1]) > 1: debuggingOuput +=  "found in state(s) "
            else: debuggingOuput += "wasn't found in any other caches"
                
            #Invalidate other copies found in other processor's caches which are only shared not modified
            for i in range(numOfProcessor):
                if optimise:
                    if index in processcorsCache["P" + str(i)] and int(line[0][1:]) != i:
                        debuggingOuput += processcorsCache["P" + str(i)][index][1] + " in P" + str(i) + ", "
                        processcorsCache["P" + str(i)][index][1] = "INVALID"
                elif processcorsCache["P" + str(i)][index][0] == tag and int(line[0][1:]) != i: 
                    debuggingOuput += processcorsCache["P" + str(i)][index][1] + " in P" + str(i) + ", "
                    processcorsCache["P" + str(i)][index][1] = "INVALID"

            if debuggingOuput[-2:] == ", ": debuggingOuput == debuggingOuput[:-2]

            Invalidations_sent += sum(directory[line[2]][1]) - 1
            #Updates sharing vector
            directory[line[2]][1] = [0]*numOfProcessor 
            directory[line[2]][1][int(line[0][1:])] = 1
            processcorsCache[line[0]][index][1] = "MODIFIED" #Updates line state in Cache

            cycleTime += 5 #Send message to directory to invalidate other copies
            cycleTime += 1 #Directory access
            cycleTime += 5 #Directory responds that there are no sharers 
            cycleTime += 1 #Probing local cache to change the state
            cycleTime += 1 #Writing data to local cache

            remoteAccessesCycleTime.append(cycleTime)

        #When line state is Modified in Cache
        elif  processcorsCache[line[0]][index][1] == "MODIFIED":
            debuggingOuput += "all other caches are in state Invalid"
            cycleTime += 1
            privateAccessesCycleTime.append(cycleTime)

        #When line state in cache is Invalid but there are sharers
        elif sum(directory[line[2]][1]) > 0 and directory[line[2]][1] != noSharers : 
            if processcorsCache[line[0]][index][1] == "INVALID":
                debuggingOuput += "Invalid (cache miss) in this cache and and found in state "
                isModified = False

                #Invalidate other copies
                for i in range(0, numOfProcessor):
                    #Checks if word address's index is in other cache
                    if i != int(line[0][1:]) and index in processcorsCache["P" + str(i)]:
                        if processcorsCache["P" + str(i)][index][0] == tag or (optimise and index in processcorsCache["P" + str(i)]):
                            #If one of the other processor's caches has word address in Modified state 
                            if processcorsCache["P" + str(i)][index][1] == "MODIFIED": 
                                isModified = True
                                debuggingOuput += "Modified in the cache of P" + str(i) + ", "
                            elif processcorsCache["P" + str(i)][index][1] == "SHARED": debuggingOuput += "Shared in the cache of P" + str(i) + ", "
                            processcorsCache["P" + str(i)][index][1] = "INVALID" #Invalidate line state
                            Invalidations_sent += 1

                debuggingOuput = debuggingOuput[:-2]
                        
                directory[line[2]][0] = "MODIFIED" #Updates line state in directory
                processcorsCache[line[0]][index][1] = "MODIFIED" #Updates line state in cache 

                cycleTime += 5 #Send message to directory to request data and invalidate other copies
                cycleTime += 1 #Directory access
                cycleTime += 5 #Directory sends message to P to invalidate and forward the line 
                cycleTime += 1 #Probe cache at P to match tag and check the state 
     
                if isModified: cycleTime += 1 #Access cache at P to forward line to other P 

                i = int(line[0][1:])
                t = 3 * numOfProcessor
                #Find closest sharer
                while(True):
                    i = i + 1
                    t -= 3 #P sends data to other P0
                    if directory[line[2]][1][i % numOfProcessor] == 1: break
                cycleTime += t
                #Checks if overlapping is possible which would reduce latenecy time 
                #Probe cache at P to match tag and check the state : 0 cycles (latency is overlapped) when there is a further away processor
                if sum(directory[line[2]][1]) >= 2 and directory[line[2]][1][int(line[0][1:])] != 1: pass
                elif sum(directory[line[2]][1]) > 3: pass
                elif not isModified: cycleTime += 1 #Probe cache at P to match tag and check the state 


                cycleTime += 1 #Probing local cache to change the state 
                cycleTime += 1 #Writing data to local cache
                
                Invalidations_sent += sum(directory[line[2]][1])
                #Updates directory sharing vector so only sharing is processor that was just written to 
                directory[line[2]][1] = [0] * numOfProcessor 
                directory[line[2]][1][int(line[0][1:])] = 1

                remoteAccessesCycleTime.append(cycleTime)

            else: print("error")

        else: 
            #When line state in cache is Invalid
            if processcorsCache[line[0]][index][1] == "INVALID":
                debuggingOuput += "Invalid (cache miss) in this cache"

                #Updates directory. Already checker and there is no sharers to no need to Invalidate other copies
                directory[line[2]][1] = [0]*numOfProcessor
                directory[line[2]][1][int(line[0][1:])] = 1
                directory[line[2]][0] = "MODIFIED"
                processcorsCache[line[0]][index][1] = "MODIFIED" #Updated line state in cache
        
                cycleTime += 5 #Send message to directory to request data : 5 cycles
                cycleTime += 1 #Directory access : 1 cycle
                cycleTime += 15 #Directory receives data from memory after finding no on-chip sharers
                cycleTime += 5 #Directory sends data to P
                cycleTime += 1 #Probing local cache to change the state
                cycleTime += 1 #Reading data from local cache

                offChipAccessesCycleTime.append(cycleTime)

            else: print("error")
        
    else:
        print("error")

    #Writes debug file
    if debugging:
        debugFile.write(debuggingOuput + "\n")
        debugFile.write("Latency - " + str(cycleTime) + "\n\n")
    
    cycleTimesOfAll.append(cycleTime)

#Generate statistics
stats = []
stats.append("Private-accesses: " + str(len(privateAccessesCycleTime)))
stats.append("Remote-accesses: " + str(len(remoteAccessesCycleTime)))
stats.append("Off-chip-accesses: " + str(len(offChipAccessesCycleTime)))
stats.append("Total-accesses: " + str(len(privateAccessesCycleTime) + len(remoteAccessesCycleTime) + len(offChipAccessesCycleTime)))
stats.append("Replacement-writebacks: " + str(Replacement_writebacks))
stats.append("Coherence-writebacks: " + str(Coherence_writebacks))
stats.append("Invalidations-sent: " + str(Invalidations_sent))
stats.append("Average-latency: " + str(np.mean(cycleTimesOfAll)))
stats.append("Priv-average-latency: " + str(np.mean(privateAccessesCycleTime)))
stats.append("Rem-average-latency: " + str(np.mean(remoteAccessesCycleTime)))
stats.append("Off-chip-average-latency: " + str(np.mean(offChipAccessesCycleTime)))
stats.append("Total-latency: " + str(sum(cycleTimesOfAll)))

#Write statistic file 
if optimise: fileName = "out_ " + fileName[:-4] + "_optimise.txt"
else: fileName = "out_ " + fileName
f = open(fileName, "wb")
for s in stats:
    f.write(s + "\n")
f.close()
if debug == "debug": debugFile.close()
