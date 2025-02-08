import requests
import streamlit as st
import folium
import random
from streamlit_folium import folium_static

# API Keys
google_api_key = 
yelp_api_key = 


# Function to fetch latitude and longitude from an address using Google Geocoding API
def get_lat_lng_from_address(address):
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": google_api_key}
    response = requests.get(geocode_url, params=params)

    if response.status_code != 200:
        return None, None

    data = response.json()
    if data["status"] == "OK" and len(data["results"]) > 0:
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    else:
        return None, None


# Function to fetch restaurants from Google Places API
def get_restaurants_google(location, radius, cuisine=None):
    google_places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "radius": radius,
        "type": "restaurant",
        "key": google_api_key,
    }

    if cuisine:
        params["keyword"] = cuisine

    response = requests.get(google_places_url, params=params)

    if response.status_code != 200:
        return None

    data = response.json()
    results = data.get("results", [])
    restaurants = []

    for place in results:
        name = place.get("name")
        address = place.get("vicinity", "N/A")
        lat = place["geometry"]["location"]["lat"]
        lng = place["geometry"]["location"]["lng"]
        place_id = place.get("place_id")

        restaurants.append({
            "name": name,
            "address": address,
            "coordinates": [lat, lng],
            "place_id": place_id,
        })

    return restaurants


# Function to enrich restaurant data with Yelp API
def enrich_with_yelp_data(restaurants, dietary_restrictions=None, budget=None, min_rating=None):
    yelp_endpoint = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization": f"Bearer {yelp_api_key}"}
    enriched_restaurants = []

    for restaurant in restaurants:
        name = restaurant["name"]
        params = {
            "term": name,
            "latitude": restaurant["coordinates"][0],
            "longitude": restaurant["coordinates"][1],
            "limit": 1,
        }
        if budget:
            params["price"] = budget
        if dietary_restrictions:
            params["attributes"] = ",".join(dietary_restrictions)

        response = requests.get(yelp_endpoint, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data["businesses"]:
                business = data["businesses"][0]
                rating = business["rating"]
                if min_rating and rating < min_rating:
                    continue
                image_url = business.get("image_url", "")
                phone = business.get("display_phone", "N/A")
                categories = ", ".join([cat["title"] for cat in business.get("categories", [])])
                price = business.get("price", "N/A")  # Get price level ($, $$, $$$, $$$$)

                restaurant.update({
                    "rating": rating,
                    "image_url": image_url,
                    "phone": phone,
                    "categories": categories,
                    "price": price,  # Include price information
                })
                enriched_restaurants.append(restaurant)

    return enriched_restaurants


# Helper function to display restaurant details
def display_restaurant(restaurant, index):
    st.image(restaurant.get("image_url", ""), width=300, caption=restaurant["name"])
    st.markdown(f"**{restaurant['name']}**")
    st.write(f"Rating: {restaurant.get('rating', 'N/A')} stars")
    st.write(f"Address: {restaurant['address']}")
    st.write(f"Phone: {restaurant.get('phone', 'N/A')}")
    st.write(f"Categories: {restaurant.get('categories', 'N/A')}")
    st.write(f"Budget: {restaurant.get('price', 'N/A')}")  # Add budget line

    # Generate Google Maps link
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={restaurant['coordinates'][0]},{restaurant['coordinates'][1]}"

    # Use a markdown hyperlink styled as a button
    st.markdown(
        f"""
        <a href="{google_maps_url}" target="_blank">
            <button style="background-color:#4CAF50; color:white; border:none; padding:10px 20px; text-align:center; font-size:14px; border-radius:5px; cursor:pointer;">
                Open in Google Maps
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )


# Top 15 Cuisines (from Yelp)
top_cuisines = [
    "American", "Mexican", "Italian", "Chinese", "Japanese",
    "Indian", "Thai", "Mediterranean", "French", "Korean",
    "Vietnamese", "Spanish", "Middle Eastern", "Greek", "Caribbean"
]

# Sidebar UI
st.sidebar.header("Search Settings")

# Address Input
address = st.sidebar.text_input("Enter your address:")
distance_feet = st.sidebar.slider("Distance (feet):", 500, 2500, 1000)

# Preferred Cuisine Dropdown
cuisine = st.sidebar.selectbox(
    "Preferred Cuisine:",
    options=["Anything"] + top_cuisines + ["Other"],
    index=0
)

# Handle 'Anything' cuisine selection (randomize for each restaurant)
cuisines_to_fetch = []
if cuisine == "Anything":
    cuisines_to_fetch = [random.choice(top_cuisines) for _ in range(3)]
elif cuisine == "Other":
    custom_cuisine = st.sidebar.text_input("Specify your preferred cuisine:")
    cuisines_to_fetch = [custom_cuisine] * 3 if custom_cuisine else []
else:
    cuisines_to_fetch = [cuisine] * 3

# Dietary restrictions
dietary_options = ["Vegetarian", "Gluten-Free", "Vegan", "Peanut Allergy", "Kosher", "Halal", "Other"]
selected_dietary = st.sidebar.multiselect("Dietary Restrictions:", dietary_options)

# Handle 'Other' dietary restriction
if "Other" in selected_dietary:
    other_restriction = st.sidebar.text_input("Specify other restriction:")
    if other_restriction:
        selected_dietary.append(other_restriction)
    selected_dietary.remove("Other")

# Budget dropdown (using dollar signs)
budget_map = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}
budget_options = ["Anything"] + list(budget_map.keys())
selected_budget_label = st.sidebar.selectbox("Budget:", budget_options)

# Handle 'Anything' budget selection (randomly choose)
if selected_budget_label == "Anything":
    selected_budget_label = random.choice(list(budget_map.keys()))

selected_budget = budget_map.get(selected_budget_label, None)

min_rating = st.sidebar.slider("Minimum Rating:", 1.0, 5.0, 4.0, step=0.5)

# Find Restaurants button
if st.sidebar.button("Find Restaurants"):
    if address:
        st.sidebar.write("Fetching location...")
        lat, lng = get_lat_lng_from_address(address)
        if lat and lng:
            location = f"{lat},{lng}"
            radius_meters = distance_feet * 0.3048

            all_restaurants = []
            for selected_cuisine in cuisines_to_fetch:
                google_restaurants = get_restaurants_google(location, radius_meters, selected_cuisine)
                if google_restaurants:
                    random_restaurant = random.choice(google_restaurants)
                    all_restaurants.append(random_restaurant)

            if not all_restaurants:
                st.error("No restaurants found matching your criteria.")
            else:
                enriched_restaurants = enrich_with_yelp_data(
                    all_restaurants, selected_dietary, selected_budget, min_rating
                )

                if not enriched_restaurants:
                    st.error("No restaurants found matching your criteria.")
                else:
                    st.header("Top Picks")
                    for index, restaurant in enumerate(enriched_restaurants):
                        display_restaurant(restaurant, index)

                    # Display map
                    st.header("Map View")
                    m = folium.Map(location=[lat, lng], zoom_start=15)
                    folium.Marker(location=[lat, lng], popup="You are here", icon=folium.Icon(color="blue")).add_to(m)
                    for restaurant in enriched_restaurants:
                        folium.Marker(location=restaurant["coordinates"], popup=restaurant["name"],
                                      icon=folium.Icon(color="green")).add_to(m)
                    folium_static(m)
        else:
            st.error("Unable to fetch location. Please check the address.")
    else:
        st.error("Please enter a valid address.")
