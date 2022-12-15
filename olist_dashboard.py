#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px

import pandas as pd
import numpy as np

import unicodedata
from urllib.request import urlopen
import json
with urlopen('https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json') as response:
    counties = json.load(response)

def transliterateDfColumn(df, column_name):
    names_utf8 = []
    
    for name in df[column_name]:
        name_utf8 = unicodedata.normalize("NFD", name)
        name_utf8 = name_utf8.encode("ascii", "ignore")
        name_utf8 = name_utf8.decode("utf-8")

        names_utf8.append(name_utf8)

    df[column_name] = names_utf8
    df[column_name] = df[column_name].str.lower()
    

orders = pd.read_csv ('olist_orders_dataset.csv')
order_items = pd.read_csv ('olist_order_items_dataset.csv')
products = pd.read_csv('olist_products_dataset.csv')

# append column with order total value (item price + freight)
order_items = order_items.assign(total_value=order_items["price"]+order_items["freight_value"])

# append column with purchase year for filtering
orders = orders.assign(purchase_year=pd.DatetimeIndex(orders['order_purchase_timestamp']).year)

### append product category name into order_items
# using set_index() + join() for performance purposes
productsTemp = products[['product_id', 'product_category_name']]

productsTemp.set_index('product_id', inplace=True)
order_items.set_index('product_id', inplace=True)

order_items = order_items.join(productsTemp, how='left').reset_index()
#------------------------------

### creating orders_detail table
# selecting only necessary orders and order_items tables columns
order_itemsTemp = order_items[['order_id',
                               'product_category_name',
                               'total_value']]

ordersTemp = orders[['order_id',
                     'customer_id',
                     'purchase_year',
                     'order_approved_at', 
                     'order_status']]

order_itemsTemp.set_index('order_id', inplace=True)
ordersTemp.set_index('order_id', inplace=True)

orders_detail = order_itemsTemp.join(ordersTemp, how='left').reset_index()
#------------------------------

### list of all product categories
product_categories = orders_detail.product_category_name.unique()
product_categories = product_categories.astype(str)
product_categories = sorted(product_categories)
product_categories.remove('nan')
#------------------------------

counties_ids = pd.read_csv('id_counties_BR.csv')
geolocation = pd.read_csv('olist_geolocation_dataset.csv')

transliterateDfColumn(counties_ids, 'geolocation_city')    
transliterateDfColumn(geolocation, 'geolocation_city')

geolocation = pd.merge(geolocation, counties_ids, on='geolocation_city', how='left')

geolocation = geolocation.fillna(0)
geolocation['city_id'] = geolocation['city_id'].astype(int)
geolocation['city_id'] = geolocation['city_id'].astype(str)

geolocation = geolocation.groupby('geolocation_city').agg({'geolocation_state':'min', 'city_id':'min'}).reset_index()


customers = pd.read_csv('olist_customers_dataset.csv')

geolocation = geolocation.rename(columns={'geolocation_city': 'city_name', 'geolocation_state':'state'})
customers = customers.rename(columns={'customer_city': 'city_name'})

customers = customers[['customer_id','city_name']]

dfTemp = pd.merge(customers, geolocation, on='city_name', how='left')

ordersTemp = orders_detail[['order_id','customer_id', 'purchase_year', 'product_category_name']]

# using join() setting customer_id as index instead of pd.merge() because of improved performance
dfTemp.set_index('customer_id', inplace=True)
ordersTemp.set_index('customer_id', inplace=True)
customers_loc = ordersTemp.join(dfTemp, how='left')

customers_loc = customers_loc.groupby(['city_id',
                                       'city_name',
                                       'purchase_year',
                                       'product_category_name']).agg({'order_id': 'nunique'}).reset_index()


# cards' formatting parameters
card_value_style = {'font-weight':'bold',
                    'font-size': '200%', 
                    'color': '#4d4d4d', 
                    'text-align': 'center',
                    'margin-bottom': '0px'}

card_title_style = {'font-size': '70%', 
                    'color': 'grey',
                    'text-align': 'center',
                    'font-weight':'bold'}


# Build App
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
html.Div([
    dcc.Markdown('''
    # E-COMMERCE DASHBOARD
    ###### This dashboard is based on real e-commerce data made public by Olist [here](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
    ''')
    ], style={'margin-left': '1vw', 'display': 'flex', 'flex': 1}),
      
