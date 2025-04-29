import streamlit as st
import os
import plotly.express as px
import pandas as pd
import folium
from streamlit_folium import folium_static

# Set page configuration and title
st.set_page_config(page_title="🚗 Road Accident Dashboard", layout="wide")
st.title("🚗 Road Accident Dashboard")

# File path
file_path = "C:/Users/madha/Downloads/Road Accident Data.xlsx"

@st.cache_data  # Cache the data loading to improve performance
def load_data(path):
    if os.path.exists(path):
        try:
            df = pd.read_excel(path, sheet_name="Data")
            df['Accident Date'] = pd.to_datetime(df['Accident Date'], errors='coerce')
            return df.dropna(subset=['Accident Date'])
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return None
    else:
        st.warning(f"File not found at: {path}. Please check the file path.")
        return None

# Load data
df = load_data(file_path)

if df is not None:
    # Columns detection
    columns_info = {
        'location': next((col for col in df.columns if 'location' in col.lower() or 'place' in col.lower()), None),
        'severity': next((col for col in df.columns if 'severity' in col.lower()), None),
        'casualties': next((col for col in df.columns if col in ['Number_of_Casualties', 'Casualties', 'Total_Casualties']), None),
        'speed': next((col for col in df.columns if 'speed' in col.lower() and 'limit' in col.lower()), None),
        'day': next((col for col in df.columns if col in ['Day_of_Week', 'DayOfWeek', 'Day']), None),
        'weather': next((col for col in df.columns if 'weather' in col.lower()), None),
        'road': next((col for col in df.columns if 'road' in col.lower() and 'condition' in col.lower()), None),
        'lat': next((col for col in df.columns if col in ['Latitude', 'Lat', 'lat']), None),
        'long': next((col for col in df.columns if col in ['Longitude', 'Long', 'lon', 'lng']), None)
    }

    # Sidebar Filters
    st.sidebar.header("Filter Data")
    min_date = df['Accident Date'].min().date()
    max_date = df['Accident Date'].max().date()
    date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    location_filter = []
    if columns_info['location']:
        location_filter = st.sidebar.multiselect(f"Select {columns_info['location']}s", df[columns_info['location']].dropna().unique())

    severity_filter = []
    if columns_info['severity']:
        severity_filter = st.sidebar.multiselect(f"Select {columns_info['severity']}", df[columns_info['severity']].dropna().unique())

    # Safe mask application
    if date_range and len(date_range) == 2:
        mask = ((df['Accident Date'] >= pd.Timestamp(date_range[0])) & (df['Accident Date'] <= pd.Timestamp(date_range[1])))
    else:
        mask = pd.Series([True] * len(df))  # No filter if date_range invalid

    if location_filter and columns_info['location']:
        mask &= df[columns_info['location']].isin(location_filter)

    if severity_filter and columns_info['severity']:
        mask &= df[columns_info['severity']].isin(severity_filter)

    df_filtered = df[mask]

    # Display Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Accidents", len(df_filtered))

    if columns_info['casualties']:
        col2.metric("Average Casualties", round(df_filtered[columns_info['casualties']].mean(), 2))
    else:
        col2.metric("Average Casualties", "N/A")

    if columns_info['speed']:
        col3.metric("Max Speed Limit", df_filtered[columns_info['speed']].max())
    else:
        col3.metric("Max Speed Limit", "N/A")

    # Tabs for Visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Trends", "Distributions", "Correlations", "Map"])

    with tab1:
        trend = df_filtered.groupby(df_filtered['Accident Date'].dt.date).size().reset_index(name='Accidents')
        fig_trend = px.line(trend, x='Accident Date', y='Accidents', title='Accidents Over Time', markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

        if columns_info['day']:
            days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            day_counts = df_filtered[columns_info['day']].value_counts().reset_index()
            day_counts.columns = [columns_info['day'], 'Count']
            day_counts[columns_info['day']] = pd.Categorical(day_counts[columns_info['day']], categories=days_order, ordered=True)
            day_counts = day_counts.sort_values(columns_info['day'])
            fig_day = px.bar(day_counts, x=columns_info['day'], y='Count', title='Accidents by Day of the Week')
            st.plotly_chart(fig_day, use_container_width=True)

    with tab2:
        if columns_info['severity']:
            severity_counts = df_filtered[columns_info['severity']].value_counts().reset_index()
            severity_counts.columns = [columns_info['severity'], 'Count']
            fig_severity = px.pie(severity_counts, values='Count', names=columns_info['severity'], title='Accident Severity Distribution', hole=0.4)
            st.plotly_chart(fig_severity, use_container_width=True)

        if columns_info['weather']:
            weather_counts = df_filtered[columns_info['weather']].value_counts().nlargest(10).reset_index()
            weather_counts.columns = [columns_info['weather'], 'Count']
            fig_weather = px.bar(weather_counts, x=columns_info['weather'], y='Count', title='Top 10 Weather Conditions in Accidents')
            st.plotly_chart(fig_weather, use_container_width=True)

    with tab3:
        if all(columns_info[k] for k in ['speed', 'casualties', 'road']):
            sample_size = min(1000, len(df_filtered))
            df_sample = df_filtered.sample(sample_size) if len(df_filtered) > sample_size else df_filtered
            fig_scatter = px.scatter(df_sample, x=columns_info['speed'], y=columns_info['casualties'], color=columns_info['road'], title='Speed Limit vs. Casualties by Road Condition')
            st.plotly_chart(fig_scatter, use_container_width=True)

    with tab4:
        if columns_info['lat'] and columns_info['long']:
            st.subheader("Accident Locations on Map")
            map_data = df_filtered.dropna(subset=[columns_info['lat'], columns_info['long']])

            if not map_data.empty:
                map_sample = map_data.head(500) if len(map_data) > 500 else map_data
                m = folium.Map(location=[map_sample[columns_info['lat']].mean(), map_sample[columns_info['long']].mean()], zoom_start=6)
                marker_cluster = folium.plugins.MarkerCluster().add_to(m)

                for _, row in map_sample.iterrows():
                    popup_text = f"Date: {row['Accident Date'].date()}"
                    if columns_info['location']:
                        popup_text += f"<br>{columns_info['location']}: {row[columns_info['location']]}"
                    if columns_info['severity']:
                        popup_text += f"<br>Severity: {row[columns_info['severity']]}"
                    folium.Marker([row[columns_info['lat']], row[columns_info['long']]], popup=popup_text).add_to(marker_cluster)

                folium_static(m)
            else:
                st.warning("No valid coordinate data available for map visualization.")
else:
    st.warning("No data available to display.")
# streamlit run roadaccident.py