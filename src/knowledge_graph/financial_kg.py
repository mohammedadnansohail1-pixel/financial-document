"""
Financial Knowledge Graph Construction
Implements entity-event-risk hierarchy for financial analysis
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass, field
import json
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Node in the knowledge graph"""
    node_id: str
    node_type: str
    properties: Dict[str, Any]
    timestamp: Optional[datetime] = None


@dataclass
class GraphEdge:
    """Edge in the knowledge graph"""
    edge_id: str
    source_id: str
    target_id: str
    relationship: str
    properties: Dict[str, Any]
    confidence: float = 1.0
    timestamp: Optional[datetime] = None


class FinancialKnowledgeGraph:
    """
    Financial Knowledge Graph following FEEKG (Financial Entity-Event-Knowledge Graph) pattern
    Implements entity-event-risk hierarchy
    """

    def __init__(self):
        # Define graph schema
        self.schema = {
            'entities': {
                'Company': ['name', 'ticker', 'cik', 'sector', 'market_cap', 'founded_date'],
                'Executive': ['name', 'position', 'tenure', 'company'],
                'Product': ['name', 'category', 'revenue_contribution', 'launch_date'],
                'Risk': ['type', 'severity', 'probability', 'impact', 'mitigation'],
                'Event': ['type', 'date', 'description', 'impact', 'participants'],
                'Metric': ['name', 'value', 'period', 'unit', 'change_pct'],
                'Sector': ['name', 'industry', 'market_size'],
                'Document': ['type', 'date', 'source', 'cik']
            },
            'relationships': {
                'OPERATES_IN': ('Company', 'Sector'),
                'LED_BY': ('Company', 'Executive'),
                'PRODUCES': ('Company', 'Product'),
                'EXPOSED_TO': ('Company', 'Risk'),
                'EXPERIENCED': ('Company', 'Event'),
                'REPORTS': ('Company', 'Metric'),
                'COMPETES_WITH': ('Company', 'Company'),
                'SUPPLIES_TO': ('Company', 'Company'),
                'CORRELATES_WITH': ('Metric', 'Metric'),
                'MENTIONED_IN': ('Entity', 'Document'),
                'TRIGGERED_BY': ('Event', 'Event'),
                'MITIGATES': ('Event', 'Risk')
            }
        }

        # In-memory graph storage (in production, use Neo4j or TigerGraph)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)

        logger.info("Initialized Financial Knowledge Graph")

    def add_node(self, node: GraphNode) -> str:
        """Add node to graph"""
        self.nodes[node.node_id] = node
        logger.debug(f"Added node: {node.node_id} ({node.node_type})")
        return node.node_id

    def add_edge(self, edge: GraphEdge) -> str:
        """Add edge to graph"""
        self.edges[edge.edge_id] = edge
        self.adjacency_list[edge.source_id].append(edge.target_id)
        logger.debug(f"Added edge: {edge.source_id} -> {edge.target_id} ({edge.relationship})")
        return edge.edge_id

    def construct_from_filing(self, filing_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Build knowledge graph from processed filing data
        Returns dict of created node and edge IDs
        """
        logger.info(f"Constructing graph from filing: {filing_data.get('document_id')}")

        created = {
            'nodes': [],
            'edges': []
        }

        # Extract company information
        company_node = self._create_company_node(filing_data)
        created['nodes'].append(self.add_node(company_node))

        # Extract and add financial metrics
        if 'chunks' in filing_data:
            for chunk in filing_data['chunks']:
                if chunk.get('chunk_type') == 'table' and 'metrics' in chunk:
                    metrics = chunk['metrics']
                    for metric_name, metric_data in metrics.items():
                        metric_node = self._create_metric_node(
                            metric_name,
                            metric_data,
                            filing_data
                        )
                        node_id = self.add_node(metric_node)
                        created['nodes'].append(node_id)

                        # Create REPORTS relationship
                        edge = self._create_edge(
                            company_node.node_id,
                            metric_node.node_id,
                            'REPORTS',
                            {
                                'period': filing_data.get('filing_date'),
                                'source_document': filing_data.get('document_id')
                            }
                        )
                        created['edges'].append(self.add_edge(edge))

        # Extract risk factors
        risk_nodes = self._extract_risk_factors(filing_data)
        for risk_node in risk_nodes:
            node_id = self.add_node(risk_node)
            created['nodes'].append(node_id)

            # Create EXPOSED_TO relationship
            edge = self._create_edge(
                company_node.node_id,
                risk_node.node_id,
                'EXPOSED_TO',
                {
                    'severity': risk_node.properties.get('severity', 'medium'),
                    'identified_date': filing_data.get('filing_date')
                }
            )
            created['edges'].append(self.add_edge(edge))

        # Extract events from narrative
        event_nodes = self._extract_events(filing_data)
        for event_node in event_nodes:
            node_id = self.add_node(event_node)
            created['nodes'].append(node_id)

            # Create EXPERIENCED relationship
            edge = self._create_edge(
                company_node.node_id,
                event_node.node_id,
                'EXPERIENCED',
                {
                    'date': event_node.properties.get('date'),
                    'impact': event_node.properties.get('impact')
                }
            )
            created['edges'].append(self.add_edge(edge))

        # Create document node
        doc_node = self._create_document_node(filing_data)
        created['nodes'].append(self.add_node(doc_node))

        # Link company to document
        edge = self._create_edge(
            company_node.node_id,
            doc_node.node_id,
            'MENTIONED_IN',
            {'relevance': 1.0}
        )
        created['edges'].append(self.add_edge(edge))

        logger.info(f"Created {len(created['nodes'])} nodes and {len(created['edges'])} edges")
        return created

    def _create_company_node(self, filing_data: Dict[str, Any]) -> GraphNode:
        """Create company node from filing data"""
        company_id = f"company_{filing_data.get('cik', filing_data.get('company', '').replace(' ', '_'))}"

        return GraphNode(
            node_id=company_id,
            node_type='Company',
            properties={
                'name': filing_data.get('company', ''),
                'cik': filing_data.get('cik'),
                'ticker': filing_data.get('ticker', ''),
                'sector': filing_data.get('sector', ''),
            },
            timestamp=filing_data.get('filing_date')
        )

    def _create_metric_node(
        self,
        metric_name: str,
        metric_data: Any,
        filing_data: Dict[str, Any]
    ) -> GraphNode:
        """Create financial metric node"""
        metric_id = f"metric_{filing_data.get('company', '')}_{metric_name}_{filing_data.get('filing_date', '')}"
        metric_id = metric_id.replace(' ', '_').replace('/', '_')

        # Extract value if it's a dict
        value = metric_data
        if isinstance(metric_data, dict):
            value = metric_data.get('value', metric_data)

        return GraphNode(
            node_id=metric_id,
            node_type='Metric',
            properties={
                'name': metric_name,
                'value': str(value),
                'period': filing_data.get('filing_date'),
                'unit': self._infer_metric_unit(metric_name),
                'company': filing_data.get('company')
            },
            timestamp=filing_data.get('filing_date')
        )

    def _create_document_node(self, filing_data: Dict[str, Any]) -> GraphNode:
        """Create document node"""
        doc_id = f"doc_{filing_data.get('document_id', '')}"

        return GraphNode(
            node_id=doc_id,
            node_type='Document',
            properties={
                'type': filing_data.get('document_type', ''),
                'date': filing_data.get('filing_date'),
                'source': 'SEC_EDGAR',
                'cik': filing_data.get('cik', ''),
                'document_id': filing_data.get('document_id', '')
            },
            timestamp=filing_data.get('filing_date')
        )

    def _create_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        properties: Dict[str, Any],
        confidence: float = 1.0
    ) -> GraphEdge:
        """Create edge between nodes"""
        edge_id = f"{source_id}_{relationship}_{target_id}"

        return GraphEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            properties=properties,
            confidence=confidence,
            timestamp=properties.get('date') or properties.get('period')
        )

    def _extract_risk_factors(self, filing_data: Dict[str, Any]) -> List[GraphNode]:
        """Extract risk factors from filing"""
        risk_nodes = []

        if 'chunks' not in filing_data:
            return risk_nodes

        for chunk in filing_data['chunks']:
            if chunk.get('section_type') != 'risk_factors':
                continue

            # Simple risk extraction based on keywords
            text = chunk.get('text', '').lower()

            risk_types = {
                'market_risk': ['market volatility', 'market conditions', 'economic downturn'],
                'operational_risk': ['operations', 'operational challenges', 'supply chain'],
                'regulatory_risk': ['regulatory', 'compliance', 'legal'],
                'credit_risk': ['credit', 'default', 'counterparty'],
                'liquidity_risk': ['liquidity', 'cash flow', 'funding']
            }

            for risk_type, keywords in risk_types.items():
                for keyword in keywords:
                    if keyword in text:
                        risk_id = f"risk_{filing_data.get('company', '')}_{risk_type}_{filing_data.get('filing_date', '')}"
                        risk_id = risk_id.replace(' ', '_')

                        risk_node = GraphNode(
                            node_id=risk_id,
                            node_type='Risk',
                            properties={
                                'type': risk_type,
                                'severity': 'medium',  # Would need ML model to classify
                                'probability': 'unknown',
                                'description': text[:200],
                                'source_document': filing_data.get('document_id')
                            },
                            timestamp=filing_data.get('filing_date')
                        )
                        risk_nodes.append(risk_node)
                        break

        return risk_nodes

    def _extract_events(self, filing_data: Dict[str, Any]) -> List[GraphNode]:
        """Extract significant events from filing"""
        event_nodes = []

        if 'chunks' not in filing_data:
            return event_nodes

        # Look for event indicators in text
        event_keywords = {
            'acquisition': ['acquired', 'acquisition', 'merger'],
            'product_launch': ['launched', 'introduced', 'released'],
            'executive_change': ['appointed', 'resigned', 'promoted'],
            'restructuring': ['restructuring', 'reorganization', 'workforce reduction'],
            'investment': ['invested', 'capital expenditure', 'capex']
        }

        for chunk in filing_data['chunks']:
            if chunk.get('chunk_type') != 'narrative':
                continue

            text = chunk.get('text', '').lower()

            for event_type, keywords in event_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        event_id = f"event_{filing_data.get('company', '')}_{event_type}_{filing_data.get('filing_date', '')}"
                        event_id = event_id.replace(' ', '_')

                        event_node = GraphNode(
                            node_id=event_id,
                            node_type='Event',
                            properties={
                                'type': event_type,
                                'date': filing_data.get('filing_date'),
                                'description': text[:200],
                                'impact': 'unknown',  # Would need sentiment analysis
                                'source_document': filing_data.get('document_id')
                            },
                            timestamp=filing_data.get('filing_date')
                        )
                        event_nodes.append(event_node)
                        break

        return event_nodes

    def _infer_metric_unit(self, metric_name: str) -> str:
        """Infer unit for financial metric"""
        metric_lower = metric_name.lower()

        if 'revenue' in metric_lower or 'income' in metric_lower or 'profit' in metric_lower:
            return 'USD'
        elif 'margin' in metric_lower or 'rate' in metric_lower:
            return 'percentage'
        elif 'shares' in metric_lower:
            return 'shares'
        elif 'eps' in metric_lower:
            return 'USD_per_share'
        else:
            return 'unknown'

    def query_by_entity(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Query graph starting from an entity
        """
        if entity_id not in self.nodes:
            return {'nodes': [], 'edges': []}

        visited_nodes = set()
        visited_edges = set()

        def traverse(node_id: str, depth: int):
            if depth > max_depth or node_id in visited_nodes:
                return

            visited_nodes.add(node_id)

            # Get all edges from this node
            for edge_id, edge in self.edges.items():
                if edge.source_id != node_id:
                    continue

                # Filter by relationship type if specified
                if relationship_type and edge.relationship != relationship_type:
                    continue

                visited_edges.add(edge_id)
                traverse(edge.target_id, depth + 1)

        traverse(entity_id, 0)

        return {
            'nodes': [self.nodes[nid] for nid in visited_nodes],
            'edges': [self.edges[eid] for eid in visited_edges]
        }

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        Find paths between two entities
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return []

        paths = []

        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return

            if current == target:
                paths.append(path.copy())
                return

            for next_node in self.adjacency_list.get(current, []):
                if next_node not in path:  # Avoid cycles
                    path.append(next_node)
                    dfs(next_node, target, path, depth + 1)
                    path.pop()

        dfs(source_id, target_id, [source_id], 0)
        return paths

    def get_temporal_subgraph(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Extract subgraph for a temporal range
        """
        filtered_nodes = []
        filtered_edges = []

        for node in self.nodes.values():
            if node.timestamp and start_date <= node.timestamp <= end_date:
                filtered_nodes.append(node)

        for edge in self.edges.values():
            if edge.timestamp and start_date <= edge.timestamp <= end_date:
                filtered_edges.append(edge)

        return {
            'nodes': filtered_nodes,
            'edges': filtered_edges
        }

    def export_to_cypher(self, output_file: str):
        """
        Export graph to Cypher queries for Neo4j
        """
        cypher_statements = []

        # Create nodes
        for node in self.nodes.values():
            props_str = ", ".join([
                f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}"
                for k, v in node.properties.items()
            ])

            cypher = f"CREATE (n:{node.node_type} {{id: '{node.node_id}', {props_str}}})"
            cypher_statements.append(cypher)

        # Create relationships
        for edge in self.edges.values():
            props_str = ", ".join([
                f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}"
                for k, v in edge.properties.items()
            ])

            cypher = f"""
            MATCH (a {{id: '{edge.source_id}'}}), (b {{id: '{edge.target_id}'}})
            CREATE (a)-[:{edge.relationship} {{confidence: {edge.confidence}, {props_str}}}]->(b)
            """
            cypher_statements.append(cypher)

        # Write to file
        with open(output_file, 'w') as f:
            f.write(";\n".join(cypher_statements))
            f.write(";")

        logger.info(f"Exported {len(cypher_statements)} Cypher statements to {output_file}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics"""
        node_types = defaultdict(int)
        edge_types = defaultdict(int)

        for node in self.nodes.values():
            node_types[node.node_type] += 1

        for edge in self.edges.values():
            edge_types[edge.relationship] += 1

        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'node_types': dict(node_types),
            'edge_types': dict(edge_types)
        }
