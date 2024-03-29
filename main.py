import dash
from dash import html
from dash import dcc
import numpy as np
import pandas as pd
import dash_cytoscape as cyto
from dash.dependencies import Input, Output

def create_nodes(df, src, region_view=True):
    nodes = []
    unique_nodes = []

    if region_view:
        relevant_routes = df[df.Source_airport_name.isin(src)]

        source_name = df[df['Source_airport_name'].isin(src)].iloc[0]['Source_airport_name']
        source_ID = df[df['Source_airport_name'].isin(src)].iloc[0]['Source_airport_ID']
        source_lat = df[df['Source_airport_name'].isin(src)].iloc[0]['Source_airport_latitude']
        source_long = df[df['Source_airport_name'].isin(src)].iloc[0]['Source_airport_longitude']

        nodes.append({'data':
                        {'id': str(source_name), 'label': source_name},
                        'position': {'x': source_long*10, 'y': -source_lat*10}
                    })

        for irow, row in relevant_routes.iterrows():
            if row['Destination_airport_name'] not in unique_nodes:
                nodes.append(
                    {'data': {'id' : str(row['Destination_airport_name']), 'label': row['Destination_airport_name'].replace(' ','\n')},
                    'position' : {'x': row['Destination_airport_longitude']*10, 'y': -row['Destination_airport_latitude']*10}
                    }
                )
                unique_nodes.append(row['Destination_airport_name'])
    else:
        relevant_routes = df[df.Equipment.isin(src)]
        relevant_routes = relevant_routes.head(15)

        for irow, row in relevant_routes.iterrows():
            if (row['Destination_airport_name'] not in unique_nodes):
                nodes.append(
                    {'data': {'id' : str(row['Destination_airport_name']), 'label': row['Destination_airport_name'].replace(' ','\n')},
                    'position' : {'x': row['Destination_airport_longitude']*10, 'y': -row['Destination_airport_latitude']*10}
                    }
                )
                unique_nodes.append(row['Destination_airport_name'])
            if (row['Source_airport_name'] not in unique_nodes):
                nodes.append(
                    {'data': {'id' : str(row['Source_airport_name']), 'label': row['Source_airport_name'].replace(' ','\n')},
                    'position' : {'x': row['Source_airport_longitude']*10, 'y': -row['Source_airport_latitude']*10}
                    }
                )
                unique_nodes.append(row['Source_airport_name'])
    return nodes

def create_edges(df, source, region_view=True):
    edge_list = []
    if region_view:
        relevant_routes = df[df.Source_airport_name.isin(source)]
    else:
        relevant_routes = df[df.Equipment.isin(source)].head(15)
    edge_df = relevant_routes.groupby(by=['Source_airport_name', 'Destination_airport_name']).size().reset_index(name='counts')
    edge_df = edge_df.sort_values("counts", ascending=False).head(10)
    edge_df['normalized_counts'] = edge_df['counts']/edge_df['counts'].abs().max()
    #print(edge_df)
    edge_list = [{'data': {'source': str(s), 'target': str(d), 'weight': c}
                    } for s, d, c in zip(edge_df.Source_airport_name.tolist(), edge_df.Destination_airport_name.tolist(),
                                        edge_df.normalized_counts.tolist())]
    return edge_list


airports = pd.read_csv('/Users/aniket/Documents/pycon/plotly-dash/data/airports.csv')
routes = pd.read_csv('/Users/aniket/Documents/pycon/plotly-dash/data/routes.csv')

airports.drop(columns=['IATA', 'ICAO', 'Altitude', 'Timezone', 'DST', 'Tz database time zone', 'Type', 'Source'], axis=1, inplace=True)
routes.drop(columns=['Airline_ID', 'Codeshare', 'Stops'], axis=1, inplace=True)

routes = routes[pd.to_numeric(routes['Source_airport_ID'], errors='coerce').notnull()]
routes = routes[pd.to_numeric(routes['Destination_airport_ID'], errors='coerce').notnull()]
routes['Source_airport_ID'] = routes['Source_airport_ID'].astype(np.int64)
routes['Destination_airport_ID'] = routes['Destination_airport_ID'].astype(np.int64)

routes = routes.merge(airports, left_on='Source_airport_ID', right_on='Airport ID')
routes['Name'] = [i.split(' Airport')[0] for i in routes['Name'].tolist()]
routes['Source_airport_name'] = routes['Name'] +' ('+ routes['City']+')'
routes['Source_airport_country'] = routes['Country']
routes['Source_airport_latitude'] = routes['Latitude']
routes['Source_airport_longitude'] = routes['Longitude']
routes.drop(['Source_airport', 'Airport ID', 'Name', 'Country', 'Latitude', 'Longitude', 'City'], axis=1, inplace=True)

routes = routes.merge(airports, left_on='Destination_airport_ID', right_on='Airport ID')
routes['Name'] = [i.split(' Airport')[0] for i in routes['Name'].tolist()]
routes['Destination_airport_name'] = routes['Name'] +' ('+ routes['City']+')'
routes['Destination_airport_country'] = routes['Country']
routes['Destination_airport_latitude'] = routes['Latitude']
routes['Destination_airport_longitude'] = routes['Longitude']
routes.drop(['Destination_airport', 'Airport ID', 'Name', 'Country', 'Latitude', 'Longitude', 'City'], axis=1, inplace=True)

