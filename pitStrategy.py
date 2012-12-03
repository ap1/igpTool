import argparse,csv,math,sys,os,datetime,glob,re,array,copy

# ------------------------------------------------------
#  Subroutines
# ------------------------------------------------------

# -- Fetch track info from tracks.csv
def fetchTrackInfo(args):
    rdr = csv.DictReader(open('tracks.csv'))
    
    matching_tracks = [t for t in rdr if t['name']==args.track]

    if len(matching_tracks)==1:
        track = matching_tracks[0]
        track['length']        = float(track['length'])
        track['difficulty']    = float(track['difficulty'])
        track['nlaps_default'] = int(track['nlaps_default'])
        return track
    else:
        print "Error: Search for %s returned %d matches" % (args.track,len(matching_tracks))
        sys.exit(1)

# -- Estimate fuel consumption
def estimateFuelConsumption(track):
    return 0.727 * track['length']

# -- Estimate tyre wear
def estimateTyreWear(track):
    tyreWearSoft = 0.0
    tyreWearHard = 0.0
    if   track['tyre_wear']=='vhigh':
        tyreWearSoft = -1.85 #[-0.11,  2.3]
        tyreWearHard = -0.87 #[-0.027, 1.15]
    elif track['tyre_wear']=='high':
        tyreWearSoft = -1.8  #[-0.006, 2.0]
        tyreWearHard = -0.8  #[-0.023, 1.4]
    elif track['tyre_wear']=='avg':
        tyreWearSoft = -1.54 #[-0.06,  1.92]
        tyreWearHard = -0.73 #[-0.008, 0.87]
    elif track['tyre_wear']=='low':
        tyreWearSoft = -1.2  #[-0.03,  1.59]
        tyreWearHard = -0.54 #[-0.006, 0.75]
    elif track['tyre_wear']=='vlow':
        tyreWearSoft = -1.15 #[-0.03,  1.57]
        tyreWearHard = -0.45 #[-0.008, 0.75]
    else:
        print "Error: cannot understand tyre wear '%s'" % track['tyre_wear']
        sys.exit(1)

    tyreWearHard = tyreWearHard * track['length'] #[tyreWearHard[0]*track['length'], tyreWearHard[1]*track['length']]
    tyreWearSoft = tyreWearSoft * track['length'] #[tyreWearSoft[0]*track['length'], tyreWearSoft[1]*track['length']]
    
    return tyreWearSoft, tyreWearHard

# -- How many laps will a tyre last?
def findGoodLaps(tyreWear, minGrip):
    tyre=100.0 + tyreWear*0.5
    lap =0.0
    while tyre>minGrip:
        lap = lap + 1.0
        tyre = tyre + tyreWear
        #print "%d laps: tyre %0.1f" % (lap,tyre)
    return (lap)

# -- Decode stint code
def decodeStint(stintCode, nStints):
    stintTyres = []
    myCode     = stintCode
    for i in range(0,nStints):
        curCode = myCode % 2
        myCode  = myCode / 2

        if(curCode == 0):
            stintTyres.insert(0, "soft")
        else:
            stintTyres.insert(0, "hard")

    return stintTyres

# -- print without end
def printWithoutEnd(s):
    sys.stdout.write(s)
    sys.stdout.flush()

# -- display lap list
def displayLapList(lapList):
    for l in lapList:
        if    l == 'hard': printWithoutEnd('h')
        elif  l == 'soft': printWithoutEnd('s')
        elif  l == 'pit':  printWithoutEnd('p')
    print ''

# -- pressEnterToContinue
def pressEnterToContinue():
    raw_input("Press Enter to continue...")

def getStratListRecursive(whichStop, nStops, startLap, nLaps, curPitList, stratList):
    lastLapForThisStop = (nLaps)-(nStops-whichStop)
    if(whichStop == (nStops)):
        stratList.append(curPitList)
        return
    for lap in range(startLap, lastLapForThisStop):
        nextPitList = copy.copy(curPitList)
        nextPitList[lap] = 1
        getStratListRecursive(whichStop+1, nStops, lap+2, nLaps, nextPitList, stratList)

def isFeasibleStrat(strat, tyreSequence, track, tyreWearHard, tyreWearSoft, minGrip):
    curStintIdx = 0
    curTyre     = tyreSequence[curStintIdx]
    curGrip     = 100.0

    lapGripVector = [0] * track['nlaps_default']

    if    curTyre == 'soft': curGrip = 100.0 + tyreWearSoft*0.5
    elif  curTyre == 'hard': curGrip = 100.0 + tyreWearHard*0.5

    for lap in range(1,track['nlaps_default']+1):
        
        gripBeforeLap = curGrip
        gripAfterLap  = 0

        # For this lap
        if gripBeforeLap < minGrip: return False, []

        if    curTyre == 'soft': gripAfterLap = gripBeforeLap + tyreWearSoft
        elif  curTyre == 'hard': gripAfterLap = gripBeforeLap + tyreWearHard

        gripMidLap = (gripBeforeLap + gripAfterLap) * 0.5
        lapGripVector[lap-1] = gripMidLap

        # For next lap
        if(strat[lap-1]==1):
            #if gripAfterLap > minGrip*2.0: return False, []
            curStintIdx = curStintIdx + 1
            curTyre = tyreSequence[curStintIdx]
            if    curTyre == 'soft': gripAfterLap = 100.0 + tyreWearSoft*0.5
            elif  curTyre == 'hard': gripAfterLap = 100.0 + tyreWearHard*0.5

        curGrip = gripAfterLap

    return True, lapGripVector

def predictStratTime(strat, lapGripVector, tyreSequence, track, tyreWearHard, tyreWearSoft, minGrip, fuelConsumption):
    
    fuelAtEndOfLaps = [0]*track['nlaps_default']
    fuelAtMidOfLaps = [0]*track['nlaps_default']
    lapTimeVector   = [0]*track['nlaps_default']

    for lap in range(track['nlaps_default'],0,-1):
        if(strat[lap-1]==1 or lap==(track['nlaps_default'])):
            fuelAtEndOfLaps[lap-1] = 1.0
        else:
            fuelAtEndOfLaps[lap-1] = fuelAtEndOfLaps[lap] + fuelConsumption

        fuelAtMidOfLaps[lap-1] = fuelAtEndOfLaps[lap-1] + 0.5 * fuelConsumption

    curStintIdx = 0
    totalTime   = 0.0
    for lap in range(1,track['nlaps_default']+1):

        if(strat[lap-1]==1):
            curStintIdx = curStintIdx + 1

        curFuel = fuelAtMidOfLaps[lap-1]
        curGrip = lapGripVector[lap-1]
        curTyre = tyreSequence[curStintIdx]
 
        pred_f = curFuel
        pred_s  = 0.0
        pred_h  = 0.0
        pred_Gs = 0.0
        pred_Gh = 0.0

        if(curTyre == 'soft'):
            pred_s  = 1.0
            pred_h  = 0.0
            pred_Gs = curGrip
            pred_Gh = 0.0
        elif(curTyre == 'hard'):
            pred_s  = 0.0
            pred_h  = 1.0
            pred_Gs = 0.0
            pred_Gh = curGrip
        
        normalizedLapTime = pred_s  * 16.6791497  + \
                            pred_h  * 16.829491   + \
                            pred_Gs *  0.0008001  + \
                            pred_Gh * -0.00425353 + \
                            pred_f  *  0.01900627
        
        myLapTime = normalizedLapTime * track['difficulty'] 
        myLapTime = myLapTime * track['length']

        if lap==1:
            myLapTime += 3.0
        elif (strat[lap-2]==1):
            myLapTime += 17.0

        lapTimeVector[lap-1] = myLapTime
        totalTime += myLapTime

    return totalTime, fuelAtEndOfLaps, lapTimeVector

# ------------------------------------------------------
#  Code
# ------------------------------------------------------

# -- Parser command line arguments
parser = argparse.ArgumentParser(description='Iterate on pit strategies')

parser.add_argument('-track',  metavar = 'name', type=str, help='name of track',          required=True)
parser.add_argument('-stints', metavar = 'num',  type=int, help='maximum stints to try',  default=3)
parser.add_argument('-laps',   metavar = 'num',  type=int, help='number of laps',         default=-1)

args = parser.parse_args()

track = fetchTrackInfo(args)

if(int(args.laps)>0):
    track['nlaps_default'] = args.laps

print "\n---------- Track Info ------------------"
print "%s: %0.3f kms" % (track['name'],track['length'])
print "%d laps" % (track['nlaps_default'])

fuelConsumption             = estimateFuelConsumption(track)
tyreWearSoft, tyreWearHard  = estimateTyreWear(track)

minGrip = 25.0

softGoodLaps = findGoodLaps(tyreWearSoft, minGrip)
hardGoodLaps = findGoodLaps(tyreWearHard, minGrip)

print "\n---------- Fuel Estimate ---------------"
print "%0.2f liters / lap" % fuelConsumption

print "\n---------- Tyre Estimates --------------"
print "soft tyre %0.1f per lap (good for %d laps)" % (-tyreWearSoft, softGoodLaps)
print "hard tyre %0.1f per lap (good for %d laps)" % (-tyreWearHard, hardGoodLaps)

print "\n---------- Pit Simulation --------------"

stratLapTimes = []
for curStints in range(1,args.stints+1):
    #print "Trying %d pit stop strategy..." % (curStints-1)

    stintMaxCode = int(math.pow(2,curStints))
    #print "%x" % stintMaxCode

    curPitList = [0]*track['nlaps_default']
    stratList  = []

    getStratListRecursive(0, curStints-1, 1, track['nlaps_default'], curPitList, stratList)

    numStrats = len(stratList)


    for strat in stratList:
        for stintCode in range(0,stintMaxCode):
            tyreSequence = decodeStint(stintCode, curStints)

            isFeasible, lapGripVector = isFeasibleStrat(strat, tyreSequence, track, tyreWearHard, tyreWearSoft, minGrip)

            if isFeasible:
                totalTime, lapFuelVector, lapTimeVector = predictStratTime(strat, lapGripVector, tyreSequence, track, tyreWearHard, tyreWearSoft, minGrip, fuelConsumption)

                #printWithoutEnd("%0.1f," % totalTime)

                stratString = ""

                curStintIdx = 0
                curTyre     = tyreSequence[curStintIdx]
                for s in strat:
                    if    curTyre == 'soft': stratString = stratString + 's' #printWithoutEnd('s')
                    elif  curTyre == 'hard': stratString = stratString + 'h' #printWithoutEnd('h')

                    if(s==1):
                        curStintIdx = curStintIdx + 1
                        curTyre = tyreSequence[curStintIdx]
                        #printWithoutEnd('p')
                        stratString = stratString + 'p'
                #print ''

                stratLapTimes.append([totalTime, stratString, strat, tyreSequence, lapGripVector, lapFuelVector, lapTimeVector]);
                #print "%0.1f %s" % (totalTime, stratString)

for sid, stratLapTime in enumerate(sorted(stratLapTimes)):
    if sid<20:
      print "[%0.2d] [%0.0f sec] %s" % (sid+1, stratLapTime[0], stratLapTime[1])

if(len(stratLapTimes)>0):    
    print "--- Top %d Stop Strategies ---" % (curStints-1)
    print "Lp, ,Tyre,FBeg,FEnd,time..."
    for lap in range(1,track['nlaps_default']+1):
        printWithoutEnd("%0.2d," % lap)
        for sid, stratLapTime in enumerate(sorted(stratLapTimes)):
            if sid<3:
                pitchar = ' '
                if stratLapTime[2][lap-1]==1: pitchar = 'P'

                printWithoutEnd("%s,%0.1f,%4.1f,%4.1f,%5.1f," % \
                      ( pitchar,
                        stratLapTime[4][lap-1], \
                        stratLapTime[5][lap-1]+fuelConsumption, \
                        stratLapTime[5][lap-1], \
                        stratLapTime[6][lap-1]))
        print ''

