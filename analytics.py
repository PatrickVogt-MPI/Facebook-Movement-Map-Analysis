import plot
import settings
import sys
import model
import construction as con
import networkx as nx
import numpy as np
import utility as ut
from networkx import Graph
from networkx import DiGraph
from pathlib  import Path
from typing   import List, Set, Dict, Tuple, Optional
from vincenty import vincenty
from tabulate import tabulate

def search_edges(graph: DiGraph, **kwargs) -> List:
    '''
    Searches edges of a graph for property values and returns list of resulting edges

    Args:
        graph:    DiGraph object
        **kwargs: edge property=search value

    Returns:
        edges: list of edges that fulfill the search criteria
    '''
    edges = []
    for id1, id2, data in graph.edges.data():
        if (all(data[key] == value for key, value in kwargs.items())):
            edges.append((id1, id2, data))
    return edges
    
def search_nodes(graph: DiGraph, **kwargs) -> List:
    '''
    Searches nodes of a graph for property values and returns list of resulting nodes

    Args:
        graph:    DiGraph object
        **kwargs: property key=search value

    Returns:
        nodes: list of nodes
    '''
    nodes = []
    for id, data in graph.nodes.data():
        if (all(data[key] == value for key, value in kwargs.items())):
            nodes.append((id, data))           
    return nodes
    
def search_graphs(graphs: list, **kwargs) -> List:
    '''
    Searches a graph for property values and returns list of resulting graphs

    Args:
        graphs:   list of DiGraph objects
        **kwargs: graph property key, search value pairs

    Returns:
        _graphs: list of graphs that fulfill the search criteria
    '''
    _graphs = []
    for graph in graphs:
        if (all(graph.graph[key] == value for key, value in kwargs.items())):
            _graphs.append(graph)
    return _graphs
   
def quadkey_to_tile_coordinates(quadkey: str) -> Tuple[float, float]:
    '''
    https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
    Returns the coordinate representation of a tile.

    Args:
        quadkey: str object

    Returns:
        coordinates: coordinates of tile
    '''
    tile_size = len(quadkey)
    x = y = 0
    for i in range(tile_size, 0, -1):
        mask = 1 << (i-1)
        digit = quadkey[tile_size - i]
        if(digit == '0'): 
            continue
        if(digit == '1'): 
            x |= mask
            continue
        if(digit == '2'): 
            y |= mask
            continue
        if(digit == '3'): 
            x |= mask
            y |= mask
            continue
        print('[ERROR] Invalid quadkey digit sequence.') 
    return (x, y)

def spherical_to_mercator_coordinates(lon: float, lat: float) -> Tuple[float, float]:
    '''
    Converts point in spherical coordinate system to point on mercator map.

    Args:
        lon: longitude (in degrees)
        lat: latitude (in degrees)
        
    Returns:
        (y, x): y- and x-coordinate of point on mercator map
    '''
    earth_radius = 6378137 # WGS-84
    x = earth_radius*lon*np.pi/180
    y = earth_radius*np.log(np.tan(np.pi/4 + lat*np.pi/360))
    return y, x
    
def mercator_to_spherical_coordinates(y: float, x: float) -> Tuple[float, float]:
    '''
    Converts point on mercator map to point in spherical coordinate system.

    Args:
        y: y-coordinate of point on mercator map
        x: x-coordinate of point on mercator map
        
    Returns:
        (lon, lat): longitude and latitude (in degrees)
    '''
    earth_radius = 6378137 #WGS-84
    lon = x / earth_radius * 180 / np.pi
    lat = (2 * np.arctan(np.exp(y / earth_radius)) - np.pi / 2) * 180 / np.pi
    return lon, lat

def get_tile_vertices(lon: float, lat: float, tile_size: int) -> Tuple[float, float, float, float]:
    '''
    Calculates all four (lon, lat) vertex positions of tile.

    Args:
        lon: longitude (in degrees)
        lat: latitude (in degrees)
        
    Returns:
        p0: (lon, lat) of top left corner (in degrees)
        p1: (lon, lat) of top right corner (in degrees)
        p2: (lon, lat) of bottom left corner (in degrees)
        p3: (lon, lat) of bottom right corner (in degrees)
    '''
    tile_length = {
        1:  20015089.262170314752 ,
        2:  10007544.631085157376,
        3:  5003772.315542578688,
        4:  2501886.157771289344 ,
        5:  1250943.078885644672,
        6:  625471.539442822336,
        7:  312735.769721411168,
        8:  156367.884860705584,
        9:  78183.942430352792,
        10: 39091.971215176396,
        11: 19545.985607588198,
        12: 9772.992803794099,
        13: 4886.4964018970495,
        14: 2443.24820094852475,
        15: 1221.624100474262375,
        16: 610.8120502371311875,
    }
    length = tile_length[tile_size]
    (y, x) = spherical_to_mercator_coordinates(lon, lat)
    p0 = mercator_to_spherical_coordinates(y + length/2, x - length/2)
    p1 = mercator_to_spherical_coordinates(y + length/2, x + length/2)
    p2 = mercator_to_spherical_coordinates(y - length/2, x - length/2)
    p3 = mercator_to_spherical_coordinates(y - length/2, x + length/2)
    return p0, p1, p2, p3

def orthodrome_length(lat1, lon1, lat2, lon2):
    '''
        Calculates the length of the orthodrome between two point using vincentys algorithm (https://en.wikipedia.org/wiki/Vincenty%27s_formulae).
        The precision is 5mm on the WGS-84 ellipsoid.
        
        Args:
            lon1: longitude of first point in degrees
            lat1: latitude of first point in degrees
            lon2: longitude of second point in degrees
            lat2: latitude of second point in degrees
            
        Returns:
            length: length of orthodrome in meters
    '''
    
    length = vincenty((lat1, lon1), (lat2, lon2))*1000
    return length
    
    
if __name__ == '__main__':
    ########################################################################
    ### Please ignore code below - just me quickly testing code snippets ###
    ########################################################################
    
    #sys.stdout = open('output.txt', 'w')
    
    movement_path            = settings.paths['movement_path']
    admin_movement_path      = settings.paths['admin_movement_path']
    population_path          = settings.paths['population_path']
    admin_population_path    = settings.paths['admin_population_path']
    compiled_population_path = r'D:\Eigene Dokumente\Arbeit\Studium\Bachelorarbeit\Data\Facebook\Germany Coronavirus Disease Prevention Map Mar 26 2020\Facebook Population (Tile Level) Graphs'
    root                     = settings.paths['root']
    '''
    graph = con.administrative_radiation_graph(next(ut.file_list(admin_population_path)), country = 'DE')
    
    sp = []
    for id1, id2, data in graph.edges.data():
        sp.append([graph.nodes[id1]["polygon_name"], graph.nodes[id1]["population"], graph.nodes[id2]["polygon_name"], graph.nodes[id2]["population"], "{0:.2%}".format(data["probability"])])
    print(tabulate(sp, headers = ['source', 'population', 'destination', 'population', 'commuting probability']))
    '''
    print(con.cumulated_infected('2020-06-01', '2020-06-07'))