"""
Explore raw MTA GTFS-RT feed data.

Run with:
    poetry run python -m scripts.explore_feed
    poetry run python -m scripts.explore_feed --feed A
    poetry run python -m scripts.explore_feed --feed N --route W --stop R08S
"""

import argparse
from datetime import datetime
from nyct_gtfs import NYCTFeed

# Valid feed keys and the routes they carry
FEEDS = {
    "1": ["1", "2", "3", "4", "5", "6", "7"],
    "A": ["A", "C", "E"],
    "B": ["B", "D", "F", "M"],
    "G": ["G"],
    "J": ["J", "Z"],
    "L": ["L"],
    "N": ["N", "Q", "R", "W"],
    "7": ["7"],
    "SI": ["SI"],
}


def print_feed_summary(feed_key: str):
    print(f"\n{'='*60}")
    print(f"FEED: {feed_key}  (routes: {', '.join(FEEDS.get(feed_key, ['?']))})")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")

    feed = NYCTFeed(feed_key)
    trips = feed.trips
    print(f"Total trips in feed: {len(trips)}")

    # count by route
    from collections import Counter
    by_route = Counter(t.route_id for t in trips)
    for route, count in sorted(by_route.items()):
        print(f"  {route}: {count} trips")

    return feed


def print_trip(trip, max_stops=None):
    print(f"\n  trip_id   : {trip.trip_id}")
    print(f"  route_id  : {trip.route_id}")
    print(f"  direction : {trip.direction}  (N/S — GTFS direction, not compass)")
    print(f"  headsign  : {trip.headsign_text}")
    print(f"  stops ({len(trip.stop_time_updates)} remaining):")

    stops = trip.stop_time_updates
    if max_stops:
        stops = stops[:max_stops]

    for s in stops:
        arr = s.arrival.strftime("%H:%M:%S") if s.arrival else "     —    "
        dep = s.departure.strftime("%H:%M:%S") if s.departure else "     —    "
        name = s.stop_name or "(no name)"
        print(f"    {s.stop_id:<6}  arr {arr}  dep {dep}  {name}")

    if max_stops and len(trip.stop_time_updates) > max_stops:
        print(f"    ... and {len(trip.stop_time_updates) - max_stops} more stops")


def explore_feed(feed_key: str, route_filter: str | None, stop_filter: str | None, n_trips: int):
    feed = print_feed_summary(feed_key)

    trips = feed.trips
    if route_filter:
        trips = [t for t in trips if t.route_id == route_filter]
        print(f"\nFiltered to route '{route_filter}': {len(trips)} trips")

    if stop_filter:
        trips = [t for t in trips if any(s.stop_id == stop_filter for s in t.stop_time_updates)]
        print(f"Filtered to stop '{stop_filter}': {len(trips)} trips")

    print(f"\nShowing first {min(n_trips, len(trips))} trip(s):")
    for trip in trips[:n_trips]:
        print_trip(trip, max_stops=8)


def search_stop_name(feed_key: str, query: str):
    print(f"\nSearching '{feed_key}' feed for stops matching '{query}'...")
    feed = NYCTFeed(feed_key)
    seen = {}
    for trip in feed.trips:
        for s in trip.stop_time_updates:
            name = s.stop_name or ""
            if query.lower() in name.lower() and s.stop_id not in seen:
                seen[s.stop_id] = name
    if seen:
        for stop_id, name in sorted(seen.items()):
            print(f"  {stop_id:<6}  {name}")
    else:
        print("  (no matches)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explore raw MTA GTFS-RT feed data")
    parser.add_argument("--feed",   default="N",  help="Feed key (default: N). Options: 1 A B G J L N 7 SI")
    parser.add_argument("--route",  default=None, help="Filter to a specific route_id, e.g. W")
    parser.add_argument("--stop",   default=None, help="Filter to trips that hit this stop_id, e.g. R08S")
    parser.add_argument("--search", default=None, help="Search for stop IDs by station name substring")
    parser.add_argument("--trips",  default=2, type=int, help="Number of trips to print in full (default: 2)")
    args = parser.parse_args()

    if args.search:
        search_stop_name(args.feed, args.search)
    else:
        explore_feed(args.feed, args.route, args.stop, args.trips)
