# auto-frequent-transit
Automatically generated frequent transit maps.  

Demos at [zacharysussman.com/frequent.html](http://zacharysussman.com/frequent.html).

## Details
When you ride the bus, one of the most important things you ask yourself is "how often does the bus come?" If that answer is "once an hour," you'll either need to really plan your trip, or just not use the bus at all. In contrast, if that answer is more like "every few minutes," you can just walk up to the stop and be confident that even though you don't know when the bus will come, it will come soon. Because people usually hate waiting around, the more frequently a bus comes, the more useful it is. In fact, Jarrett Walker, an experienced transit planner with his own blog called Human Transit, often says:

>Frequency is freedom.

He expands in his post "The Ridership Recipe":

>People who are used to getting around by a private vehicle (car or bike) often underestimate the importance of frequency, because there isn't an equivalent to it in their experience. A private vehicle is ready to go when you are, but transit is not going until it comes. High frequency means transit is coming soon, which means that it approximate the feeling of liberty you have with your private vehicle - that you can go anytime. Frequency is freedom!

At the opposite extreme, if you live in a single family house with a driveway and usually get around by car, imagine that there were an automated gate at the end of your driveway that only opened once an hour, on the hour. When it's closed, you can't get your car in or out. If that were your situation, your biggest transportation problem would not be traffic congestion, or how fast you can go on the freeway; it would be how to get this frigging gate to open more often. That's how low frequency feels to a potential transit customer, and why frequency often swamps other factors, like speed, in determining whether transit is actually useful.

Jarrett Walker was also one of the first people to advocate for "frequent transit maps": maps showing not all of the bus routes in an area, but just the most useful, the most frequent ones. Over the past few years, more and more transit agencies have been releasing these frequent transit maps, but most cities still don't have a map of their most useful lines.

As these more useful maps have slowly spread, another revolution in transit mapping has happened, with the rapid rise in computer-generated directions and maps, like Google Maps's transit directions. These overlapping trends led me to wonder if they couldn't be combined: if you could automatically generate frequent transit maps.

##Technical Details

Almost all US transit agencies release route data in a format called GTFS, for General Transit Feed Specification. I used pygtfs to read the GTFS files, then a python script to process them and filter out the most frequent routes. The script outputs a javascript file, which uses the Google Maps API to draw lines on an embedded map, suitable for display on a webpage.

In contrast to some attempts at automatic frequent route maps, I process the data stop by stop to catch the common cases where many routes interline into one frequent corridor. Examples of this happening are the 61A/B/C/D in Pittsburgh, where four 20-minute lines interline to one 5 minute line, and the Green Line in Boston, where four branches combine to provide super-frequent service into downtown. By doing this, I make sure that I capture the full range of frequency provided by a transit agency.

Right now, I use "every 15 minutes or less 10:00 am - 2:00 pm" as my hardcoded frequency guideline. Future versions will allow you to specify a particular target frequency and time.

##Areas for Improvement

I'd like to allow for custom-defined measures of frequency/reliability. Also, I'd like to revamp the map-drawing portion, first to join up segments of the same route, then to use (if available) GTFS's route line information to make the map prettier. I'm also looking into using MapBox for better ways to draw maps than outputting Google Maps commands in Javascript.