html.Div([
    html.Div([
        dcc.Dropdown(options=[{'label': '2016', 'value':2016},
                              {'label': '2017', 'value':2017},
                              {'label': '2018', 'value':2018}],
                     value=2017,
                     id='year',
                     clearable=False,
                     style={'font-weight':'bold'}),

        html.Br(),
        
        dcc.Dropdown(product_categories,
                     value='cama_mesa_banho',
                     id='product category',
                     clearable=False,
                     style={'font-weight':'bold'}),

        html.Br(),
        
        dash_table.DataTable(id='top cities table',
                             style_cell_conditional=[{'if': {'column_id': 'CITY'},
                                                      'textAlign': 'left', 'width': '75%'}], 
                             style_header={'color': 'grey', 'font-weight':'bold'}, 
                             style_cell={'color': '#4d4d4d',
                                         'font-weight':'bold', 
                                         'overflow': 'hidden',
                                         'textOverflow': 'ellipsis',
                                         'maxWidth': 0}, 
                             style_as_list_view=True)
        ], style={'width': '20%', 'padding': '1vw'}),
    
    html.Div([
        html.Div([
            dbc.Card([html.P(id='revenue', className="card-value", style=card_value_style),
                       html.P("REVENUE - BRL", className="card-title", style=card_title_style)], style={'width':'23%'}),

            dbc.Card([html.P(id='total orders', className="card-value", style=card_value_style),
                      html.P("TOTAL ORDERS", className="card-title", style=card_title_style)], style={'width':'23%'}),

            dbc.Card([html.P(id='avg ticket per order', className="card-value", style=card_value_style), 
                      html.P("AVG TICKET PER ORDER - BRL", className="card-title", style=card_title_style)], style={'width':'23%'}),

            dbc.Card([html.P(id='transaction approval', className="card-value", style=card_value_style), 
                      html.P("TRANSACTION APPROVAL RATE", className="card-title", style=card_title_style)], style={'width':'23%'})
            ], style={'display': 'flex', 'flex-direction': 'row', 'flex':'1', 'justify-content': 'space-between'}),

        html.Div([
            dcc.Graph(id='customers orders map', style={'height':'63vh'})
            ], style={'margin-top':'1vw'})
        
        ], style={'width': '80%', 'padding': '1vw', 'height':'84vh'})  
    ], style={'display': 'flex', 'flex-direction': 'row', 'flex':'1'})
], style={'display': 'flex', 'flex-direction': 'column', 'flex':'1'})


@app.callback(
    Output('revenue', 'children'),
    Output('total orders','children'),
    Output('avg ticket per order','children'),
    Output('transaction approval','children'),
    Output('top cities table', 'data'),
    Output('customers orders map','figure'),
    Input('year', 'value'),
    Input('product category', 'value'))
def update_data(selected_year, prod_category):
    # filtering year and product category
    orders_detail_filtered = orders_detail[(orders_detail['purchase_year'] == selected_year)&
                                           (orders_detail['product_category_name'] == prod_category)]
    
    revenue = orders_detail_filtered['total_value'].sum()
    # formatting with thousands separator and to BRL thousands
    revenue_formatted = format(int(revenue/1000), ',') + 'k'
    
    total_orders = orders_detail_filtered.order_id.nunique()
    # formatting with thousands separator
    total_orders_formatted = format(total_orders, ',')
    
    try:
        avg_ticket_per_order = revenue / total_orders
        # formatting to 2 decimals float
        avg_ticket_per_order_formatted = format(avg_ticket_per_order, ',.2f')
    except ZeroDivisionError:
        avg_ticket_per_order_formatted = '-'
    
    try:
        transaction_approval_rate = orders_detail_filtered[orders_detail_filtered['order_approved_at'].notna()].order_id.nunique() / total_orders
        transaction_approval_rate = format(transaction_approval_rate, '.2%')
    except ZeroDivisionError:
        transaction_approval_rate = '-'
    
    customers_loc_filtered = customers_loc[(customers_loc['purchase_year'] == selected_year)&
                                           (customers_loc['product_category_name'] == prod_category)]
    
    top_cities = customers_loc_filtered[['city_name','order_id']].nlargest(10,'order_id')
    top_cities = top_cities.rename(columns={'city_name':'CITY', 'order_id': 'ORDERS'})
    top_cities = top_cities.to_dict('records')
    
    customers_orders_map = px.choropleth_mapbox(customers_loc_filtered,
                                                geojson=counties,
                                                locations='city_id',
                                                color='order_id',
                                                featureidkey="properties.id",
                                                color_continuous_scale='pubu',
                                                mapbox_style="carto-positron",
                                                zoom=5,
                                                center = {'lat':-22.4317, 'lon':-45.4597},
                                                opacity=0.5,
                                                hover_name='city_name',
                                                hover_data={'city_id':False},
                                                labels={'order_id':'ORDERS'})

    customers_orders_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return revenue_formatted, total_orders_formatted, avg_ticket_per_order_formatted, transaction_approval_rate, top_cities, customers_orders_map


# Run app and display result
if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=False)

