import streamlit as st
import requests
import json
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
import s2sphere
import os

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Agri API Landscape Monitor")

st.title("🌱 Agricultural Landscape Monitor")

# --- Sidebar: Inputs ---
st.sidebar.header("Configuration")

# API Key Input (Use a secure way to handle keys in production)
api_key_input = os.getenv("API_KEY_AGRI", "")
# Fallback for demo purposes if user doesn't input one (Optional)
# api_key = api_key_input if api_key_input else "YOUR_FALLBACK_KEY" 
api_key = api_key_input

# S2 Cell Input
s2_cell_id = st.sidebar.text_input("S2 Cell ID", value="3486736072451293184")

# Fetch Button
fetch_button = st.sidebar.button("Fetch Data", type="primary")

# --- Crop Legend Mapping ---
CROP_COLORS = {
    "NO_PREDICTION": "#CCCCCC",
    "UNKNOWN_CROP": "#999999",
    "BAJRA": "#8B4513",
    "CHILLI": "#FF0000",
    "CORN": "#FFD700",
    "COTTON": "#FFFFFF",
    "GRAM": "#DEB887",
    "GROUNDNUT": "#CD853F",
    "MUSTARD": "#FFFF00",
    "RICE": "#90EE90",
    "SORGHUM": "#A0522D",
    "SOYBEANS": "#228B22",
    "SUGARCANE": "#00CED1",
    "WHEAT": "#F4A460"
}

# --- Helper Functions ---

