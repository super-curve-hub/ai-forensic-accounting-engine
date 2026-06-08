import plotly.express as px

def plot_roic(df):
    return px.line(df, x="date", y="ROIC")
