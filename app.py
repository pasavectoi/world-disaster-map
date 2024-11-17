import json
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import os
# Initialize the Dash application
app = Dash(__name__)
server = app.server  # Important: This is for Render deployment
# Add port configuration
port = int(os.environ.get("PORT", 10000))
def load_data():
    """
    Load and process the disaster data from JSON file
    Returns:
        pandas.DataFrame: Processed dataframe with disaster information
    """
    try:
        # Get the current directory and construct the file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'disaster_map.json')
        
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        df = pd.DataFrame(data)
        
        # Convert numerical columns and handle missing values
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        df['Total Deaths'] = pd.to_numeric(df['Total Deaths'], errors='coerce').fillna(0)
        df['Total Damage'] = pd.to_numeric(df["Total Damage, Adjusted ('000 US$)"], errors='coerce').fillna(0)
        df['Start Year'] = pd.to_numeric(df['Start Year'], errors='coerce').fillna(0).astype(int)
        
        # Remove rows with missing crucial information
        df = df.dropna(subset=['Latitude', 'Longitude', 'Disaster Type', 'Location'])
        
        # Fill missing values in text columns
        text_columns = ['Disaster Type', 'Location']
        for col in text_columns:
            df[col] = df[col].fillna('Unknown')
        
        # Filter for specific disaster types
        return df[df['Disaster Type'].isin(['Earthquake', 'Flood', 'Storm', 'Drought'])]
    
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

# Load the processed data
df = load_data()

# Define the application layout
app.layout = html.Div([
    # Title
    html.H1("Natural Disaster Visualization (1900-2023)",
            style={
                'textAlign': 'center',
                'color': '#2c3e50',
                'fontSize': '2.5em',
                'marginBottom': '30px',
                'fontFamily': 'Arial, sans-serif'
            }),
    
    # Control panel
    html.Div([
        # Year selection
        html.Label('Select Year:',
                  style={
                      'fontSize': '1.2em',
                      'marginBottom': '10px',
                      'display': 'block'
                  }),
        dcc.Slider(
            id='year-slider',
            min=df['Start Year'].min(),
            max=df['Start Year'].max(),
            step=1,
            value=df['Start Year'].max(),
            marks={year: str(year) for year in range(df['Start Year'].min(), df['Start Year'].max() + 1, 10)},
            tooltip={'placement': 'bottom', 'always_visible': True}
        ),
        html.Br(),
        
        # Disaster type selection
        html.Label('Select Disaster Type:',
                  style={
                      'fontSize': '1.2em',
                      'marginBottom': '10px',
                      'display': 'block'
                  }),
        dcc.Dropdown(
            id='disaster-dropdown',
            options=[{'label': t, 'value': t} for t in sorted(df['Disaster Type'].unique())],
            value='Earthquake',
            style={'marginBottom': '20px'}
        )
    ], style={
        'width': '80%',
        'margin': '0 auto',
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    # Statistics panel
    html.Div([
        html.Div(id='stats-panel', className='stats-container')
    ], style={
        'width': '80%',
        'margin': '20px auto',
        'padding': '15px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    # Map container
    html.Div([
        dcc.Graph(
            id='map-plot',
            style={'height': '70vh'},
            config={
                'scrollZoom': True,  # Enable mouse wheel zoom
                'displayModeBar': True,  # Show the mode bar
                'modeBarButtonsToAdd': ['drawrect', 'eraseshape'],  # Add extra control buttons
                'modeBarButtonsToRemove': ['lasso2d']  # Remove unnecessary buttons
            }
        )
    ], style={
        'width': '90%',
        'margin': '20px auto',
        'padding': '15px',
        'backgroundColor': '#ffffff',
        'borderRadius': '10px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    # Store map state
    dcc.Store(id='map-state', data={
        'zoom': 2,
        'center': {'lat': 20, 'lon': 0},
        'autosize': True
    })
])

# Define callback for updating map and statistics
@app.callback(
    [Output('map-plot', 'figure'),
     Output('stats-panel', 'children'),
     Output('map-state', 'data')],
    [Input('year-slider', 'value'),
     Input('disaster-dropdown', 'value'),
     Input('map-plot', 'relayoutData')],
    [State('map-state', 'data')]
)
def update_map_and_stats(selected_year, selected_type, relayout_data, map_state):
    """
    Update the map and statistics panel based on user input
    
    Args:
        selected_year: The year selected by the user
        selected_type: The disaster type selected by the user
        relayout_data: Map layout data from user interaction
        map_state: Current state of the map
    
    Returns:
        tuple: (figure, stats_panel, map_state)
    """
    # Update map state from user interaction
    if relayout_data:
        if 'mapbox.zoom' in relayout_data:
            map_state['zoom'] = relayout_data['mapbox.zoom']
        if 'mapbox.center' in relayout_data:
            map_state['center'] = {
                'lat': relayout_data['mapbox.center']['lat'],
                'lon': relayout_data['mapbox.center']['lon']
            }
    
    # Filter data based on user selection
    filtered_df = df[
        (df['Start Year'] == selected_year) &
        (df['Disaster Type'] == selected_type)
    ]
    
    # Create the map visualization
    if len(filtered_df) == 0:
        # Create empty map if no data
        fig = px.scatter_mapbox(
            pd.DataFrame({'lat': [0], 'lon': [0]}),
            lat='lat',
            lon='lon',
            zoom=map_state['zoom'],
            mapbox_style="open-street-map"
        )
    else:
        # Create density map for low zoom levels
        if map_state['zoom'] < 5:
            fig = px.density_mapbox(
                filtered_df,
                lat='Latitude',
                lon='Longitude',
                radius=10,
                hover_name="Location",
                hover_data={
                    "Total Deaths": ":,",
                    "Total Damage": ":,.2f"
                },
                mapbox_style="open-street-map"
            )
            fig.update_coloraxes(showscale=False)
        else:
            # Create scatter map for high zoom levels
            fig = px.scatter_mapbox(
                filtered_df,
                lat='Latitude',
                lon='Longitude',
                hover_name="Location",
                hover_data={
                    "Total Deaths": ":,",
                    "Total Damage": ":,.2f"
                },
                size="Total Deaths",
                size_max=30,
                opacity=0.7,
                mapbox_style="open-street-map"
            )
    
    # Update map layout
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        mapbox=dict(
            center=map_state['center'],
            zoom=map_state['zoom']
        ),
        uirevision='constant'  # Maintain user's view state
    )
    
    # Calculate statistics
    total_events = len(filtered_df)
    total_deaths = filtered_df['Total Deaths'].sum()
    total_damage = filtered_df['Total Damage'].sum()
    
  # Create statistics panel
    stats_panel = html.Div([
        html.Div([
            html.H3(f"Year: {selected_year}", style={'color': '#2c3e50'}),
            html.H4(f"Disaster Type: {selected_type}", style={'color': '#2c3e50'}),
            html.P([
                html.Strong("Total Events: "), f"{total_events:,}",
                html.Br(),
                html.Strong("Total Deaths: "), f"{total_deaths:,.0f}",
                html.Br(),
                html.Strong("Total Damage ('000 US$): "), f"{total_damage:,.2f}"
            ], style={'fontSize': '1.1em'})
        ], style={'textAlign': 'center'})
    ])
    
    return fig, stats_panel, map_state

# Run the server
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=port)
