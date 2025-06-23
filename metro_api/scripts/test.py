from nyct_gtfs import NYCTFeed
# from google.transit import gtfs_realtime_pb2
import requests
import time
from datetime import datetime

"""
routes i care about

Work
G Train (South), Clinton-Washington to Hoyt-Schermerhorn (key for other routes too)
C Train, Hoyt-Schermerhorn to Chambers St

G Train (North), Clinton-Washington to Broadway
"""

# -- Configuration with CORRECT Stop IDs --
CLINTON_WASHINGTON_S = "G35S"  # Clinton-Washington Avs (southbound towards Hoyt)
CLINTON_WASHINGTON_N = "G35N"  # Clinton-Washington Avs (northbound towards Court Sq)
HOYT_G_S = "A42S"  # Hoyt-Schermerhorn Sts G line (southbound)
HOYT_G_N = "A42N"  # Hoyt-Schermerhorn Sts G line (northbound)
HOYT_AC_S = "A42S"  # Hoyt-Schermerhorn Sts A/C line (southbound)
HOYT_AC_N = "A42N"  # Hoyt-Schermerhorn Sts A/C line (northbound)
CHAMBERS_ST_S = "A36S"  # Chambers St (southbound)
CHAMBERS_ST_N = "A36N"  # Chambers St (northbound)
FULTON_ST_S = "A38S"  # Fulton St (southbound)
FULTON_ST_N = "A38N"  # Fulton St (northbound)

def debug_feed_data():
    """Debug function to see what's actually in the feeds"""
    print("=== DEBUGGING FEED DATA ===")
    
    # Debug G train feed
    print("\n🔍 G TRAIN FEED DEBUG:")
    try:
        g_feed = NYCTFeed("G")
        print(f"Number of trips in G feed: {len(g_feed.trips)}")
        
        if g_feed.trips:
            # Show first few trips
            for i, trip in enumerate(g_feed.trips[:3]):
                print(f"\nTrip {i+1}: {trip.trip_id}")
                print(f"  Route: {trip.route_id}")
                print(f"  Direction: {trip.direction}")
                print(f"  Headsign: {trip.headsign_text}")
                print(f"  Number of stops: {len(trip.stop_time_updates)}")
                
                # Show stop IDs for this trip
                print("  Stop IDs in this trip:")
                for j, stop in enumerate(trip.stop_time_updates[:5]):  # First 5 stops
                    arrival_time = stop.arrival.strftime('%H:%M:%S') if stop.arrival else "N/A"
                    departure_time = stop.departure.strftime('%H:%M:%S') if stop.departure else "N/A"
                    print(f"    {j+1}. {stop.stop_id} ({stop.stop_name}) - Arr: {arrival_time}, Dep: {departure_time}")
                if len(trip.stop_time_updates) > 5:
                    print(f"    ... and {len(trip.stop_time_updates) - 5} more stops")
    except Exception as e:
        print(f"Error with G feed: {e}")
    
    # Debug A/C train feed
    print("\n🔍 A/C TRAIN FEED DEBUG:")
    try:
        ac_feed = NYCTFeed("A")  # ACE feed
        print(f"Number of trips in ACE feed: {len(ac_feed.trips)}")
        
        if ac_feed.trips:
            # Show A and C trips specifically
            a_trips = [t for t in ac_feed.trips if t.route_id == "A"]
            c_trips = [t for t in ac_feed.trips if t.route_id == "C"]
            print(f"A train trips: {len(a_trips)}")
            print(f"C train trips: {len(c_trips)}")
            
            # Show first A or C trip
            ac_trip = next((t for t in ac_feed.trips if t.route_id in ["A", "C"]), None)
            if ac_trip:
                print(f"\nSample {ac_trip.route_id} Trip: {ac_trip.trip_id}")
                print(f"  Direction: {ac_trip.direction}")
                print(f"  Headsign: {ac_trip.headsign_text}")
                print(f"  Number of stops: {len(ac_trip.stop_time_updates)}")
                
                # Show stop IDs for this trip
                print("  Stop IDs in this trip:")
                for j, stop in enumerate(ac_trip.stop_time_updates[:5]):  # First 5 stops
                    arrival_time = stop.arrival.strftime('%H:%M:%S') if stop.arrival else "N/A"
                    departure_time = stop.departure.strftime('%H:%M:%S') if stop.departure else "N/A"
                    print(f"    {j+1}. {stop.stop_id} ({stop.stop_name}) - Arr: {arrival_time}, Dep: {departure_time}")
                if len(ac_trip.stop_time_updates) > 5:
                    print(f"    ... and {len(ac_trip.stop_time_updates) - 5} more stops")
    except Exception as e:
        print(f"Error with ACE feed: {e}")

