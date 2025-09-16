import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc

# ========== Sample dataset loader ==========
def load_sample_data():
    dates = pd.date_range("2023-08-01", periods=28)  # 4 weeks of data
    products = [f"Product {i}" for i in range(1, 11)]
    np.random.seed(42)
    data = []
    for product in products:
        sales = np.random.randint(50, 200, size=len(dates))
        for d, s in zip(dates, sales):
            data.append({"date": d, "product": product, "actual": s})
    return pd.DataFrame(data)

# ========== Forecast generator ==========
def generate_forecast(df, days_ahead=7):
    df = df.copy()
    df["forecast"] = df["actual"].rolling(window=3, min_periods=1).mean()
    last_date = df["date"].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_ahead)
    future_forecast = [df["forecast"].iloc[-1]] * days_ahead
    future_df = pd.DataFrame({
        "date": future_dates,
        "product": df["product"].iloc[0],
        "actual": [None]*days_ahead,
        "forecast": future_forecast
    })
    return pd.concat([df, future_df], ignore_index=True)

# ========== Accuracy calculator ==========
def calculate_accuracy(df):
    df_valid = df.dropna(subset=["actual", "forecast"])
    if len(df_valid) == 0 or df_valid["actual"].sum() == 0:
        return None
    errors = abs(df_valid["actual"] - df_valid["forecast"]) / df_valid["actual"]
    accuracy = 100 * (1 - errors.mean())
    return round(accuracy, 1)

# ========== Initialize app ==========
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
df = load_sample_data()
df["week"] = df["date"].dt.strftime("%Y-W%U")
weeks = sorted(df["week"].unique())

# ========== Layout ==========
app.layout = dbc.Container([
    html.H1("Predictive Sales & Restocking Dashboard"),

    # Upload
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select a CSV File')]),
        style={
            'width': '50%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '1px', 'borderStyle': 'dashed',
            'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'
        },
        multiple=False
    ),

    # Controls
    dbc.Row([
        dbc.Col([
            html.Label("Select Product:"),
            dcc.Dropdown(
                id='product-filter',
                options=[{'label': p, 'value': p} for p in sorted(df['product'].unique())] +
                        [{'label': 'All Products', 'value': 'ALL'}],
                value='Product 1'
            )
        ], md=4),

        dbc.Col([
            html.Label("Aggregation (All Products):"),
            dcc.RadioItems(
                id='agg-toggle',
                options=[{'label': 'Sum', 'value': 'sum'},
                         {'label': 'Average', 'value': 'avg'}],
                value='sum',
                inline=True
            )
        ], md=4),

        dbc.Col([
            html.Label("Select Week:"),
            dcc.Dropdown(
                id='week-filter',
                options=[{'label': 'All Weeks (Daily View)', 'value': 'ALL'}] +
                        [{'label': w, 'value': w} for w in weeks],
                value='ALL'
            )
        ], md=4),
    ], className="mb-4"),

    # Graph
    dcc.Graph(id='sales-forecast-graph'),

    # Download button
    html.Div([
        html.Button("Download Data", id="btn-download", className="btn btn-primary"),
        dcc.Download(id="download-dataframe-csv")
    ], style={"marginTop": "10px"}),

    # Summary + Accuracy Cards
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H5(id="summary-title", className="card-title"),
                    html.P(id="summary-actual", style={
                        "color": "blue", "fontSize": "20px", "fontWeight": "bold"}),
                    html.P(id="summary-forecast", style={
                        "color": "orange", "fontSize": "20px", "fontWeight": "bold"})
                ])
            ], style={"boxShadow": "2px 2px 10px lightgrey", "borderRadius": "15px"})
        , width=6),

        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H5("Forecast Accuracy", className="card-title"),
                    html.P(id="summary-accuracy", style={
                        "fontSize": "22px", "fontWeight": "bold"})
                ])
            ], style={"boxShadow": "2px 2px 10px lightgrey", "borderRadius": "15px"})
        , width=6),
    ], className="mt-4")
], fluid=True)

