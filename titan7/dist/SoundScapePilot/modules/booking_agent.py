import re
import time
import httpx
import asyncio
import json
from typing import List, Dict, Any, Set, Optional

from modules.mailer import DEFAULT_DOMAIN


WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_BASE = "https://en.wikipedia.org"
OVER_PASS_APIS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

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


class BookingAgent:
    def __init__(self):
        self._last_req = 0.0
        self.client = httpx.Client(timeout=12.0, headers={
            "User-Agent": "SoundScapePilot-BookingBot/1.0 (Music Industry Research)",
            "Accept-Language": "en-US,en;q=0.9"
        }, follow_redirects=True)

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

    _osm_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _search_osm_churches(self, full_state: str) -> List[Dict[str, Any]]:
        """Query OpenStreetMap Overpass API for Christian churches in a state.
        Tries multiple endpoints, caches results per state."""
        cache_key = f"osm_churches_{full_state.lower()}"
        if cache_key in self._osm_cache:
            return list(self._osm_cache[cache_key])

        abbr = _STATE_ABBR.get(full_state.title(), "")
        if not abbr:
            return []
        # Overpass QL: find Christian places of worship in the state (node & way)
        overpass_query = f'[out:json][timeout:45];area["name"="{full_state}"]["boundary"="administrative"]["admin_level"=4]->.search;(node(area.search)["amenity"="place_of_worship"]["religion"="christian"];way(area.search)["amenity"="place_of_worship"]["religion"="christian"];);out center 300;'

        for api_url in OVER_PASS_APIS:
            try:
                r = self.client.post(api_url, data={"data": overpass_query}, timeout=55.0)
                if r.status_code != 200:
                    continue
                data = r.json()
                elements = data.get("elements", [])
                seen_names = set()
                results = []
                for el in elements:
                    name = (el.get("tags") or {}).get("name", "").strip()
                    if not name or name.lower() in seen_names:
                        continue
                    seen_names.add(name.lower())
                    tags = el.get("tags") or {}
                    city = (tags.get("addr:city", "") or tags.get("addr:suburb", "") or
                            tags.get("name:city", "")).strip()
                    if not city:
                        city_match = re.search(r'(?:,\s*|in\s+|\(|–\s*)([A-Z][a-zA-Z\s.]+?)(?:\s*(?:,|\)|$|TX|Texas))', name)
                        if city_match:
                            city = city_match.group(1).strip()
                    lat = el.get("lat", 0) or (el.get("center") or {}).get("lat", 0)
                    lon = el.get("lon", 0) or (el.get("center") or {}).get("lon", 0)
                    results.append({
                        "name": name,
                        "city": city,
                        "state": full_state,
                        "capacity": 0,
                        "contact": self._contact_from_name(name),
                        "website": tags.get("website", "") or tags.get("contact:website", ""),
                        "source": "OpenStreetMap",
                        "latitude": lat,
                        "longitude": lon,
                    })
                if results:
                    self._osm_cache[cache_key] = list(results)
                    return results
            except Exception:
                continue
        return []

    def search_venues(self, state: str, genre: str = "live music") -> List[Dict[str, Any]]:
        self._genre = (genre or "live music").lower()
        state_key = state.strip()
        full_state = None
        for full, abbr in US_STATES.items():
            if state_key.lower() == full or state_key.upper() == abbr or state_key.lower() == abbr.lower():
                full_state = full.title()
                break
        if not full_state:
            full_state = state_key.title()

        # 1. Always include curated data in the library.
        curated = list(CURATED_VENUES.get(full_state, []))
        results: List[Dict[str, Any]] = []
        for v in curated:
            v.setdefault("source", "SoundScape Pilot Curated")
            v.setdefault("state", full_state)
            results.append(dict(v))

        # 2. Always try online discovery too.
        network_results: List[Dict[str, Any]] = []
        try:
            network_results = self._search_wikipedia_venues(full_state)
        except Exception:
            pass
        results.extend(network_results)

        # 2b. For Christian/gospel, also search OpenStreetMap for churches (single query, thousands of results)
        is_christian = any(w in self._genre for w in ["christian", "church", "gospel", "religious", "worship", "faith", "spiritual"])
        if is_christian:
            try:
                osm_results = self._search_osm_churches(full_state)
                results.extend(osm_results)
            except Exception:
                pass

        # 3. Dedup — keep last occurrence so online overrides curated on name collision.
        seen: Set[str] = set()
        final: List[Dict[str, Any]] = []
        for v in results:
            name = v.get("name", "").strip()
            if not name:
                continue
            # If we've seen this name before, remove the old entry and append the new one
            # so online (which comes after curated) wins.
            if name.lower() in seen:
                final = [x for x in final if x.get("name", "").strip().lower() != name.lower()]
            else:
                seen.add(name.lower())
            v.setdefault("state", full_state)
            if not v.get("contact"):
                v["contact"] = self._contact_from_name(name)
            final.append(v)

        return final

    def _search_wikipedia_venues(self, state: str) -> List[Dict[str, Any]]:
        seen_titles: Set[str] = set()
        all_titles = []

        # --- Per-state base categories ---
        is_christian = any(w in self._genre for w in ["christian", "church", "gospel", "religious", "worship", "faith", "spiritual"])

        if is_christian:
            # For Christian/gospel, crawl church categories first via wide crawl, then fallback venues
            root_categories = [
                f"Category:Churches in {state}",
                f"Category:Religious buildings and structures in {state}",
                f"Category:Megachurches in {state}",
                f"Category:Baptist churches in {state}",
                f"Category:Methodist churches in {state}",
                f"Category:Roman Catholic church buildings in {state}",
                f"Category:Presbyterian churches in {state}",
                f"Category:Lutheran churches in {state}",
                f"Category:Episcopal church buildings in {state}",
                f"Category:Cathedrals in {state}",
                f"Category:Music venues in {state}",
                f"Category:Concert halls in {state}",
            ]
        else:
            root_categories = [
                f"Category:Music venues in {state}",
                f"Category:Concert halls in {state}",
                f"Category:Nightclubs in {state}",
                f"Category:Theatres in {state}",
                f"Category:Performing arts centres in {state}",
                f"Category:Event venues in {state}",
                f"Category:Music festivals in {state}",
                f"Category:Festivals in {state}",
            ]
        if state == "Texas" and not is_christian:
            root_categories.append("Category:Music venues in Texas by city")

        for genre_key, cats in GENRE_CATEGORIES.items():
            if genre_key in self._genre:
                for c in cats:
                    if c not in root_categories:
                        root_categories.append(c)

        # --- Crawl categories (reduced deadline for speed) ---
        deadline = time.time() + 20.0
        for cat in root_categories:
            if time.time() > deadline:
                break
            is_genre_specific = any(cat == c for cats in GENRE_CATEGORIES.values() for c in cats) and " in " not in cat
            is_church_cat = "Churches in " in cat or "Religious buildings" in cat
            if is_church_cat:
                # Efficient "wide" crawl: get subcats, then pages from each subcat
                self._collect_church_pages(cat, seen_titles, all_titles, deadline)
            elif is_genre_specific:
                md = 0
            else:
                md = 1
                self._collect_category_pages(cat, seen_titles, all_titles, depth=0, max_depth=md, deadline=deadline)

        # --- Genre-specific list pages ---
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
                        all_titles.append({"title": v["name"], "pageid": 0, "city_hint": v.get("city", "")})
            except Exception:
                pass

        titles = all_titles
        details = self._get_venue_details(titles, deadline)
        out = []
        for t in titles:
            title = t["title"]
            info = details.get(title, {})
            out.append({
                "name": title,
                "city": info.get("city") or t.get("city_hint", ""),
                "capacity": info.get("capacity"),
                "contact": self._contact_from_name(title),
                "website": info.get("url", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"),
                "source": "Wikipedia"
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
                # Try to extract city and state from cells
                city = ""
                if len(cells) > 1:
                    city_text = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if city_text and re.match(r'^[A-Z]', city_text) and len(city_text) < 60:
                        city = city_text
                if target_state:
                    state_found = False
                    for cell in cells:
                        cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                        # Match "TX", "Texas", state abbreviations
                        if cell_text == target_state or cell_text == _STATE_ABBR.get(target_state, ""):
                            state_found = True
                            break
                        if cell_text and len(cell_text) == 2 and cell_text.isupper():
                            rev_abbr = {v: k for k, v in _STATE_ABBR.items()}
                            if cell_text == rev_abbr.get(target_state, ""):
                                state_found = True
                                break
                        if cell_text == target_state:
                            # E.g. "Texas" in cell matches target_state "Texas"
                            state_found = True
                            break
                    if not state_found:
                        continue
                venues.append({"name": name, "city": city})
        return venues

    def _collect_category_pages(self, category: str, seen: Set[str], titles: list, depth: int = 0, max_depth: int = 2, deadline: float = 0.0):
        if depth > max_depth:
            return
        # At the leaf depth (== max_depth), only request pages — no further subcat recursion
        cmtype = "page" if depth == max_depth else "page|subcat"
        params = {
            "action": "query", "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": "max",
            "cmtype": cmtype,
        }
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
                    titles.append({"title": title, "pageid": m.get("pageid", 0)})
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                params["cmcontinue"] = cont["cmcontinue"]
            else:
                break
        for sc in subcats:
            if deadline and time.time() > deadline:
                return
            self._collect_category_pages(sc, seen, titles, depth + 1, max_depth, deadline)

    def _collect_church_pages(self, category: str, seen: Set[str], titles: list, deadline: float = 0.0):
        """Efficient church crawl: get all subcats, then pages from each.
        One level only — skips subcats that have no pages (e.g. by-county) to save time.
        Also gets pages directly from the root category."""
        # Direct pages from the root
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
                    titles.append({"title": title, "pageid": m.get("pageid", 0)})
            cont = data.get("continue", {})
            if "cmcontinue" in cont:
                params_root["cmcontinue"] = cont["cmcontinue"]
            else:
                break

        # Get all subcategories
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

        # Get pages from each subcat (one level only)
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
                        titles.append({"title": title, "pageid": m.get("pageid", 0)})
                cont = data.get("continue", {})
                if "cmcontinue" in cont:
                    params2["cmcontinue"] = cont["cmcontinue"]
                else:
                    break
            # If subcat had no pages, try its subcats one level deeper
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
                                titles.append({"title": title, "pageid": m.get("pageid", 0)})
                        cont = data.get("continue", {})
                        if "cmcontinue" in cont:
                            params4["cmcontinue"] = cont["cmcontinue"]
                        else:
                            break

    def _get_venue_details(self, titles: List[Dict], deadline: float = 0.0) -> Dict[str, Dict[str, Any]]:
        if not titles:
            return {}
        details = {}
        city_pattern = re.compile(r"in\s+([A-Z][a-zA-Z\s.]+?)(?:,\s*[A-Z]{2}|\.)")
        real_titles = [t["title"] for t in titles]
        for i in range(0, len(real_titles), 50):
            if deadline and time.time() > deadline:
                break
            batch = real_titles[i:i+50]
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
                    if extract:
                        m = city_pattern.search(extract)
                        if m:
                            city = m.group(1).strip()
                        if not city:
                            first = extract.split(".")[0]
                            if len(first) < 80:
                                city = first.strip()
                    details[title] = {
                        "url": page.get("fullurl", ""),
                        "city": city
                    }
        return details

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