def find_stop_ids():
    """Find the correct stop IDs by searching for station names"""
    print("\n=== FINDING CORRECT STOP IDs ===")
    
    # Search G feed for Clinton-Washington
    try:
        g_feed = NYCTFeed("G")
        print("\n🔍 Searching G feed for Clinton-Washington stops:")
        clinton_stops = []
        for trip in g_feed.trips:
            for stop in trip.stop_time_updates:
                if "clinton" in stop.stop_name.lower() and "washington" in stop.stop_name.lower():
                    if stop.stop_id not in [s['stop_id'] for s in clinton_stops]:
                        clinton_stops.append({
                            'stop_id': stop.stop_id,
                            'stop_name': stop.stop_name
                        })
        
        for stop in clinton_stops:
            print(f"  {stop['stop_id']}: {stop['stop_name']}")
        
        # Search for Hoyt-Schermerhorn
        print("\n🔍 Searching G feed for Hoyt-Schermerhorn stops:")
        hoyt_stops = []
        for trip in g_feed.trips:
            for stop in trip.stop_time_updates:
                if "hoyt" in stop.stop_name.lower() and "schermerhorn" in stop.stop_name.lower():
                    if stop.stop_id not in [s['stop_id'] for s in hoyt_stops]:
                        hoyt_stops.append({
                            'stop_id': stop.stop_id,
                            'stop_name': stop.stop_name
                        })
        
        for stop in hoyt_stops:
            print(f"  {stop['stop_id']}: {stop['stop_name']}")
            
    except Exception as e:
        print(f"Error searching G feed: {e}")
    
    # Search A/C feed for Hoyt-Schermerhorn and Financial District stops
    try:
        ac_feed = NYCTFeed("A")
        print("\n🔍 Searching ACE feed for Hoyt-Schermerhorn stops:")
        hoyt_ac_stops = []
        for trip in ac_feed.trips:
            if trip.route_id in ["A", "C"]:
                for stop in trip.stop_time_updates:
                    if "hoyt" in stop.stop_name.lower() and "schermerhorn" in stop.stop_name.lower():
                        if stop.stop_id not in [s['stop_id'] for s in hoyt_ac_stops]:
                            hoyt_ac_stops.append({
                                'stop_id': stop.stop_id,
                                'stop_name': stop.stop_name
                            })
        
        for stop in hoyt_ac_stops:
            print(f"  {stop['stop_id']}: {stop['stop_name']}")
        
        print("\n🔍 Searching ACE feed for Financial District stops:")
        financial_stops = []
        financial_keywords = ["wall", "rector", "whitehall", "chambers", "fulton", "broadway-nassau"]
        
        for trip in ac_feed.trips:
            if trip.route_id in ["A", "C"]:
                for stop in trip.stop_time_updates:
                    for keyword in financial_keywords:
                        if keyword in stop.stop_name.lower():
                            if stop.stop_id not in [s['stop_id'] for s in financial_stops]:
                                financial_stops.append({
                                    'stop_id': stop.stop_id,
                                    'stop_name': stop.stop_name
                                })
                            break
        
        for stop in financial_stops:
            print(f"  {stop['stop_id']}: {stop['stop_name']}")
            
    except Exception as e:
        print(f"Error searching ACE feed: {e}")

