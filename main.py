import dash
from dash import html
from dash import dcc
import numpy as np
import pandas as pd
import dash_cytoscape as cyto
from dash.dependencies import Input, Output

def create_nodes(df, src):
    nodes = []
    unique_nodes = []

    airports_list = routes[df.Source_airport_name.isin(src)]

    source_name = routes[routes['Source_airport_name'].isin(src)].iloc[0]['Source_airport_name']
    source_ID = routes[routes['Source_airport_name'].isin(src)].iloc[0]['Source_airport_ID']
    source_lat = routes[routes['Source_airport_name'].isin(src)].iloc[0]['Source_airport_latitude']
    source_long = routes[routes['Source_airport_name'].isin(src)].iloc[0]['Source_airport_longitude']

    nodes.append({'data':
                    {'id': str(source_name), 'label': source_name},
                    'position': {'x': source_long*10, 'y': -source_lat*10}
                })
    i_airport = 0

    for irow, row in airports_list.iterrows():
        if row['Destination_airport_name'] not in unique_nodes:
            nodes.append(
                {'data': {'id' : str(row['Destination_airport_name']), 'label': row['Destination_airport_name'].replace(' ','\n')},
                'position' : {'x': row['Destination_airport_longitude']*10, 'y': -row['Destination_airport_latitude']*10}
                }
            )
            unique_nodes.append(row['Destination_airport_name'])
            i_airport=i_airport + 1
    return nodes

def create_edges(df, source):
    edge_list = []
    relevant_routes = routes[df.Source_airport_name.isin(source)]
    edge_df = relevant_routes.groupby(by=['Source_airport_name', 'Destination_airport_name']).size().reset_index(name='counts')
    edge_df['normalized_counts'] = edge_df['counts']/edge_df['counts'].abs().max()
    edge_list = [{'data': {'source': str(s), 'target': str(d), 'weight': c}
                  } for s, d, c in zip(edge_df.Source_airport_name.tolist(), edge_df.Destination_airport_name.tolist(),
                                       edge_df.normalized_counts.tolist())]
    return edge_list


airports = pd.read_csv('airports.csv')
routes = pd.read_csv('routes.csv')

airports.drop(columns=['City', 'IATA', 'ICAO', 'Altitude', 'Timezone', 'DST', 'Tz database time zone', 'Type', 'Source'], axis=1, inplace=True)
routes.drop(columns=['Airline_ID', 'Codeshare', 'Stops'], axis=1, inplace=True)

routes = routes[pd.to_numeric(routes['Source_airport_ID'], errors='coerce').notnull()]
routes = routes[pd.to_numeric(routes['Destination_airport_ID'], errors='coerce').notnull()]
routes['Source_airport_ID'] = routes['Source_airport_ID'].astype(np.int64)
routes['Destination_airport_ID'] = routes['Destination_airport_ID'].astype(np.int64)

routes = routes.merge(airports, left_on='Source_airport_ID', right_on='Airport ID')
routes['Source_airport_name'] = routes['Name']
routes['Source_airport_country'] = routes['Country']
routes['Source_airport_latitude'] = routes['Latitude']
routes['Source_airport_longitude'] = routes['Longitude']
routes.drop(['Source_airport', 'Airport ID', 'Name', 'Country', 'Latitude', 'Longitude'], axis=1, inplace=True)

routes = routes.merge(airports, left_on='Destination_airport_ID', right_on='Airport ID')
routes['Destination_airport_name'] = routes['Name']
routes['Destination_airport_country'] = routes['Country']
routes['Destination_airport_latitude'] = routes['Latitude']
routes['Destination_airport_longitude'] = routes['Longitude']
routes.drop(['Destination_airport', 'Airport ID', 'Name', 'Country', 'Latitude', 'Longitude'], axis=1, inplace=True)

routes['Source_airport_name'] = [i.split(' Airport')[0] for i in routes['Source_airport_name'].tolist()]
routes['Destination_airport_name'] = [i.split(' Airport')[0] for i in routes['Destination_airport_name'].tolist()]

elements_list = []

style_list = [
    {'selector':'node',
    'style':{
        'content':'data(label)',
        'background-color':'#dcdcdc',
        'border-color':'black',
        'border-width':'0.1px',
        'font-size':'1.5px',
        'font-family':'system-ui',
        'opacity':0.9,
        'width':'2px',
        'height':'2px',
        'min-zoomed-font-size':'10px',
        'text-wrap' : 'wrap',
        'overlay-padding':'0.1',
        }
    },
    {'selector':'edge',
    'style':{
        'width':'data(weight)',
        'target-arrow-color':'navy',
        'target-arrow-shape':'none',
        'curve-style':'bezier',
        'opacity':0.3,
        'line-color':'navy',
        'line-cap':'round',
        'label':'data(label)',
        'text-rotation':'autorotate',
        'font-size':'3px'
        }
    },
    {'selector':'[weight>=0.75]',
    'style':{
        'line-color':'yellow',
        'target-arrow-color':'yellow',
        'opacity':0.5
        }
    },
    {'selector':'[weight>=0.9]',
    'style':{
        'line-color':'red',
        'target-arrow-color':'red',
        'opacity':0.6,
        'z-index':5000
        }
    }]
app = dash.Dash(__name__)

unique_countires = routes['Source_airport_country'].append(routes['Destination_airport_country']).unique().tolist()
unique_countires.sort()

app.layout = html.Div([
    html.Div(
        style={'width': '80%', 'display':'flex'},
        children = ['Country:',
                    dcc.Dropdown(
                        id='country-dropdown',
                        value='India',
                        multi=False,
                        clearable=False,
                        options=[{'label': name, 'value' : name} for name in unique_countires],
                        style={'width': '90%'}),
                    'Airports:',
                    dcc.Dropdown(id='airport-dropdown', style={'width': '90%'})
                    ]),
    html.Div(['Edges in ',
        html.Span('red ',style={'color': 'red'}),
        ' represent 90 percentile traffic between source and destination. Edges in ',
        html.Span('yellow', style={'color': 'yellow'}),
        ' represent 75 percentile traffic between source and destination']),
    cyto.Cytoscape(
        id='cytoscape-plot',
        layout={'name':'preset'},
        elements=elements_list,
        stylesheet=style_list,
        style={
            'width' : '100%',
            'height' : str(90)+'vh',
        }
        )])

@app.callback(Output('cytoscape-plot', 'elements'),
              [Input('airport-dropdown', 'value')])
def displaySelectedNodeData(value):
    src = [value]
    elements_list = []
    if value is not None:
        nodes = create_nodes(routes,src)
        edges = create_edges(routes, src)
        elements_list.extend(nodes)
        elements_list.extend(edges)
    return elements_list

@app.callback(Output('airport-dropdown', 'options'),
              [Input('country-dropdown', 'value')])
def airports_options(value):
    routes1 = routes[routes['Source_airport_country'].isin([value])]
    unique_airports = routes1['Source_airport_name'].unique().tolist()
    unique_airports.sort()
    return [{'label': name, 'value' : name} for name in unique_airports]

if __name__ == '__main__':
    app.run_server(debug=True)
