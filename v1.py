import requests
import json
import random
import geocoder
import streamlit as st
import folium
from streamlit_folium import folium_static
import emoji

# Yelp API Key
yelp_api_key = "8V0wD0XaZNVI7vNZ4wBoDyWs_CR7jUemUzrGjlYfB6vnquwXf2fvTKH9-lW-s9F6viimgNrbF8hR-VQlt-f3ZL1cIRvkXfDKftN04GxUOv40TDqjFjiouQOnkjo8ZHYx"

# Function to fetch restaurants from Yelp API
def get_restaurants(zipcode, dietary_restrictions=None, budget=None, miles=None, cuisine=None, min_rating=None):
    g = geocoder.arcgis(zipcode)
    location = f"{g.lat},{g.lng}"

    radius = int(miles * 1609.34) if miles else None

    yelp_endpoint = "https://api.yelp.com/v3/businesses/search"
    headers = {"Authorization": f"Bearer {yelp_api_key}"}
    params = {
        "location": location,
        "categories": "food,restaurants",
        "limit": 50,
        "radius": radius,
    }

    if dietary_restrictions:
        params["attributes"] = ",".join(dietary_restrictions)
    if budget:
        params["price"] = budget
    if cuisine:
        params["term"] = cuisine

    response = requests.get(yelp_endpoint, headers=headers, params=params)

    if response.status_code != 200:
        return None, None

    data = response.json()
    businesses = data.get("businesses", [])
    restaurants = []

    for business in businesses:
        name = business["name"]
        rating = business["rating"]
        if min_rating and rating < min_rating:
            continue
        distance = business["distance"]
        address = ", ".join(business["location"].get("display_address", []))
        phone = business.get("display_phone", "N/A")
        categories = ", ".join([cat["title"] for cat in business.get("categories", [])])
        coordinates = [business["coordinates"]["latitude"], business["coordinates"]["longitude"]]
        image_url = business.get("image_url", "")

        restaurants.append((name, rating, address, phone, categories, coordinates, image_url))

    return restaurants, random.sample(restaurants, min(len(restaurants), 3))

# Helper function to display restaurant details
def display_restaurant(restaurant, index):
    st.image(restaurant[6], width=300, caption=restaurant[0])
    st.markdown(f"**{restaurant[0]}**")
    st.write(f"Rating: {restaurant[1]} stars")
    st.write(f"Address: {restaurant[2]}")
    st.write(f"Phone: {restaurant[3]}")
    st.write(f"Categories: {restaurant[4]}")
    if st.button(f"Select {restaurant[0]}", key=f"select_button_{index}"):
        st.session_state.selected_restaurant = restaurant

# Streamlit UI
st.sidebar.header("Search Settings")

# Input fields
zip_code = st.sidebar.text_input("Enter your zip code:")
distance = st.sidebar.slider("Distance (miles):", 1, 15, 5)
dietary_restrictions = st.sidebar.text_input("Dietary restrictions (comma-separated):")
dietary_restrictions = [x.strip() for x in dietary_restrictions.split(",") if dietary_restrictions]

budget = st.sidebar.selectbox("Budget:", ["Cheap", "Moderate", "Expensive", "Luxury"], index=1)
budget_map = {"Cheap": 1, "Moderate": 2, "Expensive": 3, "Luxury": 4}
selected_budget = budget_map[budget]

cuisine = st.sidebar.text_input("Preferred cuisine:")

min_rating = st.sidebar.slider("Minimum Rating:", 1.0, 5.0, 4.0, step=0.5)

# Initialize session state for selected restaurant
if "selected_restaurant" not in st.session_state:
    st.session_state.selected_restaurant = None

# Main content
st.title(emoji.emojize("Welcome to Foodie :fork_and_knife_with_plate:"))
st.write("Discover the best restaurants near you based on your preferences. Use Version 1 on a laptop or pc for best experience. Does work on phones too. ")
st.write("Made by Hritish.")

if st.sidebar.button("Find Restaurants"):
    if zip_code:
        with st.spinner("Fetching restaurants..."):
            restaurants, top_picks = get_restaurants(zip_code, dietary_restrictions, selected_budget, distance, cuisine, min_rating)

            if not restaurants:
                st.error("No restaurants found. Please try adjusting your filters.")
            else:
                # Display results
                st.header("Top Picks")
                for index, restaurant in enumerate(top_picks):
                    display_restaurant(restaurant, index)

                # Display map
                st.header("Map View")
                g = geocoder.arcgis(zip_code)
                m = folium.Map(location=[g.lat, g.lng], zoom_start=13)
                folium.Marker(location=[g.lat, g.lng], popup="You are here", icon=folium.Icon(color="blue")).add_to(m)
                for restaurant in top_picks:
                    folium.Marker(location=restaurant[5], popup=restaurant[0], icon=folium.Icon(color="green")).add_to(m)
                folium_static(m)
    else:
        st.error("Please enter a valid zip code.")

# Display selected restaurant
if st.session_state.selected_restaurant:
    st.header("Your Selected Restaurant")
    restaurant = st.session_state.selected_restaurant
    st.markdown(f"**{restaurant[0]}**")
    st.write(f"Address: {restaurant[2]}")
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={restaurant[2].replace(' ', '+')}"
    st.markdown(f"[Get Directions]({google_maps_url})")