def fetch_g_trains_to_hoyt(n=5):
    """Fetch G trains from Clinton-Washington going south to Hoyt-Schermerhorn"""
    print("🚇 Fetching G trains to Hoyt-Schermerhorn...")
    try:
        feed = NYCTFeed("G")
        current_time = datetime.now()
        
        # Look for southbound G trains (direction S) that go to Church Av (which passes through Hoyt)
        southbound_trains = [trip for trip in feed.trips if trip.direction == "S" and "Church Av" in trip.headsign_text]
        
        print(f"Found {len(southbound_trains)} southbound G trains to Church Av")
        
        upcoming_departures = []
        
        for trip in southbound_trains:
            # Check if this trip has Clinton-Washington in its route
            clinton_departure = None
            hoyt_arrival = None
            
            for stop in trip.stop_time_updates:
                if stop.stop_id == CLINTON_WASHINGTON_S and stop.departure:
                    clinton_departure = stop.departure
                elif stop.stop_id == HOYT_G_S and stop.arrival:
                    hoyt_arrival = stop.arrival
            
            # If we found both stops and departure is in the future
            if clinton_departure and clinton_departure > current_time:
                upcoming_departures.append({
                    'trip_id': trip.trip_id,
                    'departure_from_clinton': clinton_departure,
                    'arrival_at_hoyt': hoyt_arrival,
                    'headsign': trip.headsign_text
                })
        
        # Sort by departure time
        upcoming_departures.sort(key=lambda x: x['departure_from_clinton'])
        return upcoming_departures[:n]
        
    except Exception as e:
        print(f"Error fetching G trains: {e}")
        return []

def fetch_ac_trains_from_hoyt(n=5):
    """Fetch A/C trains from Hoyt-Schermerhorn to Financial District"""
    print("🚇 Fetching A/C trains from Hoyt to Financial District...")
    try:
        feed = NYCTFeed("A")  # ACE feed
        current_time = datetime.now()
        
        # Look for A and C trains
        ac_trains = [trip for trip in feed.trips if trip.route_id in ["A", "C"]]
        
        print(f"Found {len(ac_trains)} A/C trains")
        
        upcoming_departures = []
        
        for trip in ac_trains:
            # Check if this trip stops at Hoyt and goes to Financial District
            hoyt_departure = None
            goes_to_financial = False
            financial_arrival = None
            
            for stop in trip.stop_time_updates:
                if stop.stop_id in [HOYT_AC_S, HOYT_AC_N] and stop.departure:
                    hoyt_departure = stop.departure
                elif stop.stop_id in [CHAMBERS_ST_S, CHAMBERS_ST_N, FULTON_ST_S, FULTON_ST_N]:
                    goes_to_financial = True
                    if stop.arrival:
                        financial_arrival = stop.arrival
                        break
            
            # If we found Hoyt departure and it goes to Financial District
            if hoyt_departure and hoyt_departure > current_time and goes_to_financial:
                upcoming_departures.append({
                    'trip_id': trip.trip_id,
                    'line': trip.route_id,
                    'departure_from_hoyt': hoyt_departure,
                    'arrival_at_financial': financial_arrival,
                    'headsign': trip.headsign_text,
                    'direction': trip.direction
                })
        
        # Sort by departure time
        upcoming_departures.sort(key=lambda x: x['departure_from_hoyt'])
        return upcoming_departures[:n]
        
    except Exception as e:
        print(f"Error fetching A/C trains: {e}")
        return []

