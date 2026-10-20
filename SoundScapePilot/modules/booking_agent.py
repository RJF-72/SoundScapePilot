import os
import re
import time
import httpx
from typing import List, Dict, Any, Set, Optional

from modules.mailer import DEFAULT_DOMAIN


WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_BASE = "https://en.wikipedia.org"
OVER_PASS_APIS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

_STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# Query keywords that mark a church-seeking intent. Any hit runs church
# discovery (all sources) and boosts tagged churches to the top of results.
CHURCH_KEYWORDS = [
    "church", "churches", "worship", "gospel", "christian", "catholic", "baptist",
    "methodist", "lutheran", "presbyterian", "episcopal", "pentecostal",
    "assembly of god", "non-denominational", "nondenominational", "cathedral",
    "chapel", "ministry", "ministries", "sanctuary", "revival", "revivals",
    "megachurch", "tabernacle", "nazarene",
]

CHURCH_NAME_RE = re.compile(
    r"\b(church|churches|chapel|cathedral|ministry|ministries|tabernacle|baptist|"
    r"methodist|lutheran|presbyterian|episcopal|pentecostal|catholic|nazarene|"
    r"christian|christ|savior|saviour|fellowship|worship|kingdom hall|"
    r"assembly of god|non-denominational|word of god|full gospel)\b", re.I)
CHURCH_NAME_EXCLUDE_RE = re.compile(
    r"\b(theatre|theater|ballroom|nightclub|amphitheater|amphitheatre|saloon|"
    r"lounge|pub|bar|live|studio|restaurant|grill|cinema)\b", re.I)
OUTDOOR_NAME_RE = re.compile(
    r"\b(amphitheater|amphitheatre|outdoor|bandstand|fairground|fair grounds|"
    r"open air|open-air|pavilion)\b", re.I)
LISTENING_NAME_RE = re.compile(r"\blistening\b", re.I)
ARENA_NAME_RE = re.compile(r"\b(arena|stadium|coliseum|colosseum)\b", re.I)
THEATER_NAME_RE = re.compile(
    r"\b(theatre|theater|playhouse|opera|auditorium|performing arts|cinema)\b", re.I)
CLUB_NAME_RE = re.compile(r"\b(nightclub|night club|dance hall|dancehall|club)\b", re.I)
CAFE_NAME_RE = re.compile(r"\b(cafe|caf\u00e9|coffee)\b", re.I)
BAR_NAME_RE = re.compile(
    r"\b(bar|pub|saloon|lounge|tavern|honky|brew|biergarten|beer garden|icehouse|roadhouse)\b", re.I)
CIVIC_NAME_RE = re.compile(
    r"\b(civic|community|grange|vfw|legion|elks|expo|convention|exhibition|"
    r"fraternal|events center|event center|center|centre)\b", re.I)

# Genre -> Wikipedia categories (per-state + genre-specific)
GENRE_CATEGORIES = {
    "rock": ["Category:Rock music venues", "Category:Rock clubs", "Category:Rock festivals"],
    "indie rock": ["Category:Indie rock venues", "Category:Indie music venues"],
    "indie": ["Category:Indie music venues"],
    "alternative": ["Category:Alternative rock venues"],
    "punk": ["Category:Punk venues", "Category:Punk rock clubs"],
    "metal": ["Category:Heavy metal venues", "Category:Metal clubs", "Category:Metal festivals"],
    "hardcore": ["Category:Hardcore punk venues"],
    "hip hop": ["Category:Hip hop venues", "Category:Hip hop clubs", "Category:Hip hop festivals"],
    "rap": ["Category:Hip hop venues"],
    "rnb": ["Category:R&B venues", "Category:Soul music venues"],
    "r&b": ["Category:R&B venues", "Category:Soul music venues"],
    "soul": ["Category:Soul music venues"],
    "funk": ["Category:Funk venues"],
    "blues": ["Category:Blues clubs", "Category:Blues venues", "Category:Blues festivals"],
    "jazz": ["Category:Jazz clubs", "Category:Jazz venues", "Category:Jazz festivals"],
    "country": ["Category:Country music venues", "Category:Honky-tonks", "Category:Country festivals"],
    "honky-tonk": ["Category:Honky-tonks", "Category:Country music venues"],
    "honky tonk": ["Category:Honky-tonks", "Category:Country music venues"],
    "folk": ["Category:Folk music venues", "Category:Folk festivals"],
    "americana": ["Category:Folk music venues"],
    "bluegrass": ["Category:Bluegrass festivals"],
    "electronic": ["Category:Electronic dance music venues", "Category:Nightclubs", "Category:Electronic music festivals"],
    "edm": ["Category:Electronic dance music venues"],
    "synthwave": ["Category:Electronic dance music venues"],
    "industrial": ["Category:Industrial music venues"],
    "noise": ["Category:Experimental music venues"],
    "experimental": ["Category:Experimental music venues", "Category:Avant-garde music venues"],
    "ambient": ["Category:Experimental music venues"],
    "shoegaze": ["Category:Indie music venues"],
    "post punk": ["Category:Punk venues"],
    "pop": ["Category:Pop music venues", "Category:Pop festivals"],
    "dance": ["Category:Dance clubs", "Category:Nightclubs"],
    "latin": ["Category:Latin music venues"],
    "reggae": ["Category:Reggae venues", "Category:Reggae festivals"],
    "ska": ["Category:Ska venues"],
    "classical": ["Category:Concert halls", "Category:Classical music venues", "Category:Opera houses"],
    "opera": ["Category:Opera houses", "Category:Concert halls"],
    "comedy": ["Category:Comedy clubs"],
    "theatre": ["Category:Theatres"],
    "theater": ["Category:Theatres"],
    "cabaret": ["Category:Cabaret venues"],
    "burlesque": ["Category:Burlesque venues"],
    "gospel": ["Category:Churches", "Category:Gospel music venues"],
    "worship": ["Category:Churches", "Category:Religious buildings and structures"],
    "faith": ["Category:Churches"],
    "spiritual": ["Category:Religious buildings and structures"],
    "christian": ["Category:Churches", "Category:Gospel music venues"],
    "church": ["Category:Churches", "Category:Gospel music venues"],
    "religious": ["Category:Churches", "Category:Religious buildings and structures"],
}

GENRE_LIST_PAGES = {
    "rock": ["List of rock festivals", "List of rock concert tours"],
    "jazz": ["List of jazz festivals", "List of jazz clubs"],
    "blues": ["List of blues festivals"],
    "country": ["List of country music festivals", "List of country music venues"],
    "hip hop": ["List of hip hop festivals", "List of hip hop music venues"],
    "electronic": ["List of electronic music festivals"],
    "folk": ["List of folk festivals"],
    "metal": ["List of heavy metal festivals"],
    "punk": ["List of punk rock festivals"],
    "classical": ["List of classical music festivals", "List of opera houses"],
    "reggae": ["List of reggae festivals"],
    "latin": ["List of Latin music festivals"],
    "comedy": ["List of comedy festivals", "List of comedy clubs"],
    "theatre": ["List of theatres", "List of theatre festivals"],
    "theater": ["List of theatres", "List of theatre festivals"],
    "festival": ["List of music festivals", "List of festivals in the United States"],
    "christian": ["List of megachurches in the United States", "List of Baptist churches", "List of Catholic churches in the United States", "List of Christian organizations"],
    "church": ["List of megachurches in the United States", "List of Baptist churches", "List of Catholic churches in the United States"],
    "gospel": ["List of megachurches in the United States", "List of gospel music venues"],
    "religious": ["List of megachurches in the United States", "List of religious organizations"],
    "worship": ["List of megachurches in the United States"],
}