def fetch_agri_data(api_key, cell_id):
    """Calls the Agricultural Monitoring API."""
    url = f"https://agriculturalunderstanding.googleapis.com/v1:monitorLandscape?key={api_key}"
    
    payload = {
        "locationSpecifier": {
            "s2CellId": cell_id
        },
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        with st.spinner("Fetching data from API..."):
            resp = requests.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Request Failed: {e}")
        return None

def timestamp_to_month_year(timestamp):
    """Convert Unix timestamp to 'Month Year' format."""
    if timestamp and timestamp > 0:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%B %Y")
    return "N/A"

def parse_geojson_data(api_response):
    """Parse the API response and extract GeoJSON features."""
    try:
        monitored_landscape = api_response.get("monitoredLandscape", {})
        geojson_str = monitored_landscape.get("geojson", "{}")
        geojson_data = json.loads(geojson_str)
        return geojson_data
    except Exception as e:
        st.error(f"Error parsing GeoJSON: {e}")
        return None

def get_latest_time_period(features):
    """Get the latest time period from features."""
    latest_period = None
    max_timestamp = 0
    
    for feature in features:
        predictions = feature.get("properties", {}).get("monitoring_prediction", [])
        for pred in predictions:
            start_ts = pred.get("start_timestamp_sec", 0)
            end_ts = pred.get("end_timestamp_sec", 0)
            
            if start_ts > max_timestamp and start_ts > 0 and end_ts > 0:
                max_timestamp = start_ts
                latest_period = {
                    "period_key": f"{start_ts}_{end_ts}",
                    "label": f"{timestamp_to_month_year(start_ts)} - {timestamp_to_month_year(end_ts)}",
                    "start_ts": start_ts,
                    "end_ts": end_ts
                }
    
    return latest_period

def get_crop_color(crop_name):
    """Get color for a crop type."""
    crop_upper = crop_name.upper().replace(" ", "_")
    return CROP_COLORS.get(crop_upper, "#666666")

def create_feature_popup(feature, use_latest=True):
    """Create HTML popup content for a feature."""
    props = feature.get("properties", {})
    predictions = props.get("monitoring_prediction", [])
    
    # Get the latest prediction for this field (or first available)
    selected_pred = None
    if predictions:
        if use_latest:
            # Find the prediction with the latest timestamp
            selected_pred = max(predictions, key=lambda p: p.get("start_timestamp_sec", 0))
        else:
            selected_pred = predictions[0]
    
    if not selected_pred:
        return "No data available"
    
    crop_pred = selected_pred.get("crop_prediction", {})
    
    html = f"""
    <div style="font-family: Arial; font-size: 12px; min-width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #2E7D32;">Field Information</h4>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 4px; font-weight: bold;">Field ID:</td>
                <td style="padding: 4px;">{feature.get('id', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 4px; font-weight: bold;">Area:</td>
                <td style="padding: 4px;">{props.get('area_sq_m', 0):.2f} m²</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 4px; font-weight: bold;">Season:</td>
                <td style="padding: 4px;">{timestamp_to_month_year(selected_pred.get('start_timestamp_sec'))} - {timestamp_to_month_year(selected_pred.get('end_timestamp_sec'))}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding: 8px 4px 4px 4px; font-weight: bold; color: #1976D2;">Primary Crop:</td>
            </tr>
            <tr>
                <td style="padding: 4px; padding-left: 20px;">Crop:</td>
                <td style="padding: 4px;">{crop_pred.get('crop_1', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 4px; padding-left: 20px;">Confidence:</td>
                <td style="padding: 4px;">{crop_pred.get('conf_1', 0):.2%}</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td colspan="2" style="padding: 8px 4px 4px 4px; font-weight: bold; color: #1976D2;">Secondary Crop:</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 4px; padding-left: 20px;">Crop:</td>
                <td style="padding: 4px;">{crop_pred.get('crop_2', 'N/A')}</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 4px; padding-left: 20px;">Confidence:</td>
                <td style="padding: 4px;">{crop_pred.get('conf_2', 0):.2%}</td>
            </tr>
        </table>
    </div>
    """
    return html

def create_map(geojson_data, cell_id_input, use_latest=True):
    """Create a Folium map with the GeoJSON data."""
    features = geojson_data.get("features", [])
    
    if not features:
        st.warning("No features found in the data.")
        return None
    
    # --- FIX START: Convert S2 Cell ID string to Lat/Lng ---
    try:
        # Convert the string input (e.g., "3486736072451293184") to an integer, then to CellId
        cell_id_obj = s2sphere.CellId(int(cell_id_input))
        lat_lng = cell_id_obj.to_lat_lng()
        
        # Convert to degrees
        center_lat = lat_lng.lat().degrees
        center_lon = lat_lng.lng().degrees
    except ValueError:
        st.error("Invalid S2 Cell ID format. Please ensure it is a numeric ID.")
        return None
    except Exception as e:
        st.error(f"Error calculating map center: {e}")
        return None
    # --- FIX END ---
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")
    
    # Add features to map
    for feature in features:
        props = feature.get("properties", {})
        predictions = props.get("monitoring_prediction", [])
        
        # Get the latest prediction for this specific field
        crop_name = "NO_PREDICTION"
        if predictions:
            latest_pred = max(predictions, key=lambda p: p.get("start_timestamp_sec", 0))
            crop_pred = latest_pred.get("crop_prediction", {})
            crop_name = crop_pred.get("crop_1", "NO_PREDICTION")
        
        # Get color
        color = get_crop_color(crop_name)
        
        # Create popup
        popup_html = create_feature_popup(feature, use_latest=True)
        popup = folium.Popup(popup_html, max_width=350)
        
        # Add to map
        folium.GeoJson(
            feature,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            popup=popup
        ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4 style="margin-top:0;">Crop Legend</h4>
    '''
    
    for crop, color in CROP_COLORS.items():
        crop_display = crop.replace("_", " ").title()
        legend_html += f'<p><span style="background-color:{color}; width:20px; height:20px; display:inline-block; border:1px solid black;"></span> {crop_display}</p>'
    
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def prepare_csv_data(geojson_data):
    """Prepare data for CSV export."""
    features = geojson_data.get("features", [])
    rows = []
    
    for feature in features:
        props = feature.get("properties", {})
        predictions = props.get("monitoring_prediction", [])
        
        for pred in predictions:
            crop_pred = pred.get("crop_prediction", {})
            row = {
                "Field_ID": feature.get("id", ""),
                "Area_sqm": props.get("area_sq_m", 0),
                "ALU_Type": props.get("alu_type", ""),
                "Class_Confidence": props.get("class_confidence", 0),
                "Season_Start": timestamp_to_month_year(pred.get("start_timestamp_sec", 0)),
                "Season_End": timestamp_to_month_year(pred.get("end_timestamp_sec", 0)),
                "Primary_Crop": crop_pred.get("crop_1", ""),
                "Primary_Confidence": crop_pred.get("conf_1", 0),
                "Secondary_Crop": crop_pred.get("crop_2", ""),
                "Secondary_Confidence": crop_pred.get("conf_2", 0),
                "Tertiary_Crop": crop_pred.get("crop_3", ""),
                "Tertiary_Confidence": crop_pred.get("conf_3", 0)
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

# --- Main App Logic ---

# Initialize session state
if "geojson_data" not in st.session_state:
    st.session_state.geojson_data = None
if "latest_period" not in st.session_state:
    st.session_state.latest_period = None
if "raw_response" not in st.session_state:
    st.session_state.raw_response = None

# Fetch data when button is clicked
if fetch_button:
    if not api_key:
        st.error("Please enter an API key.")
    else:
        api_response = fetch_agri_data(api_key, s2_cell_id)
        if api_response:
            st.session_state.raw_response = api_response
            geojson_data = parse_geojson_data(api_response)
            if geojson_data:
                st.session_state.geojson_data = geojson_data
                features = geojson_data.get("features", [])
                st.session_state.latest_period = get_latest_time_period(features)
                st.success(f"Data fetched successfully! Found {len(features)} fields.")

# Display map and controls if data is available
if st.session_state.geojson_data and st.session_state.latest_period:
    
    # Display selected time period
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"📅 **Displaying Latest Season Data")
    
    with col2:
        # Download button
        csv_data = prepare_csv_data(st.session_state.geojson_data)
        csv = csv_data.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"agri_landscape_{s2_cell_id}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # --- FIX START: Correct arguments passed to create_map ---
    # 1. First argument is geojson_data (matching function def)
    # 2. Second argument is s2_cell_id (the actual variable from inputs)
    folium_map = create_map(st.session_state.geojson_data, s2_cell_id, use_latest=True)
    # --- FIX END ---
    
    if folium_map:
        st_folium(folium_map, width=1400, height=600)
    
    # Display statistics
    st.subheader("📊 Summary Statistics")
    features = st.session_state.geojson_data.get("features", [])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Fields", len(features))
    with col2:
        total_area = sum(f.get("properties", {}).get("area_sq_m", 0) for f in features)
        st.metric("Total Area", f"{total_area:.2f} m²")
    with col3:
        avg_area = total_area / len(features) if features else 0
        st.metric("Avg Field Area", f"{avg_area:.2f} m²")
    
    # Display Raw JSON Response
    st.markdown("---")
    st.subheader("📄 Raw API Response")
    
    with st.expander("View Raw JSON Data", expanded=False):
        if st.session_state.raw_response:
            # Pretty print JSON
            st.json(st.session_state.raw_response)
            
            # Add download button for raw JSON
            json_str = json.dumps(st.session_state.raw_response, indent=2)
            st.download_button(
                label="📥 Download Raw JSON",
                data=json_str,
                file_name=f"agri_raw_response_{s2_cell_id}.json",
                mime="application/json"
            )
else:
    st.info("👈 Enter your API key and S2 Cell ID, then click 'Fetch Data' to begin.")