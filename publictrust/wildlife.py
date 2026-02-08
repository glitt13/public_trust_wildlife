import tabula
import pandas as pd
import requests
import io
import numpy as np
import geopandas as gpd
import folium
from folium.features import DivIcon
import branca.colormap as cm
from pathlib import Path

def parse_pdf_to_dataframe(pdf_url,
                           colnames=['Hunt_Area', 'Type', "Description", "Quota", "Issued","PP","Applicants"]):
    """
    Reads a PDF from a URL, parses tables, and returns a pandas DataFrame.

    Args:
        pdf_url (str): The URL of the PDF file.

    Returns:
        pandas.DataFrame: A DataFrame containing the data from the tables in the PDF.
                          Returns an empty DataFrame if no tables are found or an error occurs.
    """
    try:
        # It's a good practice to download the content first
        response = requests.get(pdf_url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Use an in-memory byte stream
        pdf_file = io.BytesIO(response.content)

        # Parse pdf
        list_of_dataframes = tabula.read_pdf(pdf_file, pages='all', multiple_tables=True,pandas_options={'header':None})

        if not list_of_dataframes:
            print("Warning: No tables were found in the PDF.")
            return pd.DataFrame()

        # Concatenate all the extracted DataFrames into one.
        # This is useful if a single table spans multiple pages.

        df_all = pd.concat(list_of_dataframes)
        df_all.columns = colnames
        if 'Type' in df_all.columns:
            df_all['Type'] = df_all['Type'].astype(str).str.replace('.0','')
        if 'Hunt_Area' in df_all.columns:
            df_all['Hunt_Area']=df_all['Hunt_Area'].astype(str)
        
        print("Successfully parsed PDF and created DataFrame.")
        return df_all

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the PDF from the URL: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred during PDF parsing: {e}")
        print("Please ensure you have Java installed and accessible in your system's PATH.")
        return pd.DataFrame()
    



def create_interactive_map(gdf, output_html="hunting_map.html",
                           map_cols = {'DESCRIPTION':'Description',
                                        'PCT':'pct_landowner',
                                        'DETAILS':'HUNTNAME'},
                             map_title='',
                             color_thr = 40.0):
    """
    Generates an interactive HTML map from a shapefile.
    
    Args:
        shapefile_path (str): Path to the .shp file.
        output_html (str): Filename for the output HTML map.
        map_title (str): Title to display at the top of the map.
    """
    output_html = Path(output_html).expanduser()
    desc_col = map_cols.get('DESCRIPTION')
    dat_col = map_cols.get('PCT')
    details_col = map_cols.get('DETAILS')

    # 1. Validate required columns
    required_cols = ["HUNTAREA", dat_col, desc_col, details_col]
    missing_cols = [col for col in required_cols if col not in gdf.columns]
    if missing_cols:
        print(f"Error: The following required columns are missing: {missing_cols}")
        return

    # 2. Initialize the Map
    # Reproject to WGS84 (EPSG:4326) which is required for Folium/Leaflet
    if gdf.crs != "EPSG:4326":
        print("Reprojecting data to WGS84 (EPSG:4326)...")
        gdf = gdf.to_crs("EPSG:4326")


    # Ensure PCT is numeric for coloring
    gdf[dat_col] = pd.to_numeric(gdf[dat_col], errors='coerce').fillna(0)

    
    # Center map on the data
    center_lat = gdf.geometry.centroid.y.mean()
    center_lon = gdf.geometry.centroid.x.mean()
    #m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="CartoDB positron")
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=7, # Start a bit wider for mobile context
        tiles="CartoDB positron",
        scrollWheelZoom=False, # Prevents accidental zooming while scrolling
        dragging=True          # Keeps panning enabled
    )
    # Add Title to the map
    # Use Media Queries in the title_html to adjust size based on screen width
    title_html = f'''
    <style>
        .map-title {{
            position: fixed; 
            top: 10px; left: 50%; transform: translateX(-50%); 
            z-index:9999; font-weight:bold; 
            background-color: rgba(255, 255, 255, 0.9); 
            padding: 5px 10px; border: 1px solid black; border-radius: 5px;
            font-size: 16px; width: 80%; text-align: center;
        }}
        @media (min-width: 600px) {{
            .map-title {{ font-size: 20px; width: auto; }}
        }}
    </style>
    <div class="map-title">{map_title}</div>
    '''

    m.get_root().html.add_child(folium.Element(title_html))
    # 3. Create Color Scale
    # Linear colormap from 0 to max (Red to Green)
    max_val = max(np.ceil(np.max(gdf[dat_col])), 100) # Ensure scale goes to at least 100

    # Define colors: Low (Yellow/Green) -> Transition (Orange) -> High (Deep Red)
    colors = ['#ffffcc', '#fd8d3c', '#bd0026'] 
    index = [0, color_thr,  color_thr + 0.01, max_val] # Creates the "snap" at 40%

    colormap = cm.LinearColormap(
        colors=colors,
        vmin=0,
        vmax=max_val,
        index=[0, color_thr, max_val], # Areas below 40 are one color, above are another
        caption=f"Percentage of Quota ({dat_col})"
    )
    # colormap = cm.LinearColormap(
    #     colors=['yellow',  'orange','red' ], 
    #     vmin=0, 
    #     vmax= np.ceil(np.max(gdf[dat_col]))
    # )
    #colormap.caption = f"Percentage ({dat_col})"
    colormap.caption = f"% {dat_col}"

    # Mobile-Friendly CSS Injection
    # This targets the title AND moves the legend to the bottom on small screens
    mobile_style = f'''
    <style>
        /* Title responsiveness */
        .map-title {{
            position: fixed; 
            top: 10px; left: 50%; transform: translateX(-50%); 
            z-index:9999; font-weight:bold; 
            background-color: rgba(255, 255, 255, 0.9); 
            padding: 5px 10px; border: 1px solid black; border-radius: 5px;
            font-size: 16px; width: 80%; text-align: center;
        }}
        
        /* Legend mobile placement */
        @media (max-width: 600px) {{
            .map-title {{ font-size: 14px; width: 85%; }}
            
            /* Target the branca colormap container */
            .leaflet-control-container .leaflet-bottom.leaflet-right {{
                width: 90% !important;
                left: 5% !important;
                right: 5% !important;
            }}
            .legend {{
                position: fixed !important;
                bottom: 30px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                width: 90% !important;
                background-color: rgba(255, 255, 255, 0.85) !important;
                padding: 10px !important;
                border-radius: 8px !important;
                box-shadow: 0 0 15px rgba(0,0,0,0.2) !important;
            }}
        }}
    </style>
    <div class="map-title">{map_title}</div>
    '''
    m.get_root().header.add_child(folium.Element(mobile_style))

    # 4. Add Polygons with Coloring and Hover Popup (Tooltip)
    print("Adding polygons and hover interactions...")
    
    # Style function determines the look of each polygon based on its properties
    def style_function(feature):
        pct_value = feature['properties'][dat_col]
        return {
            'fillColor': colormap(pct_value),
            'color': 'black',      # Border color
            'weight': 1,           # Border width
            'fillOpacity': 0.7
        }

    # GeoJson layer handles the geometry and hover events
    folium.GeoJson(
    gdf,
    style_function=style_function,
    popup=folium.GeoJsonPopup(
        fields=[f'{desc_col}', f'{details_col}', f'{dat_col}', 'landowner_tags_per_total'],
        aliases=['Description:', 'Details:', 'Pct Landowner:', 'LO Tags/Total:'],
        style="font-family: sans-serif; font-size: 12px; width: 200px;", # Fixed width for mobile
    )
    ).add_to(m)

    # 5. Add Labels (HUNTAREA) at Centroids
    print("Adding labels...")
    for _, row in gdf.iterrows():
        # Get centroid for label placement
        point = row.geometry.representative_point()
        centroid = row.geometry.centroid
        label_text = str(row['HUNTAREA'])
        
        # Add a text label using DivIcon
        folium.map.Marker(
            [point.y, point.x],
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 18), # Center the anchor
                html=f'''<div style="
                    font-size: 10pt; 
                    color: black; 
                    font-weight: bold; 
                    text-align: center; 
                    text-shadow: 1px 1px 0 #fff;">{label_text}</div>'''
            )
        ).add_to(m)

    # Add the legend to the map
    m.add_child(colormap)
    

    Path(output_html).parent.mkdir(parents=True,exist_ok=True)
    # Save output
    try:
        m.save(output_html)
        print(f"Map successfully generated: {output_html}")
    except Exception as e:
        print(f"COULD NOT WRITE MAP {e}")