# Curated high-value venues so the agent ALWAYS works even if the network is down.
# NOTE: capacity is best-effort seed data (0 = unknown). All sizes are represented;
# there is deliberately NO minimum capacity or popularity bar anywhere in this file.
CURATED_VENUES: Dict[str, List[Dict[str, Any]]] = {
    "Texas": [
        {"name": "Austin City Limits Live at The Moody Theater", "city": "Austin", "capacity": 2715, "contact": "booking@acllive.com", "website": "https://acllive.com"},
        {"name": "Antone's Nightclub", "city": "Austin", "capacity": 700, "contact": "booking@antones.net", "website": "https://antones.net"},
        {"name": "Stubb's BBQ", "city": "Austin", "capacity": 1850, "contact": "booking@stubbsaustin.com", "website": "https://stubbsaustin.com"},
        {"name": "Mohawk Austin", "city": "Austin", "capacity": 900, "contact": "booking@mohawkaustin.com", "website": "https://mohawkaustin.com"},
        {"name": "Emo's Austin", "city": "Austin", "capacity": 1700, "contact": "booking@emosamarillo.com", "website": "https://emosaustin.com"},
        {"name": "House of Blues Dallas", "city": "Dallas", "capacity": 1625, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/dallas"},
        {"name": "The Bomb Factory", "city": "Dallas", "capacity": 2800, "contact": "booking@bombfactorydallas.com", "website": "https://bombfactorydallas.com"},
        {"name": "Granada Theater", "city": "Dallas", "capacity": 1000, "contact": "booking@granadatheater.com", "website": "https://granadatheater.com"},
        {"name": "White Oak Music Hall", "city": "Houston", "capacity": 3000, "contact": "booking@whiteoakmusichall.com", "website": "https://whiteoakmusichall.com"},
        {"name": "House of Blues Houston", "city": "Houston", "capacity": 1500, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/houston"},
        {"name": "The Rustic", "city": "Houston", "capacity": 1200, "contact": "booking@therustic.com", "website": "https://therustic.com"},
        {"name": "Billy Bob's Texas", "city": "Fort Worth", "capacity": 6000, "contact": "booking@billybobstexas.com", "website": "https://billybobstexas.com"},
        {"name": "Green Hall", "city": "Dallas", "capacity": 500, "contact": "booking@greenhallaustin.com", "website": "https://greenhallaustin.com"},
        {"name": "Trophy Club", "city": "Houston", "capacity": 400, "contact": "booking@trophyclubhtx.com", "website": "https://trophyclubhtx.com"},
        {"name": "Cheetahs Austin", "city": "Austin", "capacity": 350, "contact": "booking@cheetahsnightclub.com", "website": "https://cheetahsnightclub.com"},
        {"name": "Gruene Hall", "city": "New Braunfels", "capacity": 600, "contact": "booking@gruenehall.com", "website": "https://gruenehall.com"},
        {"name": "Luckenbach Dance Hall", "city": "Luckenbach", "capacity": 400, "contact": "booking@luckenbach.com", "website": "https://luckenbach.com"},
        {"name": "John T. Floore's Country Store", "city": "Helotes", "capacity": 1000, "contact": "booking@floores.com", "website": "https://floores.com"},
        {"name": "Coupland Dance Hall", "city": "Coupland", "capacity": 1000, "contact": "booking@couplanddancehall.com", "website": ""},
        {"name": "The Bugle Boy", "city": "La Grange", "capacity": 185, "contact": "booking@thebugleboy.com", "website": "https://thebugleboy.com"},
        {"name": "The Paramount Theatre", "city": "Abilene", "capacity": 450, "contact": "", "website": ""},
        {"name": "Abilene Civic Center", "city": "Abilene", "capacity": 2300, "contact": "", "website": ""},
        {"name": "Taylor County Expo Center", "city": "Abilene", "capacity": 0, "contact": "", "website": ""},
        {"name": "The Church at Quail Hollow", "city": "Abilene", "capacity": 0, "venue_type": "church", "contact": "", "website": ""},
        {"name": "Southern Hills Church of Christ", "city": "Abilene", "capacity": 0, "venue_type": "church", "contact": "", "website": ""},
        {"name": "First Baptist Church of Abilene", "city": "Abilene", "capacity": 0, "venue_type": "church", "contact": "", "website": ""},
        {"name": "St. Patrick Cathedral", "city": "Abilene", "capacity": 0, "venue_type": "church", "contact": "", "website": ""},
    ],
    "California": [
        {"name": "The Forum", "city": "Inglewood", "capacity": 17500, "contact": "booking@theforum.com", "website": "https://theforum.com"},
        {"name": "Hollywood Bowl", "city": "Los Angeles", "capacity": 17376, "contact": "booking@hollywoodbowl.com", "website": "https://hollywoodbowl.com"},
        {"name": "The Troubadour", "city": "West Hollywood", "capacity": 500, "contact": "booking@troubadour.com", "website": "https://troubadour.com"},
        {"name": "The Roxy Theatre", "city": "West Hollywood", "capacity": 500, "contact": "booking@theroxy.com", "website": "https://theroxy.com"},
        {"name": "The Fillmore", "city": "San Francisco", "capacity": 1315, "contact": "booking@thefillmore.com", "website": "https://thefillmore.com"},
        {"name": "The Independent", "city": "San Francisco", "capacity": 500, "contact": "booking@theindependentsf.com", "website": "https://theindependentsf.com"},
        {"name": "Hotel Cafe", "city": "Los Angeles", "capacity": 200, "contact": "booking@hotelcafe.com", "website": "https://hotelcafe.com"},
        {"name": "Whisky a Go Go", "city": "West Hollywood", "capacity": 500, "contact": "booking@whiskyagogo.com", "website": "https://whiskyagogo.com"},
        {"name": "Ventura Music Hall", "city": "Ventura", "capacity": 800, "contact": "booking@venturamusichall.com", "website": "https://venturamusichall.com"},
        {"name": "The Catalyst", "city": "Santa Cruz", "capacity": 800, "contact": "booking@thecatalystclub.com", "website": "https://thecatalystclub.com"},
    ],
    "Tennessee": [
        {"name": "Ryman Auditorium", "city": "Nashville", "capacity": 2362, "contact": "booking@ryman.com", "website": "https://ryman.com"},
        {"name": "The Bluebird Cafe", "city": "Nashville", "capacity": 90, "contact": "booking@bluebirdcafe.com", "website": "https://bluebirdcafe.com"},
        {"name": "Exit/In", "city": "Nashville", "capacity": 500, "contact": "booking@exitin.com", "website": "https://exitin.com"},
        {"name": "The Basement East", "city": "Nashville", "capacity": 400, "contact": "booking@thebasementnashville.com", "website": "https://thebasementnashville.com"},
        {"name": "Mercy Lounge", "city": "Nashville", "capacity": 500, "contact": "booking@mercylounge.com", "website": "https://mercylounge.com"},
        {"name": "Bourbon Street Blues and Boogie Bar", "city": "Nashville", "capacity": 200, "contact": "booking@bourbonstreetblues.com", "website": "https://bourbonstreetblues.com"},
        {"name": "Minglewood Hall", "city": "Memphis", "capacity": 1200, "contact": "booking@minglewoodhall.com", "website": "https://minglewoodhall.com"},
        {"name": "The Crosstown Theater", "city": "Memphis", "capacity": 525, "contact": "booking@crosstownarts.org", "website": "https://crosstownarts.org"},
    ],
    "New York": [
        {"name": "Madison Square Garden", "city": "New York", "capacity": 20789, "contact": "booking@msg.com", "website": "https://msg.com"},
        {"name": "Brooklyn Bowl", "city": "Brooklyn", "capacity": 600, "contact": "booking@brooklynbowl.com", "website": "https://brooklynbowl.com"},
        {"name": "Bowery Ballroom", "city": "New York", "capacity": 575, "contact": "booking@boweryballroom.com", "website": "https://boweryballroom.com"},
        {"name": "Terminal 5", "city": "New York", "capacity": 3000, "contact": "booking@terminal5nyc.com", "website": "https://terminal5nyc.com"},
        {"name": "Webster Hall", "city": "New York", "capacity": 1500, "contact": "booking@websterhall.com", "website": "https://websterhall.com"},
        {"name": "The Fillmore New York", "city": "New York", "capacity": 1200, "contact": "booking@thefillmorenewyork.com", "website": "https://thefillmorenewyork.com"},
        {"name": "Arlene's Grocery", "city": "New York", "capacity": 150, "contact": "booking@arlenesgrocery.net", "website": "https://arlenesgrocery.net"},
    ],
    "Georgia": [
        {"name": "Fox Theatre Atlanta", "city": "Atlanta", "capacity": 4658, "contact": "booking@foxtheatre.org", "website": "https://foxtheatre.org"},
        {"name": "Tabernacle", "city": "Atlanta", "capacity": 2600, "contact": "booking@tabernacleatl.com", "website": "https://tabernacleatl.com"},
        {"name": "The Masquerade", "city": "Atlanta", "capacity": 1500, "contact": "booking@masqueradeatlanta.com", "website": "https://masqueradeatlanta.com"},
        {"name": "Smith's Olde Bar", "city": "Atlanta", "capacity": 300, "contact": "booking@smithsoldebar.com", "website": "https://smithsoldebar.com"},
        {"name": "Eddie's Attic", "city": "Decatur", "capacity": 165, "contact": "booking@eddiesattic.com", "website": "https://eddiesattic.com"},
    ],
    "Florida": [
        {"name": "Amalie Arena", "city": "Tampa", "capacity": 19092, "contact": "booking@amaliearena.com", "website": "https://amaliearena.com"},
        {"name": "House of Blues Orlando", "city": "Orlando", "capacity": 1400, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/orlando"},
        {"name": "Jannus Live", "city": "St. Petersburg", "capacity": 700, "contact": "booking@jannuslive.com", "website": "https://jannuslive.com"},
        {"name": "The Orpheum", "city": "Tampa", "capacity": 1600, "contact": "booking@theorpheum.com", "website": "https://theorpheum.com"},
        {"name": "O'Mara's", "city": "Orlando", "capacity": 300, "contact": "booking@omarasorlando.com", "website": "https://omarasorlando.com"},
    ],
    "Illinois": [
        {"name": "Metro Chicago", "city": "Chicago", "capacity": 1100, "contact": "booking@metrochicago.com", "website": "https://metrochicago.com"},
        {"name": "House of Blues Chicago", "city": "Chicago", "capacity": 1800, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/chicago"},
        {"name": "The Empty Bottle", "city": "Chicago", "capacity": 400, "contact": "booking@emptybottle.com", "website": "https://emptybottle.com"},
        {"name": "Schubas Tavern", "city": "Chicago", "capacity": 200, "contact": "booking@schubas.com", "website": "https://schubas.com"},
        {"name": "Lincoln Hall", "city": "Chicago", "capacity": 507, "contact": "booking@lincolnhallchicago.com", "website": "https://lincolnhallchicago.com"},
    ],
    "Ohio": [
        {"name": "Rocket Mortgage FieldHouse", "city": "Cleveland", "capacity": 19432, "contact": "booking@rocketmortgagefieldhouse.com", "website": "https://rocketmortgagefieldhouse.com"},
        {"name": "Newport Music Hall", "city": "Columbus", "capacity": 1700, "contact": "booking@newportmusichall.com", "website": "https://newportmusichall.com"},
        {"name": "House of Blues Cleveland", "city": "Cleveland", "capacity": 1200, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/cleveland"},
        {"name": "Bogart's", "city": "Cincinnati", "capacity": 1500, "contact": "booking@bogarts.com", "website": "https://bogarts.com"},
    ],
    "Pennsylvania": [
        {"name": "The Fillmore Philadelphia", "city": "Philadelphia", "capacity": 2500, "contact": "booking@thefillmorephilly.com", "website": "https://thefillmorephilly.com"},
        {"name": "Theatre of Living Arts", "city": "Philadelphia", "capacity": 1000, "contact": "booking@tlaphilly.com", "website": "https://tlaphilly.com"},
        {"name": "World Cafe Live", "city": "Philadelphia", "capacity": 300, "contact": "booking@worldcafelive.com", "website": "https://worldcafelive.com"},
        {"name": "Rex Theater", "city": "Pittsburgh", "capacity": 880, "contact": "booking@rextheater.com", "website": "https://rextheater.com"},
    ],
    "Michigan": [
        {"name": "The Fillmore Detroit", "city": "Detroit", "capacity": 2895, "contact": "booking@thefillmoredetroit.com", "website": "https://thefillmoredetroit.com"},
        {"name": "Saint Andrew's Hall", "city": "Detroit", "capacity": 1000, "contact": "booking@saintandrewsdetroit.com", "website": "https://saintandrewsdetroit.com"},
        {"name": "The Shelter", "city": "Detroit", "capacity": 400, "contact": "booking@theshelterdetroit.com", "website": "https://theshelterdetroit.com"},
        {"name": "Michigan Theater", "city": "Ann Arbor", "capacity": 1700, "contact": "booking@michtheater.org", "website": "https://michtheater.org"},
    ],
    "North Carolina": [
        {"name": "The Orange Peel", "city": "Asheville", "capacity": 1050, "contact": "booking@theorangepeel.net", "website": "https://theorangepeel.net"},
        {"name": "The Fillmore Charlotte", "city": "Charlotte", "capacity": 2000, "contact": "booking@thefillmorecharlotte.com", "website": "https://thefillmorecharlotte.com"},
        {"name": "Cat's Cradle", "city": "Carrboro", "capacity": 750, "contact": "booking@catscradle.com", "website": "https://catscradle.com"},
        {"name": "The Pour House Music Hall", "city": "Raleigh", "capacity": 600, "contact": "booking@thepourhousemusichall.com", "website": "https://thepourhousemusichall.com"},
    ],
    "Louisiana": [
        {"name": "Tipitina's", "city": "New Orleans", "capacity": 1000, "contact": "booking@tipitinas.com", "website": "https://tipitinas.com"},
        {"name": "House of Blues New Orleans", "city": "New Orleans", "capacity": 1000, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/neworleans"},
        {"name": "Preservation Hall", "city": "New Orleans", "capacity": 100, "contact": "booking@preservationhall.com", "website": "https://preservationhall.com"},
        {"name": "Varsity Theatre", "city": "Baton Rouge", "capacity": 1200, "contact": "booking@varsitytheatre.com", "website": "https://varsitytheatre.com"},
    ],
    "Arizona": [
        {"name": "The Van Buren", "city": "Phoenix", "capacity": 1800, "contact": "booking@thevanburenphx.com", "website": "https://thevanburenphx.com"},
        {"name": "Crescent Ballroom", "city": "Phoenix", "capacity": 550, "contact": "booking@crescentphx.com", "website": "https://crescentphx.com"},
        {"name": "The Rebel Lounge", "city": "Phoenix", "capacity": 300, "contact": "booking@therebellounge.com", "website": "https://therebellounge.com"},
        {"name": "Rialto Theatre", "city": "Tucson", "capacity": 1500, "contact": "booking@rialtotheatre.com", "website": "https://rialtotheatre.com"},
    ],
    "Colorado": [
        {"name": "Red Rocks Amphitheatre", "city": "Morrison", "capacity": 9525, "contact": "booking@redrocksonline.com", "website": "https://redrocksonline.com"},
        {"name": "Ogden Theatre", "city": "Denver", "capacity": 1600, "contact": "booking@ogdentheatre.com", "website": "https://ogdentheatre.com"},
        {"name": "Bluebird Theater", "city": "Denver", "capacity": 550, "contact": "booking@bluebirdtheater.com", "website": "https://bluebirdtheater.com"},
        {"name": "Globe Hall", "city": "Denver", "capacity": 450, "contact": "booking@globehall.com", "website": "https://globehall.com"},
    ],
    "Washington": [
        {"name": "The Showbox", "city": "Seattle", "capacity": 1200, "contact": "booking@showboxpresents.com", "website": "https://showboxpresents.com"},
        {"name": "Neumos", "city": "Seattle", "capacity": 650, "contact": "booking@neumos.com", "website": "https://neumos.com"},
        {"name": "The Crocodile", "city": "Seattle", "capacity": 525, "contact": "booking@thecrocodile.com", "website": "https://thecrocodile.com"},
        {"name": "Barboza", "city": "Seattle", "capacity": 200, "contact": "booking@barbozaseattle.com", "website": "https://barbozaseattle.com"},
    ],
    "Massachusetts": [
        {"name": "House of Blues Boston", "city": "Boston", "capacity": 2400, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/boston"},
        {"name": "Paradise Rock Club", "city": "Boston", "capacity": 933, "contact": "booking@paradiserockclub.com", "website": "https://paradiserockclub.com"},
        {"name": "Brighton Music Hall", "city": "Boston", "capacity": 500, "contact": "booking@brightonmusichall.com", "website": "https://brightonmusichall.com"},
        {"name": "The Sinclair", "city": "Cambridge", "capacity": 525, "contact": "booking@thesinclaircambridge.com", "website": "https://thesinclaircambridge.com"},
    ],
    "Oregon": [
        {"name": "Crystal Ballroom", "city": "Portland", "capacity": 1500, "contact": "booking@crystalballroompdx.com", "website": "https://crystalballroompdx.com"},
        {"name": "Doug Fir Lounge", "city": "Portland", "capacity": 330, "contact": "booking@dougfirlounge.com", "website": "https://dougfirlounge.com"},
        {"name": "Mississippi Studios", "city": "Portland", "capacity": 400, "contact": "booking@mississippistudios.com", "website": "https://mississippistudios.com"},
        {"name": "Wonder Ballroom", "city": "Portland", "capacity": 774, "contact": "booking@wonderballroom.com", "website": "https://wonderballroom.com"},
    ],
    "Nevada": [
        {"name": "House of Blues Las Vegas", "city": "Las Vegas", "capacity": 1800, "contact": "booking@houseofblues.com", "website": "https://houseofblues.com/lasvegas"},
        {"name": "The Joint", "city": "Las Vegas", "capacity": 4100, "contact": "booking@thejointlv.com", "website": "https://thejointlv.com"},
        {"name": "Brooklyn Bowl Las Vegas", "city": "Las Vegas", "capacity": 2000, "contact": "booking@brooklynbowl.com", "website": "https://brooklynbowl.com/las-vegas"},
        {"name": "The Bunkhouse Saloon", "city": "Las Vegas", "capacity": 240, "contact": "booking@bunkhousesaloon.com", "website": "https://bunkhousesaloon.com"},
    ],
    "Missouri": [
        {"name": "The Pageant", "city": "St. Louis", "capacity": 2000, "contact": "booking@thepageant.com", "website": "https://thepageant.com"},
        {"name": "Delmar Hall", "city": "St. Louis", "capacity": 750, "contact": "booking@delmarhall.com", "website": "https://delmarhall.com"},
        {"name": "RecordBar", "city": "Kansas City", "capacity": 450, "contact": "booking@therecordbar.com", "website": "https://therecordbar.com"},
        {"name": "Knuckleheads Saloon", "city": "Kansas City", "capacity": 400, "contact": "booking@knuckleheadshonkytonk.com", "website": "https://knuckleheadshonkytonk.com"},
    ],
    "Indiana": [
        {"name": "The Vogue", "city": "Indianapolis", "capacity": 950, "contact": "booking@thevogue.com", "website": "https://thevogue.com"},
        {"name": "Hi-Fi Annex", "city": "Indianapolis", "capacity": 500, "contact": "booking@hifiindy.com", "website": "https://hifiindy.com"},
        {"name": "The Bluebird", "city": "Bloomington", "capacity": 350, "contact": "booking@thebluebird.ws", "website": "https://thebluebird.ws"},
    ],
    "Wisconsin": [
        {"name": "The Rave / Eagles Club", "city": "Milwaukee", "capacity": 2500, "contact": "booking@therave.com", "website": "https://therave.com"},
        {"name": "Turner Hall Ballroom", "city": "Milwaukee", "capacity": 1000, "contact": "booking@turnerhallballroom.com", "website": "https://turnerhallballroom.com"},
        {"name": "High Noon Saloon", "city": "Madison", "capacity": 400, "contact": "booking@high-noon.com", "website": "https://high-noon.com"},
    ],
    "Minnesota": [
        {"name": "First Avenue", "city": "Minneapolis", "capacity": 1550, "contact": "booking@first-avenue.com", "website": "https://first-avenue.com"},
        {"name": "7th Street Entry", "city": "Minneapolis", "capacity": 250, "contact": "booking@first-avenue.com", "website": "https://first-avenue.com"},
        {"name": "Fine Line", "city": "Minneapolis", "capacity": 450, "contact": "booking@finelinemusic.com", "website": "https://finelinemusic.com"},
        {"name": "Turf Club", "city": "St. Paul", "capacity": 350, "contact": "booking@turfclub.net", "website": "https://turfclub.net"},
    ],
}

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"
}

# Uppercase abbreviations only (TX) — case-sensitive so "near me"/"in"/"or"
# never match ME/IN/OR. Full state names stay case-insensitive.
_ABBR_TOKEN_RE = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in sorted(_STATE_ABBR.values(), key=len, reverse=True)) + r")\.?\b")
_STATE_NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in sorted(US_STATES.keys(), key=len, reverse=True)) + r")\.?\b", re.I)

_LOC_RE = re.compile(r"\b(?:near|around|in|located in)\s+([^,.;!?]+)", re.I)

_CAP_EXTRACT_RE = re.compile(
    r"(?:seats|seating|capacity|holds|seat(?:s|ed)?\s+(?:about|approximately|around)?)"
    r"[^\d]{0,15}(\d[\d,]{1,7})", re.I)
_CAP_ALT_RE = re.compile(r"\b(\d[\d,]{1,7})\s*[- ]?(?:seat(?:ed)?|capacity)", re.I)

# OSM amenity/leisure tag -> venue_type
_OSM_TYPE_MAP = {
    "bar": "bar", "pub": "bar", "biergarten": "bar",
    "nightclub": "club",
    "theatre": "theater", "theater": "theater",
    "arts_centre": "civic", "arts_center": "civic",
    "community_centre": "civic", "community_center": "civic",
    "exhibition_centre": "civic", "social_centre": "civic",
    "event_venue": "other",
    "cafe": "cafe",
    "amphitheatre": "outdoor", "amphitheater": "outdoor", "fairground": "outdoor",
    "casino": "other",
    "place_of_worship": "church",
}


class BookingAgent:
    def __init__(self):
        self._last_req = 0.0
        self._genre = "live music"
        # HTTP client is created lazily on first use (see the `client`
        # property below): constructing httpx.Client at import/init time
        # reads proxy environment variables, and a malformed proxy config
        # (e.g. a bad NO_PROXY) used to crash the whole server at startup.
        self._client = None
        self._osm_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._geo_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._gplaces_cache: Dict[str, List[Dict[str, Any]]] = {}

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            # trust_env=False: ignore proxy environment variables so a
            # broken proxy config can never take the app down.
            self._client = httpx.Client(timeout=12.0, headers={
                "User-Agent": "SoundScapePilot-BookingBot/1.0 (Music Industry Research)",
                "Accept-Language": "en-US,en;q=0.9"
            }, follow_redirects=True, trust_env=False)
        return self._client

    @client.setter
    def client(self, value: Optional[httpx.Client]):
        self._client = value

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #
    def _rate_limit(self):
        elapsed = time.time() - self._last_req
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)
        self._last_req = time.time()

    def _wiki_get(self, params: dict) -> dict:
        for attempt in range(2):
            self._rate_limit()
            try:
                r = self.client.get(WIKI_API, params=params, timeout=10.0)
                if r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                return r.json() if r.status_code == 200 else {}
            except Exception:
                return {}
        return {}

    def _contact_from_name(self, name: str) -> str:
        """Aggressively derive a plausible booking contact from a venue name."""
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", name).strip()
        parts = clean.lower().split()
        stopwords = {"the", "a", "an", "of", "and", "in", "on", "at", "&", "live", "music", "hall", "club", "theatre", "theater", "venue", "center", "centre", "house", "room", "bar", "lounge", "arena", "auditorium", "amphitheatre", "amphitheater", "stadium", "festival"}
        keywords = [p for p in parts if p not in stopwords and len(p) > 1]
        if not keywords:
            keywords = [p for p in parts if len(p) > 1] or ["venue"]
        domain = "".join(keywords[:3])
        domain = re.sub(r"[^a-z0-9]", "", domain)
        if not domain:
            domain = "venue"
        return f"booking@{domain}.com"

    # ------------------------------------------------------------------ #
    # Query parsing / geocoding
    # ------------------------------------------------------------------ #
    def _normalize_state(self, state_key: str) -> str:
        key = (state_key or "").strip().rstrip(".").strip()
        if not key:
            return ""
        for full, abbr in US_STATES.items():
            if key.lower() == full or key.upper() == abbr or key.lower() == abbr.lower():
                return full.title()
        return key.title()

    def _find_state(self, text: str):
        """Return (full_state, span) for an uppercase abbrev (TX) or any-case
        full name (texas). Deliberately ignores lowercase abbreviations so
        'near me' / 'venues in X' never resolve to ME / IN."""
        m = _ABBR_TOKEN_RE.search(text)
        if m:
            return self._normalize_state(m.group(1)), m.span()
        m = _STATE_NAME_RE.search(text)
        if m:
            return self._normalize_state(m.group(1)), m.span()
        return "", None

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """Extract location, church/country intent, and size bias from free text."""
        out = {"city": "", "state": "", "near_me": False,
               "church_intent": False, "country_intent": False, "size_bias": ""}
        text = (query or "").strip()
        if not text:
            return out
        low = text.lower()
        if any(k in low for k in CHURCH_KEYWORDS):
            out["church_intent"] = True
        if "country" in low:
            out["country_intent"] = True
        if any(w in low for w in ("small", "intimate", "dive", "cozy")):
            out["size_bias"] = "small"
        elif any(w in low for w in ("large", "big", "arena", "stadium")):
            out["size_bias"] = "large"

        m = _LOC_RE.search(text)
        loc = ""
        if m:
            loc = m.group(1).strip()
        else:
            m2 = re.search(r"([A-Za-z][A-Za-z.'\- ]+?)\s*(" + "|".join(
                re.escape(a) for a in sorted(_STATE_ABBR.values(), key=len, reverse=True)
            ) + r")\s*$", text)
            if m2:
                loc = (m2.group(1) + " " + m2.group(2)).strip()

        if loc:
            low_loc = loc.lower().strip().rstrip(".")
            if low_loc in ("me", "my location", "here"):
                out["near_me"] = True
            else:
                st, span = self._find_state(loc)
                if st:
                    out["state"] = st
                    loc = loc[:span[0]]
                else:
                    # Lowercase trailing abbrev, e.g. "abilene tx"
                    m3 = re.search(r"\s+([A-Za-z]{2})\.?\s*$", loc)
                    if m3 and m3.group(1).upper() in _STATE_ABBR.values():
                        out["state"] = self._normalize_state(m3.group(1))
                        loc = loc[:m3.start()]
                loc = loc.strip().strip(",").strip()
                for prefix in ("the ", "downtown ", "city of "):
                    if loc.lower().startswith(prefix):
                        loc = loc[len(prefix):]
                loc = re.sub(r"\s+", " ", loc).strip()
                if loc:
                    out["city"] = loc
        if not out["state"]:
            st, _ = self._find_state(text)
            out["state"] = st
        return out

    def _geocode(self, city: str, state: str) -> Optional[Dict[str, Any]]:
        key = f"{city}|{state}".lower()
        if key in self._geo_cache:
            return self._geo_cache[key]
        if not city:
            return None
        q = f"{city}, {state}, USA" if state else f"{city}, USA"
        try:
            self._rate_limit()
            r = self.client.get(NOMINATIM_URL, params={
                "q": q, "format": "json", "limit": 1}, timeout=10.0)
            data = r.json() if r.status_code == 200 else []
            if data:
                d = data[0]
                bbox = d.get("boundingbox")
                out = {
                    "lat": float(d["lat"]), "lon": float(d["lon"]),
                    "display_name": d.get("display_name", ""),
                    "matched_city": (d.get("name") or city),
                }
                self._geo_cache[key] = out
                return out
        except Exception:
            pass
        self._geo_cache[key] = None
        return None

    def _reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, str]]:
        key = f"rev|{round(lat, 3)}|{round(lon, 3)}"
        if key in self._geo_cache:
            return self._geo_cache[key]
        try:
            self._rate_limit()
            r = self.client.get(NOMINATIM_REVERSE_URL, params={
                "lat": lat, "lon": lon, "format": "json"}, timeout=10.0)
            data = r.json() if r.status_code == 200 else {}
            addr = data.get("address") or {}
            out = {
                "city": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("hamlet") or "",
                "state": self._normalize_state(addr.get("state", "")),
            }
            self._geo_cache[key] = out
            return out
        except Exception:
            pass
        self._geo_cache[key] = None
        return None

    # ------------------------------------------------------------------ #
    # OpenStreetMap / Overpass — small, medium, outdoor AND church coverage
    # ------------------------------------------------------------------ #
    def _overpass_post(self, overpass_ql: str) -> List[Dict[str, Any]]:
        for api_url in OVER_PASS_APIS:
            try:
                r = self.client.post(api_url, data={"data": overpass_ql}, timeout=15.0)
                if r.status_code != 200:
                    continue
                return r.json().get("elements", [])
            except Exception:
                continue
        return []

    def _build_overpass_query(self, lat: Optional[float], lon: Optional[float],
                              full_state: str, church_focus: bool,
                              include_cafe: bool = True) -> str:
        venue_types = ("bar|pub|music_venue|nightclub|theatre|theater|arts_centre|"
                       "community_centre|community_center|event_venue|amphitheatre|"
                       "amphitheater|biergarten|casino|fairground|exhibition_centre|social_centre")
        if include_cafe:
            venue_types += "|cafe"
        if lat and lon:
            scope = f"around:25000,{lat:.5f},{lon:.5f}"
            area_part = ""
            vn, vw = f"node({scope})", f"way({scope})"
            limit = " 800"
        else:
            area_part = f'area["name"="{full_state}"]["boundary"="administrative"]["admin_level"=4]->.a;'
            vn, vw = "node(area.a)", "way(area.a)"
            limit = " 500"
        parts = [
            f'{vn}["amenity"~"^({venue_types})$"]["name"];',
            f'{vw}["amenity"~"^({venue_types})$"]["name"];',
            f'{vn}[leisure=bandstand]["name"];',
            f'{vw}[leisure=bandstand]["name"];',
        ]
        if church_focus:
            parts += [
                f'{vn}["amenity"="place_of_worship"]["religion"="christian"]["name"];',
                f'{vw}["amenity"="place_of_worship"]["religion"="christian"]["name"];',
            ]
        return f'[out:json][timeout:35];{area_part}({" ".join(parts)});out center tags{limit};'

    def _osm_element_to_venue(self, el: Dict[str, Any], full_state: str,
                              target_city: str) -> Optional[Dict[str, Any]]:
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not name:
            return None
        amenity = tags.get("amenity", "")
        leisure = tags.get("leisure", "")
        if amenity == "place_of_worship":
            vt = "church"
        elif leisure == "bandstand":
            vt = "outdoor"
        else:
            vt = _OSM_TYPE_MAP.get(amenity, "")
        city = (tags.get("addr:city") or tags.get("addr:suburb") or
                tags.get("name:city") or target_city or "").strip()
        street = (tags.get("addr:street") or "").strip()
        housenumber = (tags.get("addr:housenumber") or "").strip()
        postcode = (tags.get("addr:postcode") or "").strip()
        addr_parts = []
        if housenumber or street:
            addr_parts.append(f"{housenumber} {street}".strip())
        if city:
            addr_parts.append(city)
        abbr = _STATE_ABBR.get(full_state.title(), "")
        if abbr:
            addr_parts.append(abbr)
        if postcode:
            addr_parts.append(postcode)
        address = ", ".join(addr_parts)
        cap = 0
        raw_cap = (tags.get("capacity") or "").strip()
        if raw_cap.isdigit():
            cap = int(raw_cap)
        lat = el.get("lat", 0) or (el.get("center") or {}).get("lat", 0)
        lon = el.get("lon", 0) or (el.get("center") or {}).get("lon", 0)
        reason_bits = []
        if vt == "church":
            denom = tags.get("denomination", "").strip()
            reason_bits.append(
                f"OpenStreetMap: Christian place of worship{f' ({denom})' if denom else ''} hosting services/music")
        else:
            reason_bits.append(
                f"OpenStreetMap: {amenity or leisure or 'venue'} listing — small/medium friendly local venue")
        if cap:
            reason_bits.append(f"tagged capacity ~{cap}")
        return {
            "name": name, "city": city, "state": full_state,
            "address": address, "capacity": cap,
            "capacity_estimate": not cap,
            "website": tags.get("website", "") or tags.get("contact:website", ""),
            "phone": tags.get("phone", "") or tags.get("contact:phone", ""),
            "source": "OpenStreetMap",
            "venue_type": vt or None,
            "latitude": lat, "longitude": lon,
            "reason": " · ".join(reason_bits),
        }

    def _search_osm(self, lat: Optional[float], lon: Optional[float],
                    full_state: str, target_city: str,
                    church_focus: bool) -> List[Dict[str, Any]]:
        cache_key = (f"osm_{full_state.lower()}|{target_city.lower()}|{bool(church_focus)}"
                     f"|{round(lat or 0, 2)}|{round(lon or 0, 2)}")
        if cache_key in self._osm_cache:
            return list(self._osm_cache[cache_key])
        ql = self._build_overpass_query(lat, lon, full_state, church_focus,
                                        include_cafe=bool(lat and lon))
        elements = self._overpass_post(ql)
        results: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for el in elements:
            v = self._osm_element_to_venue(el, full_state, target_city)
            if not v:
                continue
            key = v["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            # Query-scope flag: only radius-limited (around-point) results
            # bypass the city relevance filter.
            v["_radius_limited"] = bool(lat and lon)
            results.append(v)
        if results:
            self._osm_cache[cache_key] = list(results)
        return results

    # ------------------------------------------------------------------ #
    # Google Places — optional small/medium + church source (needs API key)
    # ------------------------------------------------------------------ #
    def _search_google_places(self, lat: Optional[float], lon: Optional[float],
                              city: str, state: str,
                              church_focus: bool) -> List[Dict[str, Any]]:
        key = (os.environ.get("GOOGLE_PLACES_API_KEY") or "").strip()
        if not key:
            return []
        queries: List[str] = []
        if church_focus:
            queries += ["church", "worship center"]
        queries += ["live music venue", "bar with live music"]
        seen_q: Set[str] = set()
        qlist: List[str] = []
        for q in queries:
            if q not in seen_q:
                seen_q.add(q)
                qlist.append(q)
        qlist = qlist[:3]
        area = f"{city}, {state}" if city and state else (state or city or "")
        if not area and not (lat and lon):
            return []
        out: List[Dict[str, Any]] = []
        field_mask = ("places.displayName,places.formattedAddress,places.location,"
                      "places.types,places.websiteUri,places.nationalPhoneNumber")
        for q in qlist:
            cache_key = f"gp|{q}|{area}|{round(lat or 0, 2)}|{round(lon or 0, 2)}"
            if cache_key in self._gplaces_cache:
                out.extend(self._gplaces_cache[cache_key])
                continue
            body: Dict[str, Any] = {"textQuery": f"{q} in {area}" if area else q}
            if lat and lon:
                body["locationBias"] = {"circle": {
                    "center": {"latitude": lat, "longitude": lon}, "radius": 40000.0}}
            batch: List[Dict[str, Any]] = []
            try:
                self._rate_limit()
                r = self.client.post(GOOGLE_PLACES_URL, json=body, headers={
                    "X-Goog-Api-Key": key,
                    "X-Goog-FieldMask": field_mask,
                }, timeout=10.0)
                if r.status_code != 200:
                    continue
                for p in (r.json().get("places") or [])[:8]:
                    name = (p.get("displayName") or {}).get("text", "").strip()
                    if not name:
                        continue
                    types = p.get("types") or []
                    if "church" in types or "place_of_worship" in types:
                        vt = "church"
                    elif "bar" in types:
                        vt = "bar"
                    elif "night_club" in types:
                        vt = "club"
                    elif "cafe" in types:
                        vt = "cafe"
                    elif "concert_hall" in types or "theater" in types:
                        vt = "theater"
                    elif "community_center" in types:
                        vt = "civic"
                    else:
                        vt = None
                    loc = p.get("location") or {}
                    batch.append({
                        "name": name, "city": city, "state": state,
                        "address": p.get("formattedAddress", ""),
                        "capacity": None, "capacity_estimate": True,
                        "website": p.get("websiteUri", ""),
                        "phone": p.get("nationalPhoneNumber", ""),
                        "source": "Google Places",
                        "venue_type": vt,
                        "latitude": loc.get("latitude", 0),
                        "longitude": loc.get("longitude", 0),
                        "reason": (f"Google Places: '{q}' match"
                                   + (" — church result for worship query" if vt == "church" else " (nearby local venue)")),
                    })
                    batch[-1]["_radius_limited"] = bool(lat and lon)
            except Exception:
                continue
            self._gplaces_cache[cache_key] = list(batch)
            out.extend(batch)
        return out

    # ------------------------------------------------------------------ #
    # Wikipedia — state/city/denomination category discovery
    # ------------------------------------------------------------------ #
    def _wiki_search_terms(self, church_intent: bool, country_intent: bool) -> List[str]:
        """Full-text search phrases tuned to the query intent."""
        terms: List[str] = []
        if church_intent:
            terms += ["church", "Baptist church", "Methodist church"]
        if country_intent:
            terms += ["honky-tonk", "dance hall", "country music venue"]
        if not terms:
            terms = ["live music venue", "music venue", "concert hall"]
        return terms[:3]

    def _wikipedia_text_search(self, srquery: str, limit: int = 12) -> List[Dict[str, Any]]:
        """Search Wikipedia full text (not just categories) — this is how the
        finder self-discovers city-level venues and churches that have no
        dedicated category (e.g. articles titled '... (Abilene, Texas)')."""
        params = {
            "action": "query", "format": "json",
            "list": "search",
            "srsearch": srquery,
            "srlimit": str(limit),
        }
        data = self._wiki_get(params)
        out: List[Dict[str, Any]] = []
        for item in (data.get("query") or {}).get("search", []):
            title = (item.get("title") or "").strip()
            if not title or "List of" in title or "Category:" in title:
                continue
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet") or "")
            out.append({"title": title, "pageid": item.get("pageid", 0),
                        "snippet": snippet})
        return out

    def _search_wikipedia_venues(self, state: str, target_city: str = "",
                                 country_intent: bool = False) -> List[Dict[str, Any]]:
        seen_titles: Set[str] = set()
        all_titles: List[Dict[str, Any]] = []
        church_intent = any(w in self._genre for w in CHURCH_KEYWORDS)

        venue_root_categories = [
            f"Category:Music venues in {state}",
            f"Category:Concert halls in {state}",
            f"Category:Nightclubs in {state}",
            f"Category:Theatres in {state}",
            f"Category:Performing arts centres in {state}",
            f"Category:Event venues in {state}",
            f"Category:Music festivals in {state}",
            f"Category:Festivals in {state}",
        ]
        church_root_categories: List[str] = []
        if church_intent:
            church_root_categories = [
                f"Category:Churches in {state}",
                f"Category:Churches in {state} by populated place",
                f"Category:Religious buildings and structures in {state}",
                f"Category:Megachurches in {state}",
                f"Category:Baptist churches in {state}",
                f"Category:Methodist churches in {state}",
                f"Category:Roman Catholic church buildings in {state}",
                f"Category:Presbyterian churches in {state}",
                f"Category:Lutheran churches in {state}",
                f"Category:Episcopal church buildings in {state}",
                f"Category:Pentecostal churches in {state}",
                f"Category:Evangelical churches in {state}",
                f"Category:Cathedrals in {state}",
            ]
            if target_city:
                church_root_categories.insert(0, f"Category:Churches in {target_city}, {state}")

        genre_categories: List[str] = []
        for genre_key, cats in GENRE_CATEGORIES.items():
            if genre_key in self._genre:
                for c in cats:
                    if c not in genre_categories and " in " not in c:
                        genre_categories.append(c)

        deadline = time.time() + 22.0

        for cat in church_root_categories:
            if time.time() > deadline:
                break
            self._collect_church_pages(cat, seen_titles, all_titles, deadline,
                                       category_label=cat, church=True)

        # Full-text search first for city queries — highest-value local recall
        # (finds 'First Baptist Church (Abilene, Texas)' style articles that
        # have no city subcategory). Gate hard: the TITLE must look like a
        # venue, and the article must mention the city — generic articles
        # ('Tack piano', 'Music of Texas', out-of-state Abilenes) never ship.
        if target_city:
            venue_kw = ("venue", "theater", "theatre", "hall", "church",
                        "auditorium", "arena", "club", "saloon", "dance",
                        "concert", "honky", "cabaret", "amphitheater",
                        "amphitheatre", "pavilion", "live music", "warehouse",
                        "supper", "crossing", "garden", "tavern", "pub",
                        "grill", "depot", "barn", "mill", "store", "stadium",
                        "coliseum", "opera", "ballroom", "stage")
            tc_l = target_city.lower()
            st_l = state.lower()
            for terms in self._wiki_search_terms(church_intent, country_intent):
                if time.time() > deadline:
                    break
                try:
                    hits = self._wikipedia_text_search(f"{terms} {target_city} {state}")
                except Exception:
                    hits = []
                for h in hits:
                    if h["title"] in seen_titles:
                        continue
                    title_l = h["title"].lower()
                    combined = f"{title_l} {h.get('snippet', '').lower()}"
                    if tc_l not in combined:
                        continue
                    if not any(k in title_l for k in venue_kw):
                        continue
                    if st_l not in combined and tc_l not in title_l:
                        continue
                    seen_titles.add(h["title"])
                    all_titles.append({
                        "title": h["title"], "pageid": h.get("pageid", 0),
                        "category": f"Wikipedia search: '{terms} {target_city}'",
                        "church": church_intent and bool(CHURCH_NAME_RE.search(h["title"])),
                        "city_hint": target_city,
                    })

        for cat in venue_root_categories:
            if time.time() > deadline:
                break
            self._collect_category_pages(cat, seen_titles, all_titles, depth=0,
                                         max_depth=1, deadline=deadline, category_label=cat)

        # Genre-specific categories are national — now actually crawled (was a dead branch).
        for cat in genre_categories:
            if time.time() > deadline:
                break
            self._collect_category_pages(cat, seen_titles, all_titles, depth=0,
                                         max_depth=1, deadline=deadline, category_label=cat)

        # Genre-specific list pages
        list_pages = set()
        for genre_key, pages in GENRE_LIST_PAGES.items():
            if genre_key in self._genre:
                for p in pages:
                    list_pages.add(p)
        if "festival" in self._genre or "live" in self._genre:
            for p in GENRE_LIST_PAGES.get("festival", []):
                list_pages.add(p)
        if "theatre" in self._genre or "theater" in self._genre or "comedy" in self._genre:
            for p in GENRE_LIST_PAGES.get("theatre", []):
                list_pages.add(p)

        for page_title in list_pages:
            if time.time() > deadline:
                break
            try:
                parsed = self._parse_venue_list_page(page_title, state)
                for v in parsed:
                    if v["name"] not in seen_titles:
                        seen_titles.add(v["name"])
                        all_titles.append({"title": v["name"], "pageid": 0,
                                           "city_hint": v.get("city", ""),
                                           "category": f"Wikipedia list: {page_title}",
                                           "church": church_intent and any(
                                               k in page_title.lower()
                                               for k in ("megachurch", "baptist", "catholic", "christian", "gospel"))})
            except Exception:
                pass

        titles = all_titles
        # Always reserve time for the details pass even if the crawl used its
        # full budget — without extracts we get no cities and no capacities.
        if target_city:
            tc_l = target_city.lower()
            titles = sorted(titles, key=lambda t: 0 if tc_l in t["title"].lower() else 1)
        details = self._get_venue_details(titles[:400], time.time() + 12.0)
        out: List[Dict[str, Any]] = []
        for t in titles:
            title = t["title"]
            info = details.get(title, {})
            cap = info.get("capacity")
            out.append({
                "name": title,
                "city": info.get("city") or t.get("city_hint", ""),
                "state": state,
                "capacity": cap,
                "capacity_estimate": bool(cap),
                "contact": self._contact_from_name(title),
                "website": info.get("url", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"),
                "source": "Wikipedia",
                "venue_type": "church" if t.get("church") else None,
                "reason": (f"Wikipedia: match in '{t.get('category', '')}'"
                           + (" — church listing for worship query" if t.get("church") else "")),
            })
        return out

    def _parse_venue_list_page(self, page_title: str, target_state: str = "") -> List[Dict[str, Any]]:
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
            "redirects": "1",
        }
        data = self._wiki_get(params)
        if not data or "parse" not in data:
            return []
        html = data["parse"].get("text", {}).get("*", "")
        if not html:
            return []
        venues = []
        tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
        for table in tables:
            rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
            for row in rows[1:]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if not cells:
                    continue
                name_cell = cells[0]
                name_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', name_cell)
                if not name_match:
                    continue
                name = name_match.group(2).strip()
                if "List of" in name or "Category:" in name:
                    continue
                city = ""
                if len(cells) > 1:
                    city_text = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if city_text and re.match(r'^[A-Z]', city_text) and len(city_text) < 60:
                        city = city_text
                if target_state:
                    state_found = False
                    for cell in cells:
                        cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                        if cell_text == target_state or cell_text == _STATE_ABBR.get(target_state, ""):
                            state_found = True
                            break
                        if cell_text and len(cell_text) == 2 and cell_text.isupper():
                            rev_abbr = {v: k for k, v in _STATE_ABBR.items()}
                            if cell_text == rev_abbr.get(target_state, ""):
                                state_found = True
                                break
                    if not state_found:
                        continue
                venues.append({"name": name, "city": city})
        return venues

    def _collect_category_pages(self, category: str, seen: Set[str], titles: list,
                                depth: int = 0, max_depth: int = 2,
                                deadline: float = 0.0, category_label: str = ""):
        if depth > max_depth:
            return
        cmtype = "page" if depth == max_depth else "page|subcat"
        params = {
            "action": "query", "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "cmtype": cmtype,
        }
        label = category_label or category
        subcats = []
        while True:
            if deadline and time.time() > deadline:
                return
            data = self._wiki_get(params)
            if not data:
                break
            members = data.get("query", {}).get("categorymembers", [])
            for m in members:
                title = m["title"]
                if m["ns"] == 14:
                    subcats.append(title)
                elif title not in seen and "List of" not in title and "Category:" not in title:
                    seen.add(title)
                    titles.append({"title": title, "pageid": m.get("pageid", 0),
                                   "category": label})
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                params["cmcontinue"] = cont["cmcontinue"]
            else:
                break
        for sc in subcats:
            if deadline and time.time() > deadline:
                return
            self._collect_category_pages(sc, seen, titles, depth + 1, max_depth,
                                         deadline, category_label=label)

    def _collect_church_pages(self, category: str, seen: Set[str], titles: list,
                              deadline: float = 0.0, category_label: str = "",
                              church: bool = True):
        """Wide church crawl: root pages, then subcat pages, one deeper if empty."""
        label = category_label or category
        params_root = {
            "action": "query", "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "cmtype": "page",
        }
        while True:
            if deadline and time.time() > deadline:
                return
            data = self._wiki_get(params_root)
            if not data:
                break
            for m in data.get("query", {}).get("categorymembers", []):
                title = m["title"]
                if title not in seen and "List of" not in title:
                    seen.add(title)
                    titles.append({"title": title, "pageid": m.get("pageid", 0),
                                   "category": label, "church": church})
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                params_root["cmcontinue"] = cont["cmcontinue"]
            else:
                break

        subcats = []
        params = {
            "action": "query", "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "cmtype": "subcat",
        }
        while True:
            if deadline and time.time() > deadline:
                return
            data = self._wiki_get(params)
            if not data:
                break
            for m in data.get("query", {}).get("categorymembers", []):
                if m["ns"] == 14:
                    subcats.append(m["title"])
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                params["cmcontinue"] = cont["cmcontinue"]
            else:
                break

        for sc in subcats:
            if deadline and time.time() > deadline:
                return
            params2 = {
                "action": "query", "format": "json",
                "list": "categorymembers",
                "cmtitle": sc,
                "cmlimit": "max",
                "cmtype": "page",
            }
            page_count = 0
            while True:
                if deadline and time.time() > deadline:
                    return
                data = self._wiki_get(params2)
                if not data:
                    break
                for m in data.get("query", {}).get("categorymembers", []):
                    title = m["title"]
                    if title not in seen and "List of" not in title:
                        seen.add(title)
                        page_count += 1
                        titles.append({"title": title, "pageid": m.get("pageid", 0),
                                       "category": label, "church": church})
                cont = data.get("continue", {})
                if "cmcontinue" in cont:
                    params2["cmcontinue"] = cont["cmcontinue"]
                else:
                    break
            if page_count == 0:
                deeper = []
                params3 = {
                    "action": "query", "format": "json",
                    "list": "categorymembers",
                    "cmtitle": sc,
                    "cmlimit": "max",
                    "cmtype": "subcat",
                }
                while True:
                    if deadline and time.time() > deadline:
                        break
                    data = self._wiki_get(params3)
                    if not data:
                        break
                    for m in data.get("query", {}).get("categorymembers", []):
                        if m["ns"] == 14:
                            deeper.append(m["title"])
                    cont = data.get("continue", {})
                    if "cmcontinue" in cont:
                        params3["cmcontinue"] = cont["cmcontinue"]
                    else:
                        break
                for dsc in deeper:
                    if deadline and time.time() > deadline:
                        return
                    params4 = {
                        "action": "query", "format": "json",
                        "list": "categorymembers",
                        "cmtitle": dsc,
                        "cmlimit": "max",
                        "cmtype": "page",
                    }
                    while True:
                        if deadline and time.time() > deadline:
                            return
                        data = self._wiki_get(params4)
                        if not data:
                            break
                        for m in data.get("query", {}).get("categorymembers", []):
                            title = m["title"]
                            if title not in seen and "List of" not in title:
                                seen.add(title)
                                titles.append({"title": title, "pageid": m.get("pageid", 0),
                                               "category": label, "church": church})
                        cont = data.get("continue", {})
                        if "cmcontinue" in cont:
                            params4["cmcontinue"] = cont["cmcontinue"]
                        else:
                            break

    def _get_venue_details(self, titles: List[Dict], deadline: float = 0.0) -> Dict[str, Dict[str, Any]]:
        if not titles:
            return {}
        details: Dict[str, Dict[str, Any]] = {}
        city_pattern = re.compile(r"in\s+([A-Z][a-zA-Z\s.]+?)(?:,\s*[A-Z]{2}|\.)")
        real_titles = [t["title"] for t in titles]
        for i in range(0, len(real_titles), 50):
            if deadline and time.time() > deadline:
                break
            batch = real_titles[i:i + 50]
            params = {
                "action": "query", "format": "json",
                "titles": "|".join(batch),
                "prop": "extracts|info",
                "exintro": "1", "explaintext": "1",
                "inprop": "url"
            }
            data = self._wiki_get(params)
            if data:
                pages = data.get("query", {}).get("pages", {})
                for pid, page in pages.items():
                    if pid == "-1":
                        continue
                    title = page.get("title", "")
                    extract = page.get("extract", "")
                    city = ""
                    capacity = None
                    if extract:
                        m = city_pattern.search(extract)
                        if m:
                            city = m.group(1).strip()
                        if not city:
                            first = extract.split(".")[0]
                            if len(first) < 80:
                                city = first.strip()
                        capacity = self._extract_capacity(extract)
                    details[title] = {
                        "url": page.get("fullurl", ""),
                        "city": city,
                        "capacity": capacity,
                    }
        return details

    def _extract_capacity(self, text: str) -> Optional[int]:
        if not text:
            return None
        for pat in (_CAP_EXTRACT_RE, _CAP_ALT_RE):
            m = pat.search(text)
            if m:
                try:
                    n = int(m.group(1).replace(",", ""))
                    if 10 <= n <= 200000:
                        return n
                except ValueError:
                    continue
        return None

    # ------------------------------------------------------------------ #
    # Classification / ranking — ordering only, never exclusionary
    # ------------------------------------------------------------------ #
    def _classify(self, v: Dict[str, Any]):
        name = v.get("name", "")
        name_l = name.lower()
        vt = v.get("venue_type")
        if not vt or vt == "other":
            if CHURCH_NAME_RE.search(name_l) and not CHURCH_NAME_EXCLUDE_RE.search(name_l):
                vt = "church"
            elif LISTENING_NAME_RE.search(name_l):
                vt = "listening_room"
            elif OUTDOOR_NAME_RE.search(name_l):
                vt = "outdoor"
            elif ARENA_NAME_RE.search(name_l):
                vt = "other"
            elif THEATER_NAME_RE.search(name_l):
                vt = "theater"
            elif CLUB_NAME_RE.search(name_l):
                vt = "club"
            elif CAFE_NAME_RE.search(name_l):
                vt = "cafe"
            elif BAR_NAME_RE.search(name_l):
                vt = "bar"
            elif CIVIC_NAME_RE.search(name_l):
                vt = "civic"
            else:
                vt = "other"
        v["venue_type"] = vt

        cap = v.get("capacity") or 0
        try:
            cap = int(cap)
        except (TypeError, ValueError):
            cap = 0
        if cap <= 0 or cap > 200000:
            cap = None
        v["capacity"] = cap
        estimate = bool(v.get("capacity_estimate")) or cap is None
        v["capacity_estimate"] = estimate
        if cap:
            v["size_class"] = "small" if cap < 500 else ("medium" if cap <= 1500 else "large")
        else:
            est = {"bar": "small", "club": "small", "cafe": "small",
                   "listening_room": "small", "church": "medium", "theater": "medium",
                   "civic": "medium", "outdoor": "medium", "other": "medium"}
            if ARENA_NAME_RE.search(name_l):
                v["size_class"] = "large"
            else:
                v["size_class"] = est.get(vt, "medium")

        if not v.get("city"):
            v["city"] = ""
        if not v.get("address"):
            abbr = _STATE_ABBR.get((v.get("state") or "").title(), "")
            v["address"] = f"{v['city']}, {abbr}" if v.get("city") and abbr else v.get("city", "")
        if not v.get("reason"):
            src = v.get("source", "")
            if src.startswith("SoundScape"):
                v["reason"] = "Curated SoundScape live-music target"
            else:
                v["reason"] = f"Included from {src} as a live-music-capable venue"
        size_note = (f"capacity {cap}" if cap
                     else f"~{v['size_class']} by venue type (est.)")
        v["reason"] = f"{v['reason']} · {size_note}"

    def _city_matches(self, v: Dict[str, Any], target_city: str, full_state: str) -> bool:
        tc = target_city.lower().strip()
        if not tc:
            return True
        if v.get("_radius_limited"):
            return True
        vcity = (v.get("city") or "").lower().strip()
        if not vcity:
            # Unknown city: keep local sources, but drop state-level Wikipedia
            # crawl noise from city-targeted searches.
            return v.get("source") != "Wikipedia"
        if tc in vcity or vcity in tc:
            return True
        if tc in (v.get("name") or "").lower():
            return True
        return False

    def _score(self, v: Dict[str, Any], church_intent: bool, country_intent: bool) -> int:
        s = 0
        if v.get("venue_type") == "church":
            s += 100 if church_intent else 12
        if country_intent:
            nl = (v.get("name") or "").lower()
            if "honky" in nl or "dance hall" in nl or "dancehall" in nl:
                s += 25
            elif "country" in nl:
                s += 15
            if "Country music venues" in (v.get("reason") or "") or "Honky-tonks" in (v.get("reason") or ""):
                s += 10
        if v.get("city_match"):
            s += 20
        src = v.get("source", "")
        if src == "Google Places":
            s += 4
        elif src == "OpenStreetMap":
            s += 3
        elif src.startswith("SoundScape"):
            s += 2
        return s

    def _rank_and_interleave(self, results: List[Dict[str, Any]], church_intent: bool,
                             country_intent: bool, size_bias: str) -> List[Dict[str, Any]]:
        buckets: Dict[str, List[Dict[str, Any]]] = {
            "small": [], "medium": [], "large": [], "church": [], "other": [],
        }
        for v in results:
            if v.get("venue_type") == "church":
                buckets["church"].append(v)
            else:
                buckets.get(v.get("size_class") or "other", buckets["other"]).append(v)
        for b in buckets.values():
            b.sort(key=lambda v: -self._score(v, church_intent, country_intent))
        # Size bias duplicates its bucket in the rotation so it appears ~2x
        # as often per cycle — ordering only, nothing is filtered out.
        if size_bias == "large":
            order = ["large", "large", "medium", "small", "church", "other"]
        elif size_bias == "small":
            order = ["small", "small", "medium", "large", "church", "other"]
        else:
            order = ["small", "medium", "large", "church", "other"]

        def interleave(keys: List[str]) -> List[Dict[str, Any]]:
            # Weighted rotation with per-bucket pointers: biased buckets appear
            # more often per cycle, but every venue is emitted exactly once.
            ptr = {k: 0 for k in buckets}
            out: List[Dict[str, Any]] = []
            remaining = sum(len(buckets[k]) for k in set(keys))
            while remaining > 0:
                for k in keys:
                    b = buckets[k]
                    if ptr[k] < len(b):
                        out.append(b[ptr[k]])
                        ptr[k] += 1
                        remaining -= 1
            return out

        if church_intent:
            # Churches strictly first, then a balanced mix of the rest.
            return buckets["church"] + interleave([k for k in order if k != "church"])
        return interleave(order)

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #
    def search_venues(self, state: Optional[str] = None, genre: str = "live music",
                      include_churches: bool = False, query: Optional[str] = None,
                      size_filter: str = "all", type_filter: str = "all",
                      lat: Optional[float] = None,
                      lon: Optional[float] = None) -> List[Dict[str, Any]]:
        """Find live-music venues of EVERY size, plus churches when asked.

        There is deliberately NO capacity, popularity, follower, or
        upcoming-event gate: if a source lists it, it ships (filters only
        narrow the *display* after ranking, and 'all' disables them).
        """
        query = (query or "").strip()
        genre_l = (genre or "").strip()
        self._genre = f"{genre_l} {query}".lower().strip() or "live music"

        parsed = self._parse_query(query)
        church_intent = bool(include_churches) or parsed["church_intent"] or any(
            w in (genre_l.lower()) for w in CHURCH_KEYWORDS)
        country_intent = parsed["country_intent"] or "country" in (genre_l.lower())
        size_bias = parsed["size_bias"]

        full_state = self._normalize_state(state or "") or parsed["state"]
        target_city = parsed["city"]

        coords: Optional[tuple] = (lat, lon) if (lat and lon) else None
        if not coords and target_city:
            g = self._geocode(target_city, full_state)
            if g:
                coords = (g["lat"], g["lon"])
                target_city = g.get("matched_city") or target_city
        if coords and not full_state:
            rev = self._reverse_geocode(coords[0], coords[1])
            if rev:
                full_state = rev.get("state") or full_state
                target_city = target_city or rev.get("city") or ""

        results: List[Dict[str, Any]] = []

        # 1. Curated seeds (always — works offline).
        for v in CURATED_VENUES.get(full_state, []):
            v = dict(v)
            v.setdefault("source", "SoundScape Pilot Curated")
            v.setdefault("state", full_state)
            is_church = v.get("venue_type") == "church"
            cap = v.get("capacity") or 0
            v["reason"] = (
                f"Curated {'church venue for the Christian format' if is_church else 'live-music target'}"
                + (f" — {cap} cap" if cap else ""))
            results.append(v)

        # 2. Wikipedia (state + city + denomination categories).
        if full_state:
            try:
                results.extend(self._search_wikipedia_venues(full_state, target_city,
                                                             country_intent))
            except Exception:
                pass

        # 3. OpenStreetMap — bars/cafes/theaters/outdoor AND churches (when asked).
        if full_state or coords:
            try:
                results.extend(self._search_osm(
                    coords[0] if coords else None, coords[1] if coords else None,
                    full_state, target_city, church_focus=church_intent))
            except Exception:
                pass

        # 4. Google Places (optional; needs GOOGLE_PLACES_API_KEY).
        try:
            results.extend(self._search_google_places(
                coords[0] if coords else None, coords[1] if coords else None,
                target_city, full_state, church_intent))
        except Exception:
            pass

        # 5. Dedup — later (fresher) sources override curated on name collision.
        seen: Set[str] = set()
        final: List[Dict[str, Any]] = []
        for v in results:
            name = (v.get("name") or "").strip()
            if not name:
                continue
            key = re.sub(r"[^a-z0-9]", "", name.lower())
            if key in seen:
                final = [x for x in final
                         if re.sub(r"[^a-z0-9]", "", (x.get("name") or "").lower()) != key]
            else:
                seen.add(key)
            v.setdefault("state", full_state)
            if not v.get("contact"):
                v["contact"] = self._contact_from_name(name)
            final.append(v)

        # 6. Classify (venue_type, size_class, address, reason).
        for v in final:
            self._classify(v)

        # 7. Location targeting: for city searches keep the metro area,
        #    radius-limited providers always pass.
        if target_city:
            for v in final:
                v["city_match"] = self._city_matches(v, target_city, full_state)
            final = [v for v in final if v.get("city_match")]

        # 8. Rank: church-first for worship queries; balanced interleave otherwise.
        ranked = self._rank_and_interleave(final, church_intent, country_intent, size_bias)

        # 9. Display filters (post-ranking only; 'all' = no filtering).
        if size_filter and size_filter != "all":
            ranked = [v for v in ranked if v.get("size_class") == size_filter]
        if type_filter and type_filter != "all":
            ranked = [v for v in ranked if v.get("venue_type") == type_filter]

        return ranked

    # ------------------------------------------------------------------ #
    # EPK / contract text
    # ------------------------------------------------------------------ #
    def generate_epk_text(self, artist_name: str, genre: str, venue_name: str) -> str:
        return (
        f"Dear {venue_name} Talent Buyer,\n\n"
        f"My name is Ray from SoundScape Pilot Artist Development. I am reaching out on behalf of {artist_name}, a {genre} act that has been gaining serious traction in the region.\n\n"
        f"We believe {artist_name} would be an excellent fit for {venue_name} based on your recent calendar and audience. I have attached a short EPK with streaming links, press quotes, and live footage.\n\n"
        f"Would you be open to discussing a date in the coming months? We are flexible on routing and can work with guarantees or door deals.\n\n"
        f"Best,\n"
        f"Ray\n"
        f"ray@{DEFAULT_DOMAIN}\n"
        f"SoundScape Pilot Artist Development\n"
    )

    def generate_contract_text(self, artist_name: str, venue_name: str, date: str,
                               guarantee: float, state: str) -> str:
        return (
            f"PERFORMANCE AGREEMENT\n\n"
            f"Artist: {artist_name}\n"
            f"Venue: {venue_name}\n"
            f"Date: {date}\n"
            f"Location: {state}\n\n"
            f"Compensation: ${guarantee:.2f} guarantee, payable via wire transfer 48 hours prior to performance.\n\n"
            f"This agreement is subject to a standard performance contract reviewed by a licensed entertainment attorney. Both parties agree to execute a final rider covering sound, lighting, hospitality, and cancellation terms within 7 days.\n\n"
            f"Governing Law: {state}\n\n"
            f"SoundScape Pilot Contract Engine\n"
            f"contract@{DEFAULT_DOMAIN}\n"
        )
