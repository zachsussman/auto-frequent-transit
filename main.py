#!/usr/bin/env python3
import pygtfs
import datetime
import warnings
from sqlalchemy import exc as sa_exc
from sort_nicely import sort_nicely, sorted_nicely
import argparse
import sys
import pickle

log = None

LABELS = False
OUTPUT_FILE = None
INPUT_FILE = None
CACHE_FILE = None
SEGMENTS_FILE = None

LOCATION = None

''' The top-level schedule '''
schedule = None

routes = {}
route_headways = {}

def load_schedule(input_file):
    global schedule
    warnings.filterwarnings("ignore", category=sa_exc.SAWarning)
    schedule = pygtfs.Schedule(input_file)

    for r in schedule.routes:
        routes[r.route_short_name] = r



    log("Schedule loaded for", schedule.agencies[0].agency_name)

''' Get ordered schedule for key'th run of route: [(stop, time, order_num)*] '''
def get_sched(route, key=10):
    return trip_sched(route.trips[key])

''' Return datetime.timedelta object at hours:minutes:seconds '''
def timedelta(hours, minutes=0, seconds=0):
    return datetime.timedelta(0, hours*3600+minutes*60+seconds)

''' Get ordered schedule for trip '''
def trip_sched(trip):
    stops = []

    for s in trip.stop_times:
        stops += [(schedule.stops_by_id(s.stop_id)[0], s.arrival_time, s.stop_sequence)]

    stops.sort(key=lambda s:s[2])
##    stops = [(a[0], a[1]) for a in stops]

    return stops

''' Time of this trip, based on the stop_number'th stop '''
def trip_time(trip, stop_number=0):
    return trip_sched(trip)[stop_number][1]


''' Time of this trip, based on the stop_id stop '''
def fast_trip_time(trip, stop_id):
    s = [s for s in trip.stop_times if s.stop_id == stop_id] # Identify the stop_time for this trip
    if len(s) > 0:
        return s[0].arrival_time
    else:
        return None

''' Times of this route, based on the stop_id stop '''
def fast_route_times(route, direction_id, stop_id, f=(lambda s: True)):
    times = []
    ts = [t for t in route.trips if f(service_of_trip(t)) and t.direction_id == direction_id] # Get relevant trips
    for t in ts:
        times += [fast_trip_time(t, stop_id)]
    times = [t for t in times if t]
    return times

''' Times of this route, based on the stop_number'th stop '''
def route_times(route, direction_id, stop_number=0, f=(lambda s: True), key=10):
    key = min(key, len(route.trips)-1)
    stop_id = trip_sched(route.trips[key])[0][0].stop_id # Get the stop id for the relevant stop
    return fast_route_times(route, direction_id, stop_id, f)


''' Service days of this trip '''
def service_of_trip(trip):
    return schedule.services_by_id(trip.service_id)[0]

''' Sorted times this route runs, based on stop_number'th stop and only on trips satisfying f: Service->boolean '''
def slow_route_times(route, stop_number=0, f=(lambda s: True)):
    times = []
    ts = [t for t in route.trips if f(service_of_trip(t))]
    for t in ts:
        times += [trip_time(t)]

    times.sort()
    return times

''' Does this service run on all weekdays? '''
def isWeekday(service):
    return service.monday and service.tuesday and service.wednesday and service.thursday and service.friday

''' Does this service run on Saturday? '''
def isSaturday(service):
    return service.saturday

''' Does this service run on Sunday? '''
def isSunday(service):
    return service.sunday

''' Returns a representation of the days this service runs, in MTWThFSaSu format '''
def str_service(service):
    s = ""
    if service.monday: s += "M"
    if service.tuesday: s += "T"
    if service.wednesday: s += "W"
    if service.thursday: s += "Th"
    if service.friday: s += "F"
    if service.saturday: s += "Sa"
    if service.sunday: s += "Su"
    return s


''' Get the weekday route times for this route '''
def weekday_route_times(route, direction_id, stop_id):
    return fast_route_times(route, direction_id, stop_id, isWeekday)

''' Get a sorted slice of times between begin and end '''
def slice_times(times, begin, end):
    return sorted([t for t in times if t > begin and t < end])

''' Return the average headway between these times '''
def avg_headway(times):
    if len(times) < 2: return None
    acc = timedelta(0)
    for i in range(0, len(times)-1):
        acc += times[i+1]-times[i]
    return acc/(len(times)-1)

def max_headway(times):
    if len(times) < 2: return None
    m = timedelta(0, 0)
    for i in range(0, len(times)-1):
        t = times[i+1]-times[i]
        if m < t:
            m = t
    return m

''' Return the midday headway (10am to 2pm) of a route '''
def midday_headway(route):
    return max_headway(slice_times(route_times(route, 1, 0, isWeekday), timedelta(10), timedelta(14)))

