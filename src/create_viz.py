import pandas as pd
import numpy as np
import os
from get_data import ComtradeData, iso2name_map

from millify import millify

import plotly.graph_objects as go


class ComtradeExportMap:
    def __init__(self, data):
        self.data = data
        self.fig = go.Figure()
        self.export_traces = {}
        self.import_traces = {}
        self.flow_trace_indices = {}
        
        # Build the complete visualization
        self._add_choropleths()
        self._create_and_add_flow_traces()
        self._setup_layout_and_controls()
        
    @staticmethod
    def round_middle_values(arr: list[float]):
        if len(arr) < 3:
            return arr
        def _round(x):
            p = 10**np.floor(np.log10(x))
            return int(round(x/p)*p)
        _middle = [_round(x) for x in arr[1:-1]]
        return [arr[0]] + _middle + [arr[-1]]
        
    def _add_choropleths(self):
        export_country_names = [
            iso2name_map.get(country, country) 
            for country in self.data.exports['country'].to_list()
        ]
        
        # Create country names for imports  
        import_country_names = [
            iso2name_map.get(country, country) 
            for country in self.data.imports['country'].to_list()
        ]
        
        """Add choropleth layers for exports and imports"""
        # Exports choropleth
        _zmax = self.data.exports['log_value'].max()
        _tick_vals = self.round_middle_values(np.linspace(0, _zmax, 5))
        _tick_text = ["$"+millify(10**x, precision=0) for x in _tick_vals]
        _tick_text[0] = "$0"
        
        self.fig.add_trace(
            go.Choropleth(
                locations=self.data.exports['country'],
                z=self.data.exports['log_value'],
                locationmode='ISO-3',
                text=export_country_names,
                hovertemplate='<b>%{text}</b><br>' +
                            'Export Value: US$%{customdata[0]:,.0f}<br>' +
                            'Top 5 Partners: %{customdata[1]}' +
                            '<br><i>Click to show export flows</i><extra></extra>',
                customdata=list(
                    zip(
                        self.data.exports['value'], 
                        self.data.exports['top5_partners']
                    )
                ),
                colorscale='Blues',
                visible=True,
                name="Exports",
                zmin=0,
                zmax=_zmax,
                colorbar=dict(
                    title="Export Value",
                    x=0.5,
                    y=-0.2,
                    len=0.7,
                    tickmode='array',
                    tickvals=_tick_vals,
                    ticktext=_tick_text,
                    orientation='h',
                    xanchor='center',
                    yanchor='bottom'
                )
            )
        )
        
        # Imports choropleth
        _zmax = self.data.imports['log_value'].max()
        _tick_vals = self.round_middle_values(np.linspace(0, _zmax, 5))
        _tick_text = ["$"+millify(10**x, precision=0) for x in _tick_vals]
        _tick_text[0] = "$0"
        
        self.fig.add_trace(
            go.Choropleth(
                locations=self.data.imports['country'],
                z=self.data.imports['log_value'],
                locationmode='ISO-3',
                text=import_country_names,
                hovertemplate='<b>%{text}</b><br>' +
                            'Import Value: US$%{customdata[0]:,.0f}<br>' +
                            'Top 5 Partners: %{customdata[1]}' +
                            '<br><i>Click to show import flows</i><extra></extra>',
                customdata=list(
                    zip(
                        self.data.imports['value'], 
                        self.data.imports['top5_partners']
                        )
                    ),
                colorscale='Greens',
                visible=False,
                name="Imports",
                zmin=0,
                zmax=_zmax,
                colorbar=dict(
                    title="Import Value",
                    x=0.5,
                    y=-0.2,
                    len=0.7,
                    tickmode='array',
                    tickvals=_tick_vals,
                    ticktext=_tick_text,
                    orientation='h',
                    xanchor='center',
                    yanchor='bottom'
                )
            )
        )
    
    def _create_and_add_flow_traces(self):
        """Create and add all flow traces to the figure"""
        export_indices = {}
        import_indices = {}
        
        # Create export flow traces
        for country in self.data.all['exporter'].unique():
            country_data = self.data.all[self.data.all['exporter'] == country].copy()
            
            if len(country_data) == 0:
                continue
                
            # Calculate normalized line widths
            country_data['log_value'] = country_data['value'].apply(
                lambda x: 0 if x < 1 else np.log10(x)
            )
            max_log = country_data['log_value'].max()
            if max_log > 0:
                country_data['normalized_width'] = 1 + (4 * country_data['log_value'] / max_log)
            else:
                country_data['normalized_width'] = 1
            
            indices = []
            for _, row in country_data.iterrows():
                _country_name = iso2name_map.get(country, country)
                _partner_name = iso2name_map.get(row['partner'], row['partner'])
                self.fig.add_trace(
                    go.Scattergeo(
                        locations=[country, row['partner']],
                        locationmode='ISO-3',
                        hovertemplate=f"<b>{_country_name} → {_partner_name}</b><br>" +
                                    f"Value: US${row['value']:,.0f}<br>" +
                                    f"Quantity: {row['quantity']:,.0f} litres<extra></extra>",
                        mode='lines+markers',
                        line=dict(
                            width=row['normalized_width'],
                            color='rgba(255, 165, 0, 0.5)'  # Orange
                        ),
                        marker=dict(size=3, color='red'),
                        visible=False,
                        showlegend=False,
                        name=f"export_flow_{country}_{row['partner']}"
                    )
                )
                indices.append(len(self.fig.data) - 1)
            
            if indices:
                export_indices[country] = indices
        
        # Create import flow traces
        for country in self.data.all['partner'].unique():
            country_data = self.data.all[self.data.all['partner'] == country].copy()
            
            if len(country_data) == 0:
                continue
                
            # Calculate normalized line widths
            country_data['log_value'] = country_data['value'].apply(
                lambda x: 0 if x < 1 else np.log10(x)
            )
            max_log = country_data['log_value'].max()
            if max_log > 0:
                country_data['normalized_width'] = 1 + (4 * country_data['log_value'] / max_log)
            else:
                country_data['normalized_width'] = 1
            
            indices = []
            for _, row in country_data.iterrows():
                _country_name = iso2name_map.get(country, country)
                _exporter_name = iso2name_map.get(row['exporter'], row['exporter'])
                self.fig.add_trace(
                    go.Scattergeo(
                        locations=[row['exporter'], country],
                        locationmode='ISO-3',
                        hovertemplate=f"<b>{_exporter_name} → {_country_name}</b><br>" +
                                    f"Value: US${row['value']:,.0f}<br>" +
                                    f"Quantity: {row['quantity']:,.0f} litres<extra></extra>",
                        mode='lines+markers',
                        line=dict(
                            width=row['normalized_width'],
                            color='rgba(255, 165, 0, 0.5)'  # Orange
                        ),
                        marker=dict(size=3, color='red'),
                        visible=False,
                        showlegend=False,
                        name=f"import_flow_{row['exporter']}_{country}"
                    )
                )
                indices.append(len(self.fig.data) - 1)
            
            if indices:
                import_indices[country] = indices
        
        self.flow_trace_indices = {
            "export": export_indices,
            "import": import_indices
        }
    
    def _create_click_handlers(self):
        """Generate JavaScript code for handling map clicks"""
        export_countries = self.data.exports['country'].tolist()
        import_countries = self.data.imports['country'].tolist()
        
        # Create mapping dictionaries for JavaScript
        export_flow_map = {}
        for country, indices in self.flow_trace_indices['export'].items():
            if country in export_countries:
                country_index = export_countries.index(country)
                export_flow_map[country_index] = indices
        
        import_flow_map = {}
        for country, indices in self.flow_trace_indices['import'].items():
            if country in import_countries:
                country_index = import_countries.index(country)
                import_flow_map[country_index] = indices
        
        total_traces = len(self.fig.data)
        
        # JavaScript code for click handling
        click_handler_js = f"""
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var gd = document.getElementById('{{plot_div}}');
            
            // Flow trace mappings
            var exportFlowMap = {export_flow_map};
            var importFlowMap = {import_flow_map};
            var totalTraces = {total_traces};
            
            console.log('Trade map initialized');
            
            // Handle plotly clicks
            gd.on('plotly_click', function(data) {{
                var point = data.points[0];
                var traceIndex = point.fullData.index;
                var pointIndex = point.pointIndex;
                
                console.log('Clicked trace:', traceIndex, 'point:', pointIndex);
                
                // Step 1: Hide all flow traces (everything except the first 2 choropleths)
                var hidePromise = Plotly.restyle(gd, 'visible', false, Array.from({{length: totalTraces - 2}}, (_, i) => i + 2));
                
                hidePromise.then(function() {{
                    var flowsToShow = [];
                    
                    // Step 2: Determine which flows to show
                    if (traceIndex === 0 && exportFlowMap[pointIndex]) {{
                        flowsToShow = exportFlowMap[pointIndex];
                        console.log('Showing export flows:', flowsToShow);
                    }} else if (traceIndex === 1 && importFlowMap[pointIndex]) {{
                        flowsToShow = importFlowMap[pointIndex];
                        console.log('Showing import flows:', flowsToShow);
                    }}
                    
                    // Step 3: Show only the selected flows
                    if (flowsToShow.length > 0) {{
                        return Plotly.restyle(gd, 'visible', true, flowsToShow);
                    }}
                }}).catch(function(error) {{
                    console.error('Error updating traces:', error);
                }});
            }});
        }});
        </script>
        """
        
        return click_handler_js
    
    def _setup_layout_and_controls(self):
        """Configure layout with dropdown menus and styling"""
        n_flow_traces = len(self.fig.data) - 2
        
        self.fig.update_layout(
            title={
                'text': f"Global Trade for {self.data._commodity} ({self.data._period})<br>" +
                    f"<sub>UN Comtrade data • Click countries to show trade routes</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=[
                        dict(
                            args=[{"visible": [True, False] + [False] * n_flow_traces}],
                            label="Exports View",
                            method="restyle"
                        ),
                        dict(
                            args=[{"visible": [False, True] + [False] * n_flow_traces}],
                            label="Imports View", 
                            method="restyle"
                        )
                    ],
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=0.5,
                    xanchor="center",
                    y=1.0,  # Position relative to plot area
                    yanchor="bottom"
                ),
            ],
            
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor="lightgray",
                projection_type='natural earth',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                showocean=True,
                oceancolor='rgb(204, 235, 255)',
                showcountries=True,
                countrycolor="white",
                domain=dict(x=[0, 1], y=[0, 0.9])
            ),
            
            height=700,
            margin=dict(t=150, b=80, l=50, r=50),
            font=dict(size=12),
        )
            
            # annotations=[
            #     dict(
            #         text="💡 Line thickness represents trade volume magnitude",
            #         showarrow=False,
            #         xref="paper", yref="paper",
            #         x=0.02, y=0.02,
            #         xanchor="left", yanchor="bottom",
            #         font=dict(size=11, color="gray"),
            #         bgcolor="rgba(255,255,255,0.8)",
            #         bordercolor="gray",
            #         borderwidth=1
            #     )
            # ]
        # )
    
    def create_file_name(self):
        return f"comtrade_{self.data._commodity}_{self.data._period}.html"
    
    def save_html(self, filename=None, include_plotlyjs=True):
        """
        Save the interactive map as standalone HTML
        
        Args:
            filename: Output HTML filename
            include_plotlyjs: Whether to include Plotly.js in the HTML file
        """
        if filename is None:
            filename = self.create_file_name()
            
        if not filename.endswith(".html"):
            filename += "html"
        
        # Generate the click handler JavaScript
        click_js = self._create_click_handlers()
        
        # Save the figure
        html_string = self.fig.to_html(
            include_plotlyjs=include_plotlyjs,
            div_id="trade-map-div"
        )
        
        # Insert the click handler JavaScript
        html_string = html_string.replace(
            'div_id="trade-map-div"',
            'div_id="trade-map-div"'
        ).replace(
            '</body>',
            click_js.replace('{plot_div}', 'trade-map-div') + '\n</body>'
        )
        
        with open(os.path.join('plots', filename), 'w', encoding='utf-8') as f:
            f.write(html_string)
        
        print(f"Interactive trade map saved as '{filename}'")
        print(f"Total traces: {len(self.fig.data)} (2 choropleths + {len(self.fig.data)-2} flow traces)")
        
        return filename

# Usage function
def create_trade_visualization(commodity: str | int, period: int, filename=None):
    """
    Create a complete interactive trade visualization
    
    Args:
        commodity: The HS Code (or name) of the commodity
        period: The year for which to display annual trade data
        output_file: Output HTML filename
    
    Returns:
        ComtradeExportMap instance
    """
    print("Creating trade visualization...")
    
    # Import the data
    data = ComtradeData(period=period, commodity_code=commodity)
    print("Imported Comtrade data")
    
    # Create the map
    trade_map = ComtradeExportMap(data)
    
    # Save as HTML
    output_file = trade_map.save_html(filename=filename)
    
    print(f"Visualization complete! Open '{output_file}' in your browser.")
    
    return trade_map