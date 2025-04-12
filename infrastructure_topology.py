"""
Infrastructure topology visualization module for AWS chaos engineering platform.
"""
import streamlit as st
import pandas as pd
import random
import math
from datetime import datetime, timedelta

# AWS service icons (simple emoji representation)
AWS_ICONS = {
    'ec2': '💻',
    'rds': '🗄️',
    'lambda': 'λ',
    's3': '📦',
    'dynamodb': '📊',
    'elb': '⚖️',
    'cloudfront': '🌐',
    'route53': '🔄',
    'vpc': '🔒',
    'subnet': '🔗',
    'security_group': '🛡️',
    'api_gateway': '🚪',
    'sns': '📨',
    'sqs': '📋',
    'alarm': '🔔',
    'healthy': '✅',
    'degraded': '⚠️',
    'failed': '❌'
}

class InfrastructureTopology:
    """
    Class to create and update AWS infrastructure topology visualization.
    """
    def __init__(self):
        """Initialize the topology with default AWS components."""
        # Define AWS components
        self.nodes = {
            # VPC and Network
            'vpc': {'type': 'vpc', 'label': 'VPC', 'tier': 'network', 'dependencies': []},
            'public_subnet_1': {'type': 'subnet', 'label': 'Public Subnet 1', 'tier': 'network', 'dependencies': ['vpc']},
            'public_subnet_2': {'type': 'subnet', 'label': 'Public Subnet 2', 'tier': 'network', 'dependencies': ['vpc']},
            'private_subnet_1': {'type': 'subnet', 'label': 'Private Subnet 1', 'tier': 'network', 'dependencies': ['vpc']},
            'private_subnet_2': {'type': 'subnet', 'label': 'Private Subnet 2', 'tier': 'network', 'dependencies': ['vpc']},
            
            # Load Balancer
            'alb': {'type': 'elb', 'label': 'Application Load Balancer', 'tier': 'balancer', 'dependencies': ['public_subnet_1', 'public_subnet_2']},
            
            # EC2 Instances
            'web_server_1': {'type': 'ec2', 'label': 'Web Server 1', 'tier': 'web', 'dependencies': ['alb', 'public_subnet_1']},
            'web_server_2': {'type': 'ec2', 'label': 'Web Server 2', 'tier': 'web', 'dependencies': ['alb', 'public_subnet_2']},
            'app_server_1': {'type': 'ec2', 'label': 'App Server 1', 'tier': 'app', 'dependencies': ['web_server_1', 'web_server_2', 'private_subnet_1']},
            'app_server_2': {'type': 'ec2', 'label': 'App Server 2', 'tier': 'app', 'dependencies': ['web_server_1', 'web_server_2', 'private_subnet_2']},
            
            # Databases
            'primary_db': {'type': 'rds', 'label': 'Primary RDS', 'tier': 'data', 'dependencies': ['app_server_1', 'app_server_2', 'private_subnet_1']},
            'replica_db': {'type': 'rds', 'label': 'Read Replica', 'tier': 'data', 'dependencies': ['primary_db', 'private_subnet_2']},
            
            # Other services
            's3_bucket': {'type': 's3', 'label': 'S3 Storage', 'tier': 'storage', 'dependencies': ['app_server_1', 'app_server_2']},
            'lambda_function': {'type': 'lambda', 'label': 'Lambda Processor', 'tier': 'compute', 'dependencies': ['queue', 'api_gateway']},
            'queue': {'type': 'sqs', 'label': 'SQS Queue', 'tier': 'messaging', 'dependencies': ['app_server_1', 'app_server_2']},
            'api_gateway': {'type': 'api_gateway', 'label': 'API Gateway', 'tier': 'api', 'dependencies': []}
        }
        
        # Initialize node states
        self.node_states = {node_id: 'healthy' for node_id in self.nodes}
        
        # Store history of state changes for animation
        self.state_history = []
        
        # Create a list of connections (edges)
        self.edges = []
        for node_id, node_info in self.nodes.items():
            for dep in node_info['dependencies']:
                self.edges.append((dep, node_id))
    
    def apply_chaos_action(self, action_description):
        """
        Update the topology based on a chaos action.
        
        Args:
            action_description (str): Description of the chaos action.
        
        Returns:
            list: Affected nodes and their new states.
        """
        affected_nodes = []
        
        # Determine which components are affected based on the action description
        if "EC2" in action_description:
            # EC2 instance failure or CPU stress
            candidates = [node_id for node_id, info in self.nodes.items() if info['type'] == 'ec2']
            if candidates:
                target = random.choice(candidates)
                new_state = 'failed' if "termination" in action_description else 'degraded'
                self.node_states[target] = new_state
                affected_nodes.append((target, new_state))
                
                # Also affect dependent nodes
                self._propagate_impact(target, 0.5)  # 50% chance to propagate issues
        
        elif "RDS" in action_description or "database" in action_description:
            # Database issues
            candidates = [node_id for node_id, info in self.nodes.items() if info['type'] == 'rds']
            if candidates:
                target = random.choice(candidates)
                new_state = 'degraded'
                self.node_states[target] = new_state
                affected_nodes.append((target, new_state))
                
                # Also affect dependent nodes
                self._propagate_impact(target, 0.3)  # 30% chance to propagate issues
        
        elif "network" in action_description or "latency" in action_description:
            # Network latency issues - affect network components
            candidates = [node_id for node_id, info in self.nodes.items() if info['tier'] in ['network', 'balancer']]
            if candidates:
                targets = random.sample(candidates, min(2, len(candidates)))
                for target in targets:
                    self.node_states[target] = 'degraded'
                    affected_nodes.append((target, 'degraded'))
                    
                    # Also affect dependent nodes
                    self._propagate_impact(target, 0.7)  # 70% chance to propagate network issues
        
        elif "API" in action_description or "throttling" in action_description:
            # API issues
            api_nodes = [node_id for node_id, info in self.nodes.items() if info['type'] == 'api_gateway']
            if api_nodes:
                for node in api_nodes:
                    self.node_states[node] = 'degraded'
                    affected_nodes.append((node, 'degraded'))
                    
                    # Also affect dependent nodes
                    self._propagate_impact(node, 0.4)  # 40% chance to propagate API issues
        
        elif "Lambda" in action_description:
            # Lambda issues
            lambda_nodes = [node_id for node_id, info in self.nodes.items() if info['type'] == 'lambda']
            if lambda_nodes:
                for node in lambda_nodes:
                    self.node_states[node] = 'degraded'
                    affected_nodes.append((node, 'degraded'))
                    
                    # Also affect dependent nodes
                    self._propagate_impact(node, 0.2)  # 20% chance to propagate Lambda issues
        
        # Record the state change in history
        self.state_history.append({
            'timestamp': datetime.now(),
            'action': 'chaos',
            'description': action_description,
            'affected_nodes': affected_nodes,
            'node_states': self.node_states.copy()
        })
        
        return affected_nodes
    
    def _propagate_impact(self, node_id, probability):
        """
        Propagate impact to dependent nodes with a given probability.
        
        Args:
            node_id (str): The node that is causing the impact.
            probability (float): Probability of propagating the impact.
        """
        # Find nodes that depend on this node
        dependent_nodes = [dep_id for dep_id, info in self.nodes.items() 
                          if node_id in info['dependencies']]
        
        for dep_node in dependent_nodes:
            # Only propagate if the node is still healthy and with the given probability
            if self.node_states[dep_node] == 'healthy' and random.random() < probability:
                self.node_states[dep_node] = 'degraded'
    
    def apply_remediation_action(self, action_description):
        """
        Update the topology based on a remediation action.
        
        Args:
            action_description (str): Description of the remediation action.
        
        Returns:
            list: Restored nodes and their new states.
        """
        restored_nodes = []
        
        # Determine which components are restored based on the action description
        if "EC2" in action_description or "instance" in action_description:
            # EC2 instance restoration
            degraded_ec2 = [node_id for node_id, info in self.nodes.items() 
                           if info['type'] == 'ec2' and self.node_states[node_id] != 'healthy']
            for node in degraded_ec2:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        elif "RDS" in action_description or "database" in action_description:
            # Database restoration
            degraded_dbs = [node_id for node_id, info in self.nodes.items() 
                           if info['type'] == 'rds' and self.node_states[node_id] != 'healthy']
            for node in degraded_dbs:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        elif "network" in action_description or "latency" in action_description:
            # Network restoration
            network_nodes = [node_id for node_id, info in self.nodes.items() 
                            if info['tier'] in ['network', 'balancer'] and self.node_states[node_id] != 'healthy']
            for node in network_nodes:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        elif "API" in action_description or "throttling" in action_description:
            # API restoration
            api_nodes = [node_id for node_id, info in self.nodes.items() 
                        if info['type'] == 'api_gateway' and self.node_states[node_id] != 'healthy']
            for node in api_nodes:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        elif "Lambda" in action_description:
            # Lambda restoration
            lambda_nodes = [node_id for node_id, info in self.nodes.items() 
                           if info['type'] == 'lambda' and self.node_states[node_id] != 'healthy']
            for node in lambda_nodes:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        # When no specific components match, do general healing
        if not restored_nodes:
            # Find any degraded nodes and restore them
            degraded_nodes = [node_id for node_id, state in self.node_states.items() if state != 'healthy']
            for node in degraded_nodes:
                self.node_states[node] = 'healthy'
                restored_nodes.append((node, 'healthy'))
        
        # Record the state change in history
        self.state_history.append({
            'timestamp': datetime.now(),
            'action': 'remediation',
            'description': action_description,
            'restored_nodes': restored_nodes,
            'node_states': self.node_states.copy()
        })
        
        return restored_nodes
    
    def get_node_icon(self, node_id):
        """Get the icon for a node based on its type and state."""
        node_type = self.nodes[node_id]['type']
        node_state = self.node_states[node_id]
        
        # Get the AWS service icon
        icon = AWS_ICONS.get(node_type, '●')
        
        # Add status indicator
        status_icon = AWS_ICONS.get(node_state, '')
        return f"{icon} {status_icon}"
    
    def reset(self):
        """Reset the topology to healthy state."""
        self.node_states = {node_id: 'healthy' for node_id in self.nodes}
        self.state_history = []