agency_locations = {
    "Port Authority of Allegheny County": (40.4486904,  -79.9433273),
    "Miami Dade Transit": (25.7084636, -80.2051862),
    "Spokane Transit Authority": (47.6727552, -117.4183375),
    "San Francisco Municipal Transportation Agency": (37.760665, -122.4640383),
    "Central Ohio Transit Authority": (39.9986493, -82.9825982),
    "Regional Transit System": (29.6772486, -82.3293686)  # Gainesville
    }



stop_pairs_list = {}

def iterate_trip(trip, route_name):
    ts = trip_sched(trip)
    for i in range(0, len(ts)-1):
        stop_pair = ts[i][0].stop_id + "-" + ts[i+1][0].stop_id
        if stop_pair in stop_pairs_list:
            stop_pairs_list[stop_pair] += [(route_name, trip.direction_id)]
        else:
            stop_pairs_list[stop_pair] = [(route_name, trip.direction_id)]



def get_trips(route):
    direction = lambda d, t: t.direction_id == d
    listA = [t for t in route.trips if t.direction_id == 0]
    listB = [t for t in route.trips if t.direction_id == 1]
    if len(listA) > 0 and len(listB) > 0:
        return listA[0], listB[0]
    else:
        return None, None

def iterate_route(route_name):
    route = routes[route_name]
    if len(route.trips) < 2: return
    a, b = get_trips(route)
    if not a or not b: return
    iterate_trip(a, route_name)
    iterate_trip(b, route_name)

def iterate_routes(names):
    log("Tracing routes:")
    names = list(names)
    sort_nicely(names)
    i = 0
    for n in names:
        i += 1
        log(n, end='\t')
        if i%8 == 0:
            log()
        iterate_route(n)
    log()



def routes_to_key(info_list):
    string = ""
    info_list = sorted(info_list, key=lambda q: q[0])
    for a in info_list:
        route, direction = a
        string += route + "#" + str(direction) + "-"

    return string

def get_stop_schedule(stop_pair):
    a, b = stop_pair.split("-")
    times = []
    for q in stop_pairs_list[stop_pair]:
        r, d = q
        route = routes[r]
        time_list = weekday_route_times(route, d, b)
        times += time_list
        if r not in route_headways:
            midday_times = slice_times(time_list, timedelta(10), timedelta(14))
            route_headways[r] = max_headway(midday_times)
    return times


combined_frequencies = {}
def midday_frequency(stop_pair):
    global combined_frequencies
    route_names = routes_to_key(stop_pairs_list[stop_pair])
    if route_names in combined_frequencies:
        return combined_frequencies[route_names]

    times = get_stop_schedule(stop_pair)
    times = slice_times(times, timedelta(10), timedelta(14))
    frequency = max_headway(times)
    combined_frequencies[route_names] = frequency
    return frequency




def produce_line_segment(stopA, stopB):
    latA = str(stopA.stop_lat)
    latB = str(stopB.stop_lat)
    longA = str(stopA.stop_lon)
    longB = str(stopB.stop_lon)
    return "        new google.maps.Polyline({path: [{lat:" + latA + \
           ", lng:" + longA + "},{lat:" + latB + ", lng:" + longB + \
           "}],geodesic: true,strokeColor: '#FF0000',strokeOpacity: 1.0,strokeWeight: 5}).setMap(map);\n"

def str_point(lat, lng):
    return "{lat:" + str(lat) + ", lng:" + str(lng) + "}"

def str_stop(stop_id):
    s = schedule.stops_by_id(stop_id)[0]
    return str_point(s.stop_lat, s.stop_lon)

def str_stops(lst):
    return ",".join(map(str_stop, lst))

def str_routes(routes):
    names = [a[0] for a in routes if a[0] in route_headways and route_headways[a[0]]]
    sort_nicely(names)
    ss = ""
    ss += ", ".join(names[0:5])
    for i in range(5, len(names), 5):
        ss += "\\n, ".join(names[i:i+5])
    return ss

def str_label(label, lat, lng):
    return "new MapLabel({text:'" + label + "', position: new google.maps.LatLng(" + \
           str(lat) + ", " +  str(lng) + "), map: map, fontSize: 8, align: 'center', zIndex:15}).setMap(map);\n"

def produce_line(lst, routes, hsh):
    label = str_routes(routes)
    ss =   "        var " + hsh + " = new google.maps.Polyline({path: [" + str_stops(lst) + \
           "],geodesic: true,strokeColor: '#FF0000',strokeOpacity: 1.0,strokeWeight: 5 });\n" + \
           "        " + hsh + ".setMap(map);\n" + \
           "        var info" + hsh + " = new google.maps.InfoWindow({content: \"" + label + \
           "\"});\n" + \
           "        " + hsh + ".addListener('mouseover', function(e) {   info" + hsh + \
           ".open(map, " + hsh + "); info" + hsh + ".setPosition(e.latLng);});\n" + \
           "        " + hsh + ".addListener('mouseout', function(e) {   info" + hsh + \
           ".close(); });\n"

    if LABELS and routes[0][1] == 1:
        stops = [schedule.stops_by_id(stop_id)[0] for stop_id in lst]
        points = [(stop.stop_lat, stop.stop_lon) for stop in stops]
        label_points = []
        for i in range(0, len(points)-1, 5):
            lata, lona = points[i]
            latb, lonb = points[i+1]
            label_points += [((lata+latb)/2, (lona+lonb)/2)]
        for p in label_points:
            lat, lon = p
            ss += str_label(label, lat, lon)

    return ss




