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
                             map_title=''):
    """
    Generates an interactive HTML map from a shapefile.
    
    Args:
        shapefile_path (str): Path to the .shp file.
        output_html (str): Filename for the output HTML map.
        map_title (str): Title to display at the top of the map.
    """

    desc_col = map_cols.get('DESCRIPTION')
    dat_col = map_cols.get('PCT')
    details_col = map_cols.get('DETAILS')
    # 1. Validate required columns
    required_cols = ["HUNTAREA", dat_col, desc_col, details_col]
    missing_cols = [col for col in required_cols if col not in gdf.columns]
    if missing_cols:
        print(f"Error: The following required columns are missing: {missing_cols}")
        return

    # Ensure PCT is numeric for coloring
    gdf[dat_col] = pd.to_numeric(gdf[dat_col], errors='coerce').fillna(0)

    # 2. Initialize the Map
    # Reproject to WGS84 (EPSG:4326) which is required for Folium/Leaflet
    if gdf.crs != "EPSG:4326":
        print("Reprojecting data to WGS84 (EPSG:4326)...")
        gdf = gdf.to_crs("EPSG:4326")

    # Center map on the data
    center_lat = gdf.geometry.centroid.y.mean()
    center_lon = gdf.geometry.centroid.x.mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="CartoDB positron")
    # Add Title to the map
    title_html = f'''
     <div style="position: fixed; 
     top: 10px; left: 50%; transform: translateX(-50%); width: auto; height: auto; 
     z-index:9999; font-size:20px; font-weight:bold; background-color: rgba(255, 255, 255, 0.8); 
     padding: 10px; border: 1px solid black; border-radius: 5px;">
     {map_title}
     </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    # 3. Create Color Scale
    # Linear colormap from 0 to max (Red to Green)
    colormap = cm.LinearColormap(
        colors=['yellow',  'orange','red' ], 
        vmin=0, 
        vmax= np.ceil(np.max(gdf[dat_col]))
    )
    colormap.caption = f"Percentage ({dat_col})"

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
        tooltip=folium.GeoJsonTooltip(
            fields=[f'{desc_col}', f'{details_col}', f'{dat_col}', 'landowner_tags_per_total'],
            aliases=['Description:', 'Details:', 'Percentage of Quota:', 'Landowner Tags/Total:'],
            # fields=['Description', f'{details_col}'], 
            # aliases=['Description:', 'Details:'],
            style="font-family: sans-serif; font-size: 14px;",
            localize=True,
            sticky=True # Tooltip follows mouse
        )
    ).add_to(m)

    # 5. Add Labels (HUNTAREA) at Centroids
    print("Adding labels...")
    for _, row in gdf.iterrows():
        # Get centroid for label placement
        centroid = row.geometry.centroid
        label_text = str(row['HUNTAREA'])
        
        # Add a text label using DivIcon
        folium.map.Marker(
            [centroid.y, centroid.x],
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
    m.save(output_html)
    print(f"Map successfully generated: {output_html}")