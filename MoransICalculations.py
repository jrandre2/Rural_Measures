import geopandas as gpd
import pandas as pd
import libpysal as lps
from esda.moran import Moran

def calculate_morans_i(gdf, variable, w):
    """Calculate Moran's I for a given variable."""
    standardized_var = (gdf[variable] - gdf[variable].mean()) / gdf[variable].std()
    moran = Moran(standardized_var, w)
    return moran.I, moran.p_sim

# Load data
file_path = 'C:/Users/jesse/OneDrive - University of Nebraska at Kearney/Code/HouseholdData.csv'
data = pd.read_csv(file_path)

# Convert DataFrame to GeoDataFrame
gdf = gpd.GeoDataFrame(data, geometry=gpd.points_from_xy(data['X'], data['Y']))

# Spatial weight matrix
w = lps.weights.KNN.from_dataframe(gdf, k=8)
w.transform = 'r'

# Variables
continuous_variables = ['ISPSpeed', 'ISPCompetition', 'ISPAdequate', 'ISPStable' '']
categorical_variables = ['InternetType']

# Calculate Moran's I for each continuous variable
morans_i_results = pd.DataFrame(columns=['Variable', 'Morans_I', 'P_Value'])

for var in continuous_variables:
    morans_i, p_value = calculate_morans_i(gdf, var, w)
    new_row = pd.DataFrame({'Variable': [var], 'Morans_I': [morans_i], 'P_Value': [p_value]})
    morans_i_results = pd.concat([morans_i_results, new_row], ignore_index=True)

# Convert categorical variable to dummies and calculate Moran's I
for var in categorical_variables:
    dummies = pd.get_dummies(data[var], prefix=var)
    for dummy_var in dummies:
        gdf[dummy_var] = dummies[dummy_var]
        morans_i, p_value = calculate_morans_i(gdf, dummy_var, w)
        new_row = pd.DataFrame({'Variable': [dummy_var], 'Morans_I': [morans_i], 'P_Value': [p_value]})
        morans_i_results = pd.concat([morans_i_results, new_row], ignore_index=True)

# Display results
print(morans_i_results)