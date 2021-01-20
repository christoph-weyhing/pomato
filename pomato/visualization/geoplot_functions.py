"""Collection of functions used in the generation of the GeoPlot."""

import pandas as pd
import numpy as np
import scipy

def merc(lat, lon):
    """convert lat lon to x,y"""
    r_major = 6378137.000
    coord_x = r_major * np.radians(lon)
    scale = coord_x/lon
    coord_y = 180.0/np.pi * np.log(np.tan(np.pi/4.0 + lat * (np.pi/180.0)/2.0)) * scale
    return(coord_x, coord_y)

def _build_raster(nodes, plot_width, plot_hight, alpha=4):
    """Build Raster for prices layer"""

    raster = np.zeros((plot_width, plot_hight))
    known_points_coords = [[b.x, b.y] for i,b in nodes.iterrows()]
    raster[nodes.x.values, nodes.y.values] = nodes.marginal.values

    raster_coords = np.array([[x,y] for x in range(plot_width) for y in range(plot_hight)])
    distance_matrix = scipy.spatial.distance.cdist(raster_coords, known_points_coords)
    condition = np.all(distance_matrix > 0, axis=1)
    distance_matrix = distance_matrix[condition]
    tmp = np.divide(1.0, np.power(distance_matrix, alpha))
    raster_values = tmp.dot(nodes.marginal.values)/tmp.sum(axis=1)
    
    for i, (x, y) in enumerate(raster_coords[condition]):
        raster[x, y] = raster_values[i]
    return raster

def add_prices_layer(nodes, prices, compress=True):
    """Adds prices layer to Geoplot"""

    if compress:
        # price[price.marginal >= 1000]
        # prices.loc[prices.marginal > 100] = 100

        quantile = .1
        prices.loc[prices.marginal > prices.marginal.quantile(1 - quantile), "marginal"] = prices.marginal.quantile(1 - quantile)
        prices.loc[prices.marginal < prices.marginal.quantile(quantile), "marginal"] = prices.marginal.quantile(quantile)

    nodes = pd.merge(nodes[["lat", "lon"]], prices, left_index=True, right_index=True)
    
    lat, lon = list(nodes.lat.values), list(nodes.lon.values)

    lat.extend([min(lat) - 4, max(lat) + 4])
    lon.extend([min(lon) - 8, max(lon) + 8])
    # Calculate plot dimensions
    xx, yy = merc(np.array(lat), np.array(lon))
    ratio = (max(xx) - min(xx))/(max(yy) - min(yy))
    size = (max(yy) - min(yy))/5e4
    # prices Plot Coordinates (0,0) (plot_width, plot_hight)
    x = ((xx - min(xx))/max(xx - min(xx))*ratio*size).astype(int)
    y = ((yy - min(yy))/max(yy - min(yy))*size).astype(int)
    nodes["x"], nodes["y"] = x[:-2], y[:-2]
    plot_width, plot_hight = x.max(), y.max()
    prices_layer = _build_raster(nodes, plot_width, plot_hight, alpha=8)
    
    lon_min, lon_max = min(lon), max(lon)
    lat_min, lat_max = min(lat), max(lat)
    corners = [[lon_max, lat_min], [lon_max, lat_max], 
               [lon_min, lat_max], [lon_min, lat_min], ]

    return prices_layer, corners, plot_hight/plot_width


def line_colors(lines, n_0_flows, n_1_flows,
                option=0, range_start=0, range_end=100):
    """Line colors in 10 shades of RedYellowGreen palette"""
    ## 0: N-0 Flows, 1: N-1 Flows 2: Line voltage levels
    # timesteps = 't'+ "{0:0>4}".format(int(slider.value))
    stepsize = round((range_end - range_start)/10, 3)
    steps = [range_start + i*stepsize for i in range(0, 10)]
    RdYlGn = ('#006837', '#1a9850', '#66bd63', '#a6d96a', '#d9ef8b', 
              '#fee08b', '#fdae61', '#f46d43', '#d73027', '#a50026') 
    if option == 0:
        n_0_flows = n_0_flows.to_frame()
        n_0_flows.columns = ["flow"]
        n_0_flows["alpha"] = 0.4
        n_0_flows["color"] = RdYlGn[0]
        for idx, loading in enumerate(steps):
            condition = abs(n_0_flows.flow.values)/lines.capacity > loading/100
            n_0_flows.loc[condition, "color"] = RdYlGn[idx]
        color = list(n_0_flows.color.values)
        line_alpha = list(n_0_flows.alpha.values)

    elif option == 1:
        n_1_flows = n_1_flows.to_frame()
        n_1_flows.columns = ["flow"]
        n_1_flows["alpha"] = 0.4
        n_1_flows["color"] = RdYlGn[0]
        for idx, loading in enumerate(steps):
            condition = abs(n_1_flows.flow.values)/lines.capacity > loading/100
            n_1_flows.loc[condition, "color"] = RdYlGn[idx]
        color = list(n_1_flows.color.values)
        line_alpha = list(n_1_flows.alpha.values)
    elif option == 2:
        color = create_voltage_colors(lines)
        line_alpha = [0.6 for i in lines.index]

    return color, line_alpha