# ========== Callbacks ==========
@app.callback(
    Output('sales-forecast-graph', 'figure'),
    Output('summary-title', 'children'),
    Output('summary-actual', 'children'),
    Output('summary-forecast', 'children'),
    Output('summary-accuracy', 'children'),
    Input('product-filter', 'value'),
    Input('agg-toggle', 'value'),
    Input('week-filter', 'value')
)
def update_graph(selected_product, agg_type, selected_week):
    df_filtered = df.copy()

    # Product filter
    if selected_product == 'ALL':
        if agg_type == 'sum':
            df_grouped = df_filtered.groupby('date')['actual'].sum().reset_index()
        else:
            df_grouped = df_filtered.groupby('date')['actual'].mean().reset_index()
        df_grouped['product'] = 'All Products'
        df_filtered = df_grouped
    else:
        df_filtered = df_filtered[df_filtered['product'] == selected_product]

    # Week filter
    if selected_week != "ALL":
        df_filtered = df_filtered[df_filtered['date'].dt.strftime("%Y-W%U") == selected_week]

    # Forecast
    df_forecast = generate_forecast(df_filtered)

    # Plot
    trace_actual = go.Scatter(x=df_forecast['date'], y=df_forecast['actual'],
                              mode='lines+markers', name='Actual Sales',
                              line=dict(color='blue'))
    trace_forecast = go.Scatter(x=df_forecast['date'], y=df_forecast['forecast'],
                                mode='lines+markers', name='Forecasted Sales',
                                line=dict(color='orange', dash='dash'))
    fig_sales = go.Figure(data=[trace_actual, trace_forecast])
    fig_sales.update_layout(title=f"Sales vs Forecast ({selected_product})",
                            xaxis_title="Date", yaxis_title="Units Sold")

    # Summary
    total_actual = df_forecast['actual'].sum(skipna=True)
    total_forecast = df_forecast['forecast'].sum(skipna=True)
    summary_title = f"Summary ({'All Weeks' if selected_week == 'ALL' else selected_week})"

    # Accuracy
    accuracy = calculate_accuracy(df_forecast)
    if accuracy is None:
        accuracy_display = html.Span("Not Available", style={"color": "gray"})
    else:
        color = "green" if accuracy >= 80 else "red"
        accuracy_display = html.Span(f"{accuracy}%", style={"color": color})

    return (
        fig_sales,
        summary_title,
        f"Total Actual Sales: {int(total_actual)}",
        f"Total Forecasted Sales: {int(total_forecast)}",
        accuracy_display
    )

# Download callback
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    State("product-filter", "value"),
    State("agg-toggle", "value"),
    State("week-filter", "value"),
    prevent_initial_call=True
)
def download_data(n_clicks, selected_product, agg_type, selected_week):
    df_filtered = df.copy()

    # Product filter
    if selected_product == 'ALL':
        if agg_type == 'sum':
            df_grouped = df_filtered.groupby('date')['actual'].sum().reset_index()
        else:
            df_grouped = df_filtered.groupby('date')['actual'].mean().reset_index()
        df_grouped['product'] = 'All Products'
        df_filtered = df_grouped
    else:
        df_filtered = df_filtered[df_filtered['product'] == selected_product]

    # Week filter
    if selected_week != "ALL":
        df_filtered = df_filtered[df_filtered['date'].dt.strftime("%Y-W%U") == selected_week]

    # Forecast
    df_forecast = generate_forecast(df_filtered)

    # Summary
    total_actual = df_forecast['actual'].sum(skipna=True)
    total_forecast = df_forecast['forecast'].sum(skipna=True)
    accuracy = calculate_accuracy(df_forecast)

    # Add summary rows at the bottom
    summary_rows = pd.DataFrame({
        "date": ["", "", ""],
        "product": ["Summary", "Summary", "Summary"],
        "actual": [f"Total Actual: {int(total_actual)}", "", ""],
        "forecast": [f"Total Forecast: {int(total_forecast)}",
                     f"Accuracy: {accuracy if accuracy else 'N/A'}%", ""]
    })

    export_df = pd.concat([df_forecast, summary_rows], ignore_index=True)

    # Dynamic filename
    product_label = selected_product.replace(" ", "_")
    week_label = "AllWeeks" if selected_week == "ALL" else selected_week.replace("-", "_")
    filename = f"forecast_{product_label}_{week_label}.csv"

    return dcc.send_data_frame(export_df.to_csv, filename, index=False)

# ========== Run ==========
if __name__ == '__main__':
    app.run(debug=True)
