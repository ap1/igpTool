import lxml.html as lh
from lxml import etree
import argparse

# --- Command line arguments
parser = argparse.ArgumentParser(description='parses iGP data')
parser.add_argument('-f', metavar = 'filename', type=argparse.FileType('r'), help='input results html', required=True)
args = parser.parse_args()

colheaders = ['Lap','Laptime','Gap','kph','Pos','Tyre','Fuel']

# --- convert table html element into hash
def lapTableToDict(tab):
    outtab = []
    for rowi,row in enumerate(tab.cssselect('tr')):
        rowdict = {}       
        if(not('pit' in row.get('class'))):
            cells = row.cssselect('td')
            if(len(cells)>0):
                for ci,cell in enumerate(cells):
                    key = colheaders[ci]
                    rowdict[key] = cell.text_content()

                mainkey = int(rowdict['Lap'])
                outtab.append(rowdict)
    return outtab


def parseLapTime(laptime):
    timearr = laptime.split(':')
    outtime = 0.0
    for timeval in timearr:
        outtime = outtime * 60 + float(timeval)
    return outtime

htmlcontent = args.f.read()

doc = lh.fromstring(htmlcontent)


tabs = doc.cssselect('table.acp')

#print tabs[0].text_content()

# --- parse the data
tabhash = lapTableToDict(tabs[0])

# --- massage the data
for lapi,row in enumerate(tabhash):
    lap = lapi+1
    print str(lap) + ": " + str(row)
    row['Laptime'] = parseLapTime(row['Laptime'])
    print str(lap) + ": " + str(row)
