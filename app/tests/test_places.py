import places


def test_town_read_in_the_state_it_names_else_their_search_states():
    jc, ny = places.town("Jersey City"), places.town("New York")
    assert jc[2] == "Jersey City" and ny[2] == "New York City"
    # Newark CA is the bigger one by name alone; a New York City area search reads it in New Jersey
    assert places.located("Newark, CA")[2] == "Newark" and places.located("Newark, CA")[1] < -100
    assert places.located("Newark, United States", prefer={"NJ", "NY"})[1] > -75
    assert places.located("Remote, NJ") is None and places.located("United States") is None


def test_distance_to_the_nearest_office_it_names():
    home = places.located("Montclair, New Jersey")
    near = lambda loc, cities=(): places.distance({"location": loc, "cities": list(cities)}, home, {"NJ", "NY", "CT"})
    miles, at = near("Jersey City, NJ, US")
    assert at == "Jersey City" and 5 < miles < 12
    assert near("Stamford, United States")[0] > 25
    # several offices: the nearest one it names, never the job search's first city tag
    assert near("Tampa, Florida, USA; Jersey City, New Jersey, USA")[1] == "Jersey City"
    assert near("Plano, TX or Charlotte, NC or Jersey City - hybrid")[1] == "Jersey City"
    assert near("Madhive HQ (New York, NY)")[1] == "New York City"
    assert near("Grand Central, Manhattan")[1] == "Manhattan"
    # no town in the location: its city tags
    assert near("New Jersey, United States", ["Secaucus"])[1] == "Secaucus"
    assert near("United States") is None and places.distance({"location": "Jersey City"}, None) is None


def test_home_from_their_saved_address_else_their_resume():
    assert places.home({"home_address": {"city": "Hoboken", "state": "New Jersey"}}, {"location": "NYC"})[2] == "Hoboken"
    assert places.home({"home_address": {"city": None}}, {"location": "NYC"})[2] == "New York City"
    assert places.home({}, None) is None
