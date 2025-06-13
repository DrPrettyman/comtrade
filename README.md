# Comtrade

Create visualisations of Comtrade trade data (imports/exports).

Creates a plotly figure and writes to an html file.

The figure shows a choropleth world map color-coded with import/export values in US$. Interative buttons to switch between exports and imports. Click on a country to see trade routes to all trading partners with hover text showing values and quantities. 

## Example usage

Using commodity name:
```
python3 src/main.py wine 2023
```
or using HS code for commodity: 
```
python3 src/main.py 2204 2023
```