def line_coordinates(lines, nodes):
    # Add Columns to lines with total systems and an index
    # so each line from a system has an relative index e.g. 1/3 or 4/5
    tmp = lines[["node_i", "node_j"]].copy()
    tmp["systems"] = 1
    tmp = tmp.groupby(["node_i", "node_j"]).sum()
    tmp = tmp.reset_index()
    lines["systems"] = 1
    lines["no"] = 1
    for node_i, node_j, systems in zip(tmp.node_i, tmp.node_j, tmp.systems):
        condition = (lines.node_i == node_i)&(lines.node_j == node_j)
        lines.loc[condition, "systems"] = systems
        # np.array bc of bug when assigning a 2-elm list
        lines.loc[condition, "no"] = np.array([nr for nr in range(0, systems)])

    lx, ly = [], []
    for l in lines.index:
        xi, yi = (nodes.lat[lines.node_i[l]], nodes.lon[lines.node_i[l]])
        xj, yj = (nodes.lat[lines.node_j[l]], nodes.lon[lines.node_j[l]])
        mx = xj - xi
        my = yj - yi
        # multiple lines are spread across a circle with radius d around each node
        # starting from PI/4 in equal steps (in angle) to -PI/4 from reference point
        # reference point is the intersection of the circle and the line to the other node
        # the 20 and pi/5 are purely visual
        d = 0.05*np.power((np.sqrt(np.power(mx, 2) + np.power(my, 2))), 1/2)
        if lines.systems[l] == 1:
            idx = 0
        else:
            idx = lines.no[l]/(lines.systems[l] - 1) - 0.5
        if mx == 0:
            alpha = np.pi/4*idx + np.pi/2
            alpha2 = 3/2*np.pi - np.pi/4*idx
        elif mx > 0: # bottom left -> top right | top left -> bottom right
            alpha = np.arctan(my/mx) + np.pi/4*idx
            alpha2 = np.arctan(my/mx) + np.pi - np.pi/4*idx
        elif mx < 0: # bottom right -> top left | top right -> bottom right
            alpha2 = np.arctan(my/mx) + np.pi/4*idx
            alpha = np.arctan(my/mx) + np.pi - np.pi/4*idx

        # lx contains start point, point on circle for multiple lines on start point,
        # a point 1/2 of the way for the hover menus to stick to
        # point on circle for multiple lines on end point, end point
        lx.append([xi, xi + np.cos(alpha)*d,
                   0.5*(xi + np.cos(alpha)*d + xj + np.cos(alpha2)*d),
                   xj + np.cos(alpha2)*d, xj])
        ly.append([yi, yi + np.sin(alpha)*d,
                   0.5*(yi + np.sin(alpha)*d + yj + np.sin(alpha2)*d),
                   yj + np.sin(alpha2)*d, yj])
    return lx, ly

def create_voltage_colors(lines): 
    #{380: 'red', 400: 'red', 220: 'green', 232: 'green', 165: 'grey', 150: 'grey', 132: 'black'}
    if not "voltage" in lines.columns:
        lines[["voltage"]] = lines[["type"]].copy()
    tmp = lines[["voltage"]].copy()
    tmp["voltage"] = lines.loc[:, "voltage"].apply(pd.to_numeric, errors='coerce')
    tmp["color"] = ""
    for line in tmp.index:
        if tmp.loc[line, "voltage"] > 500:
            tmp.loc[line, "color"] = "blue"
        elif tmp.loc[line, "voltage"] > 300:
            tmp.loc[line, "color"] = "red"
        elif tmp.loc[line, "voltage"] > 200:
            tmp.loc[line, "color"] = "green" 
        elif tmp.loc[line, "voltage"] > 100:
            tmp.loc[line, "color"] = "black" 
        elif tmp.loc[line, "voltage"] <= 100:
            tmp.loc[line, "color"] = "grey" 
        else:
            tmp.loc[line, "color"] = "purple"

    return list(tmp.color)