# Function to create the topology visualization in Streamlit
def display_infrastructure_topology(topology=None, width=800, height=600, show_controls=True):
    """
    Display the infrastructure topology visualization in Streamlit using Streamlit's built-in components.
    
    Args:
        topology (InfrastructureTopology, optional): Topology object. If None, a new one is created.
        width (int): Width of the figure in pixels (not strictly used, but kept for API compatibility).
        height (int): Height of the figure in pixels (not strictly used, but kept for API compatibility).
        show_controls (bool): Whether to show animation controls.
        
    Returns:
        InfrastructureTopology: The topology object.
    """
    if topology is None:
        topology = InfrastructureTopology()
    
    # Create a container for the visualization
    st.markdown("""
    <style>
    .topology-container {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        background-color: #f5f5f5;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display the topology in a styled container
    with st.container():
        st.markdown('<div class="topology-container">', unsafe_allow_html=True)
        
        # Display infrastructure health status
        healthy_nodes = sum(1 for state in topology.node_states.values() if state == 'healthy')
        total_nodes = len(topology.node_states)
        health_percentage = (healthy_nodes / total_nodes) * 100 if total_nodes > 0 else 100
        
        # Display health status with appropriate color
        if health_percentage >= 90:
            st.success(f"Infrastructure Health: {health_percentage:.1f}% ({healthy_nodes}/{total_nodes} nodes healthy)")
        elif health_percentage >= 60:
            st.warning(f"Infrastructure Health: {health_percentage:.1f}% ({healthy_nodes}/{total_nodes} nodes healthy)")
        else:
            st.error(f"Infrastructure Health: {health_percentage:.1f}% ({healthy_nodes}/{total_nodes} nodes healthy)")
        
        # Group nodes by tier for better visualization
        tiers = {}
        for node_id, node_info in topology.nodes.items():
            tier = node_info['tier']
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append({
                'id': node_id,
                'label': node_info['label'],
                'type': node_info['type'],
                'state': topology.node_states[node_id],
                'icon': topology.get_node_icon(node_id)
            })
        
        # Display interactive AWS infrastructure topology diagram
        st.subheader("AWS Infrastructure Topology")
        
        # Simple AWS infrastructure diagram using tables
        st.write("### AWS Infrastructure Status")
        
        # Group nodes by tier
        tiers = {}
        for node_id, node_info in topology.nodes.items():
            tier = node_info['tier']
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append({
                'id': node_id,
                'label': node_info['label'],
                'type': node_info['type'],
                'state': topology.node_states[node_id],
                'icon': AWS_ICONS.get(node_info['type'], '●')
            })
        
        # Define the tier order and human-readable names
        tier_order = ['network', 'subnet', 'balancer', 'web', 'app', 'data', 'storage', 'messaging', 'compute', 'api']
        tier_names = {
            'network': 'Network Layer',
            'subnet': 'Subnet Layer',
            'balancer': 'Load Balancers',
            'web': 'Web Tier',
            'app': 'Application Tier',
            'data': 'Database Tier',
            'storage': 'Storage Services',
            'messaging': 'Messaging Services', 
            'compute': 'Compute Services',
            'api': 'API Gateway'
        }
        
        # Create a 3-column layout
        cols = st.columns([1, 1, 1])
        
        # Counter to distribute tiers across columns
        col_idx = 0
        
        # Create the infrastructure visualization using tables
        for tier_name in tier_order:
            if tier_name in tiers:
                with cols[col_idx % 3]:
                    # Display tier heading
                    tier_label = tier_names.get(tier_name, tier_name.capitalize())
                    st.markdown(f"#### {tier_label}")
                    
                    # Create tier data
                    tier_data = []
                    for node in tiers[tier_name]:
                        # Set status emoji based on node state
                        status_emoji = "🟢" if node['state'] == 'healthy' else "🟠" if node['state'] == 'degraded' else "🔴"
                        
                        # Add node to tier data
                        tier_data.append({
                            'Service': f"{node['icon']} {node['label']}",
                            'Status': f"{status_emoji} {node['state'].title()}"
                        })
                    
                    # Display tier data as a table
                    if tier_data:
                        df = pd.DataFrame(tier_data)
                        st.table(df)
                
                # Increment column index
                col_idx += 1
        
        # Display connections between components
        st.markdown("### Service Connections")
        
        # Create connection data
        connections = []
        for source, target in topology.edges:
            # Get source and target node info
            source_info = topology.nodes[source]
            target_info = topology.nodes[target]
            source_state = topology.node_states[source]
            target_state = topology.node_states[target]
            
            # Determine connection state (worst of the two connected nodes)
            connection_state = 'degraded' if ('degraded' in [source_state, target_state]) else \
                              'failed' if ('failed' in [source_state, target_state]) else 'healthy'
            
            # Set status emoji based on connection state
            status_emoji = "🟢" if connection_state == 'healthy' else "🟠" if connection_state == 'degraded' else "🔴"
            
            # Add connection to data
            connections.append({
                'Source': f"{AWS_ICONS.get(source_info['type'], '●')} {source_info['label']}",
                'Target': f"{AWS_ICONS.get(target_info['type'], '●')} {target_info['label']}",
                'Status': f"{status_emoji} {connection_state.title()}"
            })
        
        # Display connections as a table
        if connections:
            df = pd.DataFrame(connections)
            st.table(df)
        
        # Display latest action if available
        if topology.state_history:
            latest_event = topology.state_history[-1]
            event_type = latest_event['action'].title()
            description = latest_event['description']
            
            # Show event info with appropriate styling
            if event_type == 'Chaos':
                st.error(f"Latest Event: {event_type} - {description}")
            else:
                st.success(f"Latest Event: {event_type} - {description}")
            
            # Show affected or restored nodes
            affected_key = 'affected_nodes' if 'affected_nodes' in latest_event else 'restored_nodes'
            if affected_key in latest_event and latest_event[affected_key]:
                nodes = [f"{topology.nodes[node]['label']} → {state}" 
                        for node, state in latest_event[affected_key]]
                
                if affected_key == 'affected_nodes':
                    st.warning(f"Affected Services: {', '.join(nodes)}")
                else:
                    st.info(f"Restored Services: {', '.join(nodes)}")
        
        # Display dependencies that have issues
        problematic_deps = []
        for node_id, node_info in topology.nodes.items():
            node_state = topology.node_states[node_id]
            if node_state != 'healthy':
                # Check dependencies
                for dep_id in node_info['dependencies']:
                    dep_state = topology.node_states[dep_id]
                    dep_label = topology.nodes[dep_id]['label']
                    node_label = node_info['label']
                    
                    if dep_state != 'healthy':
                        problematic_deps.append({
                            'Connection': f"{dep_label} → {node_label}",
                            'Status': f"⚠️ Both services have issues"
                        })
                    else:
                        problematic_deps.append({
                            'Connection': f"{dep_label} → {node_label}",
                            'Status': f"🔄 Upstream service affected"
                        })
        
        if problematic_deps:
            st.markdown("#### Service Dependencies with Issues")
            st.dataframe(pd.DataFrame(problematic_deps), hide_index=True, use_container_width=True)
    
    # Show animation controls if requested
    if show_controls and topology.state_history:
        st.subheader("Infrastructure Event Timeline")
        st.write("View how infrastructure changed during simulation:")
        
        # Create a selectbox for historical states
        state_options = [f"{idx+1}. {state['timestamp'].strftime('%H:%M:%S')} - {state['action'].title()}: {state['description']}" 
                        for idx, state in enumerate(topology.state_history)]
        
        selected_state = st.selectbox("Select event to view", state_options)
        
        if selected_state:
            # Extract the index from the selection
            selected_idx = int(selected_state.split('.')[0]) - 1
            
            # Create a temporary copy of the topology and restore the selected state
            temp_topology = InfrastructureTopology()
            state = topology.state_history[selected_idx]
            temp_topology.node_states = state['node_states'].copy()
            
            # Display info about the selected state
            st.info(f"Event: {state['description']}")
            
            if 'affected_nodes' in state:
                affected = [f"{topology.nodes[node]['label']} → {state}" for node, state in state['affected_nodes']]
                if affected:
                    st.write("Affected services:", ", ".join(affected))
            
            if 'restored_nodes' in state:
                restored = [f"{topology.nodes[node]['label']} → {state}" for node, state in state['restored_nodes']]
                if restored:
                    st.write("Restored services:", ", ".join(restored))
            
            # Display the historical state
            display_infrastructure_topology(temp_topology, width, height, show_controls=False)
        
        # Add play button for animation
        if st.button("▶️ Play Animation"):
            st.write("Playing animation...")
            placeholder = st.empty()
            
            for i, state in enumerate(topology.state_history):
                with placeholder.container():
                    st.write(f"Step {i+1}: {state['action'].title()} - {state['description']}")
                    
                    # Create a temporary topology with this state
                    temp_topology = InfrastructureTopology()
                    temp_topology.node_states = state['node_states'].copy()
                    
                    # Display it
                    display_infrastructure_topology(temp_topology, width, height, show_controls=False)
                    
                # Delay for animation
                import time
                time.sleep(2)
    
    return topology

def main():
    """Main function for testing the topology visualization."""
    st.title("AWS Infrastructure Topology Visualization")
    
    # Create a topology
    topology = InfrastructureTopology()
    
    # Add chaos and remediation actions for testing
    topology.apply_chaos_action("EC2 instance termination")
    topology.apply_remediation_action("Restore EC2 instance")
    topology.apply_chaos_action("Network latency injection")
    topology.apply_remediation_action("Fix network latency")
    
    # Display the topology
    display_infrastructure_topology(topology)

if __name__ == "__main__":
    main()