frequent_hash = []

def index_segments(stop_pairs_list):
    global frequent_hash

    i = 0
    n = 0
    l = len(stop_pairs_list)
    log("Indexing", l, "segments")
    for k in stop_pairs_list:
        m = midday_frequency(k)
        if m and m <= timedelta(0, 15, 1):
            segment = stop_pairs_list[k]
            frequent_pairs[k] = segment
            a, b = k.split("-")
            frequent_hash += [(a, b, routes_to_key(segment), segment, [])]
        i += 1
        if i%(l//20) == 0:
            log(".", end='')

    log("Segments indexed,", len(combined_frequencies), "unique schedules")

    log("Collating segments...")
    new_segments = []
    while len(frequent_hash) > 0:
        new_segments += [extend(frequent_hash[0])]


    log(len(new_segments), "polylines generated")




    return new_segments




''' Extends a segment fully.
segment: (left, right, routes, key, list)
'''

def extend(segment):
    global frequent_hash
    left, right, key, routes, lst = segment

    def find(point):
        l = [a for a in frequent_hash if point in (a[0], a[1]) and a[2] == key]
        if len(l) > 0: return l[0]
        else: return None

    lst += [left, right]

    frequent_hash.remove(segment)

    p = find(left)
    while p:
        frequent_hash.remove(p)
        if left == p[0]:
            left = p[1]
        else:
            left = p[0]
        p = find(left)
        lst.insert(0, left)

    p = find(right)
    while p:
        frequent_hash.remove(p)
        if right == p[0]:
            right = p[1]
        else:
            right = p[0]
        p = find(right)
        lst.append(right)

    return (left, right, routes, key, lst)


def write(segments, file):
    log("Writing file...")
    lat = LOCATION[0]
    lng = LOCATION[1]

    intro = \
"var map;\n" + \
"    function initMap() {\n" + \
"        map = new google.maps.Map(document.getElementById('map'), {\n" + \
"            center: {lat: " + str(lat) + ", lng: " + str(lng) + "}, zoom: 12\n" + \
"            });\n"


    file.write(intro)

    for s in segments:
        a, b, routes, key, lst = s
        file.write(produce_line(lst, routes, "q"+a+b))


    outro = "}\n initMap();"
    file.write(outro)



frequent_pairs = {}
new_segments = []

def create_frequent_map(input_file, output_file, rlist = None):
    global combined_frequencies, frequent_pairs, frequent_hash, new_segments, route_headways
    global LOCATION

    load_schedule(input_file)

    if not LOCATION and schedule.agencies[0].agency_name in agency_locations:
        LOCATION = agency_locations[schedule.agencies[0].agency_name]
    if not LOCATION:
        raise Exception("No location given for map")

    if not rlist:
        rlist = routes.keys()

    if SEGMENTS_FILE:
        log("Loading frequent routes from", SEGMENTS_FILE+"...")
        with open(SEGMENTS_FILE, 'rb') as f:
            new_segments, route_headways = pickle.load(f)
    else:
        iterate_routes(rlist)
        new_segments = index_segments(stop_pairs_list)


    if CACHE_FILE:
        log("Caching frequent routes into", CACHE_FILE+"...")
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump((new_segments, route_headways), f)

    with open(output_file, 'w') as f:
        write(new_segments, f)




def internal_log(*a, **kwargs):
    print(*a, **kwargs)
    sys.stdout.flush()

parser = None

parser = argparse.ArgumentParser(description="Creates a frequent transit map from gtfs data.")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable logging")
parser.add_argument("-l", "--label", action="store_true", help="Add labels to map routes")
parser.add_argument("-c", "--cache", nargs=1, help="Cache frequent segments", metavar="CACHE")
parser.add_argument("-d", "--draw", nargs=1, help="Read frequent routes from cache", metavar="CACHE")
parser.add_argument("--loc", nargs=2, type=float, help="Latitude and longitude of city", metavar=("LAT", "LONG"))
parser.add_argument("input_file", help="GTFS or sqlite file")
parser.add_argument("output_file", help=".js file to be included in map page")

args = parser.parse_args()
LABELS = args.label
if args.verbose:
    log = internal_log
else:
    log = lambda *s: None

INPUT_FILE = args.input_file
OUTPUT_FILE = args.output_file
CACHE_FILE = args.cache and args.cache[0]
SEGMENTS_FILE = args.draw and args.draw[0]

LOCATION = args.loc

try:
    create_frequent_map(INPUT_FILE, OUTPUT_FILE)
except Exception as e:
    raise
