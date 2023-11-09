"""Test fetch timing"""

from src.config import load_data
from src.debug import Timed, TimedCumulative

stations, events, posters = load_data()

timer0 = TimedCumulative("fetch api")
timer1 = TimedCumulative("parse departures")
timer2 = TimedCumulative("duplicates and sort")

for row in stations:
    for station in row:
        data = []
        departures = []
        with timer0:
            for url in station.get_urls():
                data += station._fetch_raw_departure_data(url)

        with timer1:
            for departure_data in data:
                departure = station._create_departure(departure_data)
                if departure is None:
                    continue
                departures.append(departure)

        with timer2:
            departures = list(dict.fromkeys(departures))
            departures.sort()

print(timer0.name, timer0.time)
print(timer1.name, timer1.time)
print(timer2.name, timer2.time)