def calculate_journey_times():
    """Calculate complete journey from Clinton-Washington to Financial District"""
    print("\n" + "="*60)
    print("🗽 NYC METRO JOURNEY: Clinton-Washington → Financial District")
    print("="*60)
    
    current_time = datetime.now()
    print(f"Current time: {current_time.strftime('%H:%M:%S')}")
    
    # Get G train options
    g_trains = fetch_g_trains_to_hoyt(3)
    
    print(f"\n🚇 G TRAIN OPTIONS (Clinton-Washington → Hoyt-Schermerhorn):")
    if g_trains:
        for i, train in enumerate(g_trains, 1):
            dep_time = train['departure_from_clinton'].strftime('%H:%M')
            arr_time = train['arrival_at_hoyt'].strftime('%H:%M') if train['arrival_at_hoyt'] else "N/A"
            print(f"  {i}. Depart {dep_time} → Arrive Hoyt {arr_time} (Train {train['trip_id'][-6:]})")
    else:
        print("  ❌ No upcoming G trains found")
    
    # Get A/C train options
    ac_trains = fetch_ac_trains_from_hoyt(5)
    
    print(f"\n🚇 A/C TRAIN OPTIONS (Hoyt-Schermerhorn → Financial District):")
    if ac_trains:
        for i, train in enumerate(ac_trains, 1):
            dep_time = train['departure_from_hoyt'].strftime('%H:%M')
            arr_time = train['arrival_at_financial'].strftime('%H:%M') if train['arrival_at_financial'] else "N/A"
            print(f"  {i}. {train['line']} Train - Depart {dep_time} → Arrive {arr_time}")
            print(f"     Destination: {train['headsign']} (Train {train['trip_id'][-6:]})")
    else:
        print("  ❌ No upcoming A/C trains found")
    
    # Calculate best connections
    if g_trains and ac_trains:
        print(f"\n🔄 BEST CONNECTION OPTIONS:")
        for g_train in g_trains[:2]:  # Top 2 G trains
            g_arrival = g_train['arrival_at_hoyt']
            if g_arrival:
                # Find A/C trains departing after G train arrives (with 3-minute buffer)
                buffer_time = g_arrival.replace(minute=g_arrival.minute + 3)
                connecting_trains = [ac for ac in ac_trains if ac['departure_from_hoyt'] > buffer_time]
                
                if connecting_trains:
                    best_connection = connecting_trains[0]
                    g_dep = g_train['departure_from_clinton'].strftime('%H:%M')
                    g_arr = g_arrival.strftime('%H:%M')
                    ac_dep = best_connection['departure_from_hoyt'].strftime('%H:%M')
                    ac_arr = best_connection['arrival_at_financial'].strftime('%H:%M') if best_connection['arrival_at_financial'] else "N/A"
                    
                    total_time = (best_connection['arrival_at_financial'] - g_train['departure_from_clinton']).total_seconds() / 60 if best_connection['arrival_at_financial'] else "N/A"
                    
                    print(f"  • G Train {g_dep} → {g_arr} + {best_connection['line']} Train {ac_dep} → {ac_arr}")
                    print(f"    Total journey time: {total_time:.0f} minutes" if total_time != "N/A" else "    Total time: N/A")
    
    print(f"\n💡 Transfer Info:")
    print(f"  • Transfer at Hoyt-Schermerhorn Sts")
    print(f"  • Walking time between G and A/C platforms: ~2-3 minutes")
    print(f"  • A train is express (faster), C train is local")

if __name__ == "__main__":
    debug_feed_data()
    find_stop_ids()
    calculate_journey_times()

# def fetch_active_alerts():
#     headers = {"x-api-key": MTA_API_KEY}
#     r = requests.get(ALERTS_FEED_URL, headers=headers)
#     r.raise_for_status()
#     data = r.content
#     # parse GTFS‑rt alerts
#     feed = gtfs_realtime_pb2.FeedMessage()
#     feed.ParseFromString(data)
#     alerts = []
#     now = int(time.time())
#     for entity in feed.entity:
#         if entity.HasField('alert'):
#             alert = entity.alert
#             routes = [ie.route_id for ie in alert.informed_entity if ie.route_id]
#             if "G" in routes:
#                 # check active period
#                 for period in alert.active_period:
#                     if (not period.HasField('start') or period.start <= now) and \
#                        (not period.HasField('end') or period.end >= now):
#                         alerts.append({
#                             "header": alert.header_text.translation[0].text,
#                             "description": alert.description_text.translation[0].text
#                         })
#                         break
#     return alerts
