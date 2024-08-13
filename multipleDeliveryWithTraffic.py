import os
from dotenv import load_dotenv
import googlemaps
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv('GOOGLE_MAPS_API_KEY')

gmaps = googlemaps.Client(key=api_key)

addresses = [
    "1600 Amphitheatre Parkway, Mountain View, CA",
    "1 Infinite Loop, Cupertino, CA",
    "1 Hacker Way, Menlo Park, CA",
    "345 Spear St, San Francisco, CA"
]

locations = []
for address in addresses:
    geocode_result = gmaps.geocode(address)
    lat_lng = geocode_result[0]['geometry']['location']
    locations.append((lat_lng['lat'], lat_lng['lng']))

distance_matrix_result = gmaps.distance_matrix(locations, locations, mode="driving", departure_time="now")

travel_times_matrix = []
for row in distance_matrix_result['rows']:
    travel_times = []
    for element in row['elements']:
        travel_times.append(element['duration_in_traffic']['value'])  
    travel_times_matrix.append(travel_times)

def create_data_model():
    return {
        'distance_matrix': travel_times_matrix,
        'num_vehicles': 1,
        'depot': 0  
    }

def solve_tsp(data):
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    # transit callback
    def distance_callback(from_index, to_index):
        return data['distance_matrix'][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Set first solution heuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(search_parameters)

    return solution, routing, manager

data = create_data_model()
solution, routing, manager = solve_tsp(data)

def get_route_order(solution, routing, manager):
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))
    return route

route_order = get_route_order(solution, routing, manager)

ordered_locations = [locations[i] for i in route_order]

df = pd.DataFrame(ordered_locations, columns=['Latitude', 'Longitude'])
df['Order'] = range(1, len(ordered_locations) + 1)

# Create a scatter mapbox trace for the pins with visible text
pins = go.Scattermapbox(
    lat=df['Latitude'],
    lon=df['Longitude'],
    mode='markers+text',
    marker=go.scattermapbox.Marker(size=10, color='red'),
    text=df['Order'].astype(str),  # Ensure the order is treated as text
    textfont=dict(size=14, color="red"),  # Customize text appearance
    textposition="top right",
    showlegend=False
)

# Create the line mapbox trace for the route
route = go.Scattermapbox(
    lat=df['Latitude'],
    lon=df['Longitude'],
    mode='lines',
    line=go.scattermapbox.Line(width=4, color='blue'),
    showlegend=False
)

fig = go.Figure()
fig.add_trace(route)
fig.add_trace(pins)

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_zoom=10,
    mapbox_center={"lat": df['Latitude'].mean(), "lon": df['Longitude'].mean()},
    margin={"r":0,"t":30,"l":0,"b":0},
    title="Optimal Delivery Route with Pins"
)

fig.show()
