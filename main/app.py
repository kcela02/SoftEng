import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
from sklearn.linear_model import LinearRegression
import base64, io

# ========== Sample dataset loader (realistic 500 sales/day) ==========
def load_sample_data():
    dates = pd.date_range("2023-08-01", periods=(pd.Timestamp.today() - pd.Timestamp("2023-08-01")).days + 1)
    products = [f"Product {i}" for i in range(1, 11)]
    np.random.seed(42)
    data = []

    for d in dates:
        total_sales = np.random.normal(loc=500, scale=30)  # mean 500 per day
        total_sales = max(400, min(600, int(total_sales)))  # clamp between 400–600

        weights = np.random.dirichlet(np.ones(len(products)), size=1)[0]
        product_sales = (weights * total_sales).astype(int)

        for product, s in zip(products, product_sales):
            data.append({"date": d, "product": product, "actual": s})

    return pd.DataFrame(data)

# ========== Forecast generator with Linear Regression ==========
def generate_forecast(df, days_ahead=7):
    df = df.copy()
    df = df.dropna(subset=["actual"])
    if len(df) < 2:
        df["forecast"] = df["actual"]
        return df

    # Linear regression
    X = np.arange(len(df)).reshape(-1, 1)
    y = df["actual"].values
    model = LinearRegression()
    model.fit(X, y)

    # Predict historical + future
    forecast_hist = model.predict(X)
    forecast_hist = np.clip(forecast_hist, 0, None).astype(int)

    future_X = np.arange(len(df), len(df) + days_ahead).reshape(-1, 1)
    forecast_future = model.predict(future_X)
    forecast_future = np.clip(forecast_future, 0, None).astype(int)

    # Build forecast dataframe
    df["forecast"] = forecast_hist
    last_date = df["date"].max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_ahead)
    future_df = pd.DataFrame({
        "date": future_dates,
        "product": df["product"].iloc[0],
        "actual": [None]*days_ahead,
        "forecast": forecast_future
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
df["month"] = df["date"].dt.to_period("M").astype(str)
df["week"] = ((df["date"].dt.day - 1) // 7 + 1).astype(str)

months = sorted(df["month"].unique())
weeks = ["1", "2", "3", "4"]

# ========== Layout ==========
app.layout = dbc.Container([

    html.H1("Predictive Sales & Restocking Dashboard"),

    # Controls (Product / Month / Week + Upload & Download)
    dbc.Row([

        # Filters
        dbc.Col([
            html.Label("Select Product:"),
            dcc.Dropdown(
                id='product-filter',
                options=[{'label': 'All Products', 'value': 'ALL'}] +
                        [{'label': p, 'value': p} for p in sorted(df['product'].unique())],
                value='ALL'
            )
        ], md=3),

        dbc.Col([
            html.Label("Select Month:"),
            dcc.Dropdown(
                id='month-filter',
                options=[{'label': m, 'value': m} for m in months],
                value=months[-1]  # latest month
            )
        ], md=3),

        dbc.Col([
            html.Label("Select Week:"),
            dcc.Dropdown(
                id='week-filter',
                options=[{'label': 'All Weeks', 'value': 'ALL'}] +
                        [{'label': f"Week {w}", 'value': w} for w in weeks],
                value='ALL'
            )
        ], md=3),

        # Upload & Download
        dbc.Col([
            html.Label("Data Options:"),
            dbc.Row([
                dbc.Col([
                    dcc.Upload(
                        id="upload-data",
                        children=html.Div(["📂 Upload File"]),
                        style={
                            "width": "100%", "height": "40px", "lineHeight": "40px",
                            "borderWidth": "1px", "borderStyle": "dashed",
                            "borderRadius": "5px", "textAlign": "center"
                        },
                        multiple=False
                    )
                ], width=6),

                dbc.Col([
                    html.Button("⬇️ Download", id="btn-download", className="btn btn-primary", style={"width": "100%"}),
                    dcc.Download(id="download-data")
                ], width=6),
            ])
        ], md=3)

    ], className="mb-4"),

    # Graph
    dcc.Graph(id='sales-forecast-graph'),

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

# Upload callback
@app.callback(
    Output("sales-forecast-graph", "figure"),
    Output("summary-title", "children"),
    Output("summary-actual", "children"),
    Output("summary-forecast", "children"),
    Output("summary-accuracy", "children"),
    Input("product-filter", "value"),
    Input("month-filter", "value"),
    Input("week-filter", "value"),
    Input("upload-data", "contents"),
    State("upload-data", "filename")
)
def update_graph(selected_product, selected_month, selected_week, uploaded_file, filename):
    global df

    # Handle upload
    if uploaded_file is not None:
        content_type, content_string = uploaded_file.split(',')
        decoded = base64.b64decode(content_string)
        try:
            if filename.endswith('.csv'):
                df_new = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            elif filename.endswith(('.xls', '.xlsx')):
                df_new = pd.read_excel(io.BytesIO(decoded))
            else:
                return dash.no_update
            df_new["date"] = pd.to_datetime(df_new["date"])
            df = pd.concat([df, df_new], ignore_index=True)
            df["month"] = df["date"].dt.to_period("M").astype(str)
            df["week"] = ((df["date"].dt.day - 1) // 7 + 1).astype(str)
        except Exception as e:
            print("Error reading file:", e)
            return dash.no_update

    # Filter
    df_filtered = df[df["month"] == selected_month]
    if selected_week != "ALL":
        df_filtered = df_filtered[df_filtered["week"] == selected_week]
    if selected_product != "ALL":
        df_filtered = df_filtered[df_filtered["product"] == selected_product]
    else:
        df_filtered = df_filtered.groupby("date")["actual"].sum().reset_index()
        df_filtered["product"] = "All Products"

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
    summary_title = f"Summary ({selected_month}, {'Week ' + selected_week if selected_week != 'ALL' else 'All Weeks'})"

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
    Output("download-data", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True
)
def download_filtered_data(n_clicks):
    return dcc.send_data_frame(df.to_csv, "sales_forecast_data.csv", index=False)

# ========== Run ==========
if __name__ == '__main__':
    app.run(debug=True)
