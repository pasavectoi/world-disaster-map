import json
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import webbrowser
from threading import Timer


def open_browser():
    webbrowser.open_new('http://localhost:8051')


# Step 1: Load JSON data
with open(r"disaster_map.json", 'r', encoding='utf-8') as file:
    data = json.load(file)

df = pd.DataFrame(data)

# 数据清洗部分保持不变
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
df['Total Deaths'] = pd.to_numeric(df['Total Deaths'], errors='coerce').fillna(0)
df['Total Damage'] = pd.to_numeric(df["Total Damage, Adjusted ('000 US$)"], errors='coerce').fillna(0)
df['Start Year'] = pd.to_numeric(df['Start Year'], errors='coerce').fillna(0).astype(int)
df = df.dropna(subset=['Latitude', 'Longitude', 'Disaster Type', 'Location'])

text_columns = ['Disaster Type', 'Location']
for col in text_columns:
    df[col] = df[col].fillna('Unknown')

# Filter for specific disaster types
df = df[df['Disaster Type'].isin(['Earthquake', 'Flood', 'Storm', 'Drought'])]

# Step 2: Initialize Dash application
app = Dash(__name__)

# Step 3: Define layout
app.layout = html.Div([
    html.H1("Natural Disaster Visualization (1900-2023)",
            style={
                'textAlign': 'center',
                'color': '#2c3e50',
                'fontSize': '2.5em',
                'marginBottom': '30px',
                'fontFamily': 'Arial, sans-serif'
            }),
    html.Div([
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

    html.Div([
        dcc.Graph(
            id='map-plot',
            style={'height': '70vh'},
            config={
                'scrollZoom': True,  # 启用滚轮缩放
                'displayModeBar': True,  # 显示模式栏
                'modeBarButtonsToAdd': ['drawrect', 'eraseshape'],  # 添加额外的控制按钮
                'modeBarButtonsToRemove': ['lasso2d']  # 移除不需要的按钮
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

    # 存储地图状态
    dcc.Store(id='map-state', data={
        'zoom': 2,
        'center': {'lat': 20, 'lon': 0},
        'autosize': True
    })
])


# Step 4: Update map and statistics
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
    # 更新地图状态
    if relayout_data:
        if 'mapbox.zoom' in relayout_data:
            map_state['zoom'] = relayout_data['mapbox.zoom']
        if 'mapbox.center' in relayout_data:
            map_state['center'] = {
                'lat': relayout_data['mapbox.center']['lat'],
                'lon': relayout_data['mapbox.center']['lon']
            }

    # Filter data
    filtered_df = df[
        (df['Start Year'] == selected_year) &
        (df['Disaster Type'] == selected_type)
        ]

    if len(filtered_df) == 0:
        fig = px.scatter_mapbox(
            pd.DataFrame({'lat': [0], 'lon': [0]}),
            lat='lat',
            lon='lon',
            zoom=map_state['zoom'],
            mapbox_style="open-street-map"
        )
    else:
        # 根据缩放级别选择显示方式
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
            fig = px.scatter_mapbox(
                filtered_df,
                lat='Latitude',
                lon='Longitude',
                hover_name="Location",
                hover_data={
                    "Total Deaths": ":,",
                    "Total Damage": ":,.2f"
                },
                size="Total Deaths",  # 添加大小变化
                size_max=30,  # 最大点大小
                opacity=0.7,  # 透明度
                mapbox_style="open-street-map"
            )

    # 保持用户的视角
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        mapbox=dict(
            center=map_state['center'],
            zoom=map_state['zoom']
        ),
        uirevision='constant'  # 保持用户交互状态
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


# Step 5: Run the server
if __name__ == '__main__':
    print("Starting server on http://localhost:8051")
    Timer(1.5, open_browser).start()
    app.run_server(
        host='localhost',
        port=8051,
        debug=True,
        use_reloader=False
    )
