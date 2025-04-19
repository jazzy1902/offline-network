"""
Network module for the Disaster Mesh application.
Handles peer-to-peer communication and network discovery.
"""

try:
    # When running as a module
    from disaster_mesh.src.network.mesh_node import DisasterMeshNode
except ImportError:
    # When running directly
    from src.network.mesh_node import DisasterMeshNode

__all__ = ['DisasterMeshNode'] 