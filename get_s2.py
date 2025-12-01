import streamlit as st
import leafmap.foliumap as leafmap
import s2sphere

st.set_page_config(page_title="S2 Cell Finder", layout="centered")

st.title("📍 Leafmap S2 Finder")
st.markdown("Click anywhere on the map to get the **Level 13 S2 Cell ID**.")

# --- Helper Function: S2 Calculation ---
def get_s2_cell_info(lat, lng, level=13):
    """Calculates S2 Cell ID from Lat/Long."""
    p = s2sphere.LatLng.from_degrees(lat, lng)
    cell = s2sphere.CellId.from_lat_lng(p).parent(level)
    return {
        "id_int": str(cell.id()),
        "id_token": cell.to_token(),
        "level": level
    }

# --- Leafmap Setup ---
# We use leafmap.foliumap to ensure it works smoothly in Streamlit
m = leafmap.Map(center=[22.5, 82.0], zoom=4, locate_control=True)

# Add a simple instruction to the map directly
m.add_title("Click to find S2 Cell", font_size="20px", align="center")

# --- Render Map & Capture Click ---
# m.to_streamlit() renders the map and returns the interaction data
map_data = m.to_streamlit(height=600, bidirectional=True)

# --- Process Click ---
# Leafmap returns the click data in the 'last_clicked' key
if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lng = map_data["last_clicked"]["lng"]
    
    # Calculate S2
    s2_info = get_s2_cell_info(clicked_lat, clicked_lng)
    
    st.divider()
    st.subheader("✅ Selected Location")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.info(f"**Lat:** {clicked_lat:.5f}\n\n**Lng:** {clicked_lng:.5f}")
        
    with c2:
        st.success(f"**S2 Cell ID:**\n\n`{s2_info['id_int']}`")
        st.caption(f"Token: {s2_info['id_token']}")
    
    st.warning("Copy the S2 Cell ID above for your Agri API.")

else:
    st.info("👆 Click on the map to see the S2 Cell ID.")