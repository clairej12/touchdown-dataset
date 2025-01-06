import sys
import os
import config
import pdb

class Node:
    def __init__(self, panoid, pano_yaw_angle, lat, lng):
        self.panoid = panoid
        self.pano_yaw_angle = pano_yaw_angle
        self.neighbors = {}
        self.coordinate = (lat, lng)


class Graph:
    def __init__(self):
        self.nodes = {}
        
    def add_node(self, panoid, pano_yaw_angle, lat, lng):
        self.nodes[panoid] = Node(panoid, int(pano_yaw_angle), lat, lng)

    def add_edge(self, start_panoid, end_panoid, heading):
        start_node = self.nodes[start_panoid]
        end_node = self.nodes[end_panoid]
        start_node.neighbors[int(heading)] = end_node


class GraphLoader:
    def __init__(self, node_file = None, link_file = None):
        self.graph = Graph()
        self.node_file = config.paths['node'] if not node_file else node_file
        self.link_file = config.paths['link'] if not link_file else link_file

    def construct_graph(self):
        with open(self.node_file) as f:
            for line in f:
                panoid, pano_yaw_angle, lat, lng = line.strip().split(',')
                self.graph.add_node(panoid, int(pano_yaw_angle), float(lat), float(lng))

        with open(self.link_file) as f:
            for line in f:
                start_panoid, heading, end_panoid = line.strip().split(',')
                self.graph.add_edge(start_panoid, end_panoid, int(heading))

        num_edges = 0
        for panoid in self.graph.nodes.keys():
            num_edges += len(self.graph.nodes[panoid].neighbors)

        print('===== Graph loaded =====')
        print('Number of nodes:', len(self.graph.nodes))
        print('Number of edges:', num_edges)
        print('========================')
        return self.graph

class GraphWriter:
    def __init__(self, node_file='nodes.txt', edge_file='edges.txt'):
        """
        Initialize the GraphWriter.

        :param graph: The graph object to write.
        :param node_file: The file to write node information.
        :param edge_file: The file to write edge information.
        """
        self.node_file = node_file
        self.edge_file = edge_file

    def write_nodes(self):
        """
        Write nodes to the node file.
        """
        with open(self.node_file, 'w') as f:
            for panoid, node in self.graph.nodes.items():
                f.write(f"{node.panoid},{node.pano_yaw_angle},{node.coordinate[0]},{node.coordinate[1]}\n")

    def write_edges(self):
        """
        Write edges to the edge file.
        """
        with open(self.edge_file, 'w') as f:
            for start_panoid, start_node in self.graph.nodes.items():
                for heading, end_node in start_node.neighbors.items():
                    f.write(f"{start_panoid},{heading},{end_node.panoid}\n")

    def write_graph(self, graph):
        """
        Write both nodes and edges to their respective files.
        """
        self.graph = graph
        print('===== Writing Graph to Files =====')
        self.write_nodes()
        print(f"Nodes written to {self.node_file}")
        self.write_edges()
        print(f"Edges written to {self.edge_file}")
        print('===================================')
