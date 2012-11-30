import argparse,csv,math,sys,os,datetime,glob,re,array

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
        track['nlaps_default'] = int(track['nlaps_default'])
        return track
    else:
        print "Error: Search for %s returned %d matches" % (args.track,len(matching_tracks))
        sys.exit(1)

# -- Estimate fuel consumption
def estimateFuelConsumption(track):
    return 0.73 * track['length']

# -- Estimate tyre wear
def estimateTyreWear(track):
    tyreWearHard = [0.0, 0.0]
    tyreWearSoft = [0.0, 0.0]
    if   track['tyre_wear']=='vhigh':
        tyreWearHard = [-0.027, 1.15]
        tyreWearSoft = [-0.11,  2.3]
    elif track['tyre_wear']=='high':
        tyreWearHard = [-0.023, 1.4]
        tyreWearSoft = [-0.006, 2.0]
    elif track['tyre_wear']=='avg':
        tyreWearHard = [-0.008, 0.87]
        tyreWearSoft = [-0.06,  1.92]
    elif track['tyre_wear']=='low':
        tyreWearHard = [-0.006, 0.75]
        tyreWearSoft = [-0.03,  1.59]
    elif track['tyre_wear']=='vlow':
        tyreWearHard = [-0.008, 0.75]
        tyreWearSoft = [-0.03,  1.57]
    else:
        print "Error: cannot understand tyre wear '%s'" % track['tyre_wear']
        sys.exit(1)

    tyreWearHard = [tyreWearHard[0]*track['length'], tyreWearHard[1]*track['length']]
    tyreWearSoft = [tyreWearSoft[0]*track['length'], tyreWearSoft[1]*track['length']]
    
    return tyreWearSoft, tyreWearHard

# -- How many laps will a tyre last?
def findGoodLaps(tyreWear):
    tyre=100.0
    lap =0.0
    while tyre>40.0:
        lap = lap + 1.0
        tyre = tyre - (tyreWear[0]*lap + tyreWear[1])
        #print "%d laps: tyre %0.1f" % (lap,tyre) >> mohamed.csv
    return (lap)


# ------------------------------------------------------
#  Code
# ------------------------------------------------------

# -- Parser command line arguments
parser = argparse.ArgumentParser(description='Iterate on pit strategies')

parser.add_argument('-track',  metavar = 'name', type=str, help='name of track',          required=True)
parser.add_argument('-stints', metavar = 'num',  type=int, help='maximum stints to try',  default=4)
parser.add_argument('-laps',   metavar = 'num',  type=int, help='number of laps',         default=-1)

args = parser.parse_args()

track = fetchTrackInfo(args)

if(int(args.laps)>0):
    track['nlaps_default'] = args.laps

print "%s: %0.3f kms" % (track['name'],track['length'])
print "%d laps" % (track['nlaps_default'])

fuelConsumption             = estimateFuelConsumption(track)
tyreWearSoft, tyreWearHard  = estimateTyreWear(track)

softGoodLaps = findGoodLaps(tyreWearSoft)
hardGoodLaps = findGoodLaps(tyreWearHard)

print "%0.2f liters / lap" % fuelConsumption
print "soft tyre good for %d laps" % (softGoodLaps)
print "hard tyre good for %d laps" % (hardGoodLaps)

for curStints in range(1,args.stints+1):
    print "Trying %d pit stop strategy..." % (curStints-1)
