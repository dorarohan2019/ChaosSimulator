def safe_int_conversion(value):
    """
    Safely convert a value to integer, handling various formats including comma-separated strings.
    
    Args:
        value: Value to convert (int, float, str)
        
    Returns:
        int or None: Converted integer or None if conversion fails
    """
    if value is None:
        return None
    
    # If it's already an integer, return it
    if isinstance(value, int):
        return value
    
    # If it's a float, convert to int
    if isinstance(value, float):
        return int(value)
    
    # If it's a string, handle different formats
    if isinstance(value, str):
        # If it contains commas, it might be a list of numbers - take the first one
        if ',' in value:
            try:
                # Try to get the first number from the comma-separated list
                first_num = value.split(',')[0].strip()
                return int(float(first_num))
            except (ValueError, IndexError):
                return None
        
        # Try direct conversion
        try:
            return int(float(value))
        except ValueError:
            return None
            
    # For any other type, return None
    return None

def display_impact_analysis():
    """Display impact analysis of chaos and remediation actions on the system."""
    import streamlit as st
    
    st.header("Impact Analysis")
    
    # Ensure all required session state variables exist
    if 'simulation_metrics' not in st.session_state:
        st.session_state.simulation_metrics = {
            'timestamps': [], 'step': [], 'system_health': [], 'anomaly_score': [], 
            'phase': [], 'cpu_utilization': [], 'memory_usage': [], 'network_latency': [],
            'api_error_rate': [], 'service_availability': [], 'action_type': [], 'action_description': []
        }
    
    if 'chaos_actions' not in st.session_state:
        st.session_state.chaos_actions = []
        
    if 'remediation_actions' not in st.session_state:
        st.session_state.remediation_actions = []
    
    if len(st.session_state.chaos_actions) > 0:
        # Simulation has been run, so analyze the impact
        
        # Display unified step sequence graphs for anomaly score and system health
        st.subheader("Step Sequence Timeline Analysis")
        
        # Function to create unified timeline graphs
        try:
            if len(st.session_state.simulation_metrics['step']) > 0:
                import pandas as pd
                import numpy as np
                import plotly.graph_objects as go
                import plotly.subplots as sp
                
                # Convert metrics to dataframe for easier processing
                df = pd.DataFrame(st.session_state.simulation_metrics)
                
                # Create a simple plot to show progress over time
                st.line_chart(df[['system_health', 'anomaly_score']])
                st.info("For more detailed analysis, run a full simulation.")
        except Exception as e:
            st.error(f"Error creating timeline graphs: {str(e)}")
            st.info("Try running a simulation with more data points for better visualization.")
        
        # Critical vulnerabilities analysis section
        st.subheader("Critical Vulnerabilities & Remediation Analysis")
        
        try:
            # Basic display of chaos actions
            if len(st.session_state.chaos_actions) > 0:
                for i, action in enumerate(st.session_state.chaos_actions):
                    step = action.get('step', i+1)
                    description = action.get('description', 'Unknown action')
                    st.markdown(f"**Step {step}**: {description}")
                
                # Basic display of remediation actions
                if len(st.session_state.remediation_actions) > 0:
                    st.subheader("Remediation Actions")
                    for i, action in enumerate(st.session_state.remediation_actions):
                        step = action.get('step', i+1)
                        description = action.get('description', 'Unknown action')
                        st.markdown(f"**Step {step}**: {description}")
            else:
                st.info("Run a complete simulation to see critical system vulnerabilities and their remediation.")
        except Exception as e:
            st.error(f"Error analyzing system vulnerabilities: {str(e)}")
            st.info("Try running a new simulation to collect comprehensive data.")
                            
        # Add a section for most effective remediation actions
        st.subheader("Most Effective Remediation Actions")
        
        if len(st.session_state.remediation_actions) > 0:
            st.info("Analysis of remediation effectiveness would be shown here after a complete simulation.")
        else:
            st.info("Run a complete simulation to see most effective remediation actions.")
                
    else:
        # Simulation has not been run yet
        st.warning("Run a chaos simulation to see impact analysis.")