elements_list = []

style_list = [
    {'selector':'node',
    'style':{
        'content':'data(label)',
        'background-color':'#dcdcdc',
        'border-color':'black',
        'border-width':'0.1px',
        'font-size':'1px',
        'font-family':'system-ui',
        'opacity':0.9,
        'width':'3px',
        'height':'3px',
        'min-zoomed-font-size':'1px',
        'text-wrap' : 'wrap',
        'overlay-padding':'0.1',
        }
    },
    {'selector':'edge',
    'style':{
        'width':'data(weight)',
        'target-arrow-color':'navy',
        'target-arrow-shape':'triangle',
        'target-endpoint':'outside-to-node-or-label',
        'arrow-scale':0.4,
        'curve-style':'bezier',
        'opacity':0.9,
        'line-color':'navy',
        'line-cap':'butt',
        'label':'data(label)',
        'text-rotation':'autorotate',
        'font-size':'1px'
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
app.config.suppress_callback_exceptions = True

unique_countires = routes['Source_airport_country'].tolist() + (routes['Destination_airport_country']).unique().tolist()
unique_countires.sort()
unique_equipments = [str(i) for i in routes['Equipment'].unique().tolist()]
unique_equipments.sort()

app.layout = html.Div([
    dcc.RadioItems(
        id='selection',
        options=[{'label':'Filter based on region', 'value':'region'},{'label':'Filter based on equipment', 'value':'equipment'}],
        value='region',
        style={'width': '40%','margin-left':'10px'}),
    html.Div(
        id='dropdown',
        style={'width': '95%', 'display':'flex','margin-left':'10px', 'padding':'15px'},
        ),
    html.Div(['Edges in ',
        html.Span('red ',style={'color': 'red'}),
        ' represent 90 percentile traffic between source and destination. Edges in ',
        html.Span('yellow', style={'color': 'yellow'}),
        ' represent 75 percentile traffic between source and destination'], style={'margin-left':'10px'}),
    html.Hr(),
    html.Div(id='region_plot',hidden=False),
    html.Div(id='equipment_plot',children=[],hidden=True)
    ])

@app.callback(Output('dropdown', 'children'),
              [Input('selection', 'value')])
def choosePlotOption(selected_value):
    if selected_value == 'region':
        children = ['Source Country:',
                    dcc.Dropdown(
                        id='country-dropdown',
                        value='India',
                        multi=False,
                        clearable=False,
                        options=[{'label': name, 'value' : name} for name in unique_countires],
                        style={'width': '40%'}),
                    'Source Airport:',
                    dcc.Dropdown(id='airport-dropdown', style={'width': '40%'})
                    ]
    else:
        children = ['Equipment:',
                    dcc.Dropdown(
                        id='equipment_dropdown',
                        value=['777','ATR'],
                        multi=True,
                        clearable=False,
                        options=[{'label': name, 'value' : name} for name in unique_equipments],
                        style={'width': '40%'}
                    )]
    return children

@app.callback(Output('airport-dropdown', 'options'),
              [Input('country-dropdown', 'value')])
def airports_options(value):
    routes_in_country = routes[routes['Source_airport_country'].isin([value])]
    unique_airports = routes_in_country['Source_airport_name'].unique().tolist()
    unique_airports.sort()
    return [{'label': name, 'value' : name} for name in unique_airports]

@app.callback(Output('region_plot', 'children'),
              [Input('airport-dropdown', 'value')])
def displaySelectedNodeData(value):
    src = [value]
    elements_list = []
    if value is not None:
        nodes = create_nodes(routes,src,region_view=True)
        edges = create_edges(routes,src)
        nodes_ = [[i['data']['source'] for i in edges][0]]+[i['data']['target'] for i in edges]
        #print(edges)
        nodes_ = [i for i in nodes if i['data']['id'] in nodes_]
        for i in nodes_:
            i['data']['label']=i['data']['label'].split("(")[1].split(")")[0]
        elements_list.extend(nodes_)
        elements_list.extend(edges)

    return cyto.Cytoscape(
        id='cytoscape-plot',
        layout={'name':'concentric'},
        elements=elements_list,
        stylesheet=style_list,
        style={
            'width' : '100%',
            'height' : str(90)+'vh',
        }
        )

@app.callback([Output('equipment_plot', 'children'),
               Output('region_plot', 'hidden'),
               Output('equipment_plot', 'hidden')],
              [Input('equipment_dropdown', 'value')])
def displaySelectedNodeData(value):
    elements_list = []
    if value is not None:
        nodes = create_nodes(routes,value,region_view=False)
        edges = create_edges(routes, value, region_view=False)
        nodes_ = [[i['data']['source'] for i in edges][0]]+[i['data']['target'] for i in edges]
        #print(edges)
        nodes_ = [i for i in nodes if i['data']['id'] in nodes_]
        for i in nodes_:
            i['data']['label']=i['data']['label'].split("(")[1].split(")")[0]
        elements_list.extend(nodes)
        elements_list.extend(edges)
   
    return cyto.Cytoscape(
        id='cytoscape-plot',
        layout={'name':'concentric'},
        elements=elements_list,
        stylesheet=style_list,
        style={
            'width' : '100%',
            'height' : str(90)+'vh',
        }
        ), True, False

if __name__ == '__main__':
    app.run_server(debug=True)
