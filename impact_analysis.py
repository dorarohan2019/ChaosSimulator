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
    
    # Check if simulation has been run
    if len(st.session_state.chaos_actions) > 0:
        # Simulation has been run, so analyze the impact
        
        # Display unified step sequence graphs for anomaly score and system health
        st.subheader("Step Sequence Timeline Analysis")
        
        # Function to create unified timeline graphs
        if len(st.session_state.simulation_metrics['timestamps']) > 0:
            try:
                # Import libraries needed for visualization
                import pandas as pd
                import numpy as np
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                # Create dataframe from metrics
                df = pd.DataFrame(st.session_state.simulation_metrics)
                
                # Make sure all expected columns exist to prevent errors
                required_columns = ['step', 'system_health', 'anomaly_score', 'phase', 
                                  'cpu_utilization', 'memory_usage', 'network_latency',
                                  'api_error_rate', 'service_availability']
                
                # Check if required columns exist, if not add them with default values
                for col in required_columns:
                    if col not in df.columns:
                        df[col] = [0.5] * len(df) if col != 'step' else list(range(1, len(df) + 1))
                
                # Sort by the global step number to ensure correct sequence
                sorted_indices = sorted(range(len(df)), key=lambda x: x)
                
                # Create a figure with subplots (2 rows, 1 column)
                fig = make_subplots(
                    rows=2, 
                    cols=1, 
                    subplot_titles=("Anomaly Score Fluctuation", "System Health Fluctuation"),
                    vertical_spacing=0.12,
                    shared_xaxes=True
                )
                
                # Create one unified trace for anomaly score (all points connected by step sequence)
                # Create two separate traces for coloring and visibility (Chaos and Remediation)
                chaos_mask = (df['phase'] == 'Chaos')
                remediation_mask = (df['phase'] == 'Remediation')
                
                # First, add the unified green line that connects all points
                # Just use sorted indices to ensure points are connected in sequence
                all_x = sorted_indices  # All sorted indices
                all_y = [df.iloc[idx]['anomaly_score'] for idx in all_x]
                
                # Add Single Green Line connecting all points in sequence (top subplot)
                fig.add_trace(
                    go.Scatter(
                        x=all_x, y=all_y,
                        mode='lines',
                        name='Step Sequence',
                        line=dict(color='#00FF00', width=2.5),
                        showlegend=True
                    ),
                    row=1, col=1
                )
                
                # Add Chaos Phase for Anomaly Score (top subplot)
                if any(chaos_mask):
                    chaos_x = [idx for idx in sorted_indices if chaos_mask[idx]]
                    chaos_y = [df.iloc[idx]['anomaly_score'] for idx in chaos_x]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=chaos_x, y=chaos_y,
                            mode='markers',  # Only markers, no lines
                            name='Chaos Phase',
                            marker=dict(color='#FF0000', size=10, symbol='circle',
                                    line=dict(color='#8B0000', width=2))
                        ),
                        row=1, col=1
                    )
                
                # Add Remediation Phase for Anomaly Score (top subplot)
                if any(remediation_mask):
                    remediation_x = [idx for idx in sorted_indices if remediation_mask[idx]]
                    remediation_y = [df.iloc[idx]['anomaly_score'] for idx in remediation_x]
                    
                    fig.add_trace(
                        go.Scatter(
                            x=remediation_x, y=remediation_y,
                            mode='markers',  # Only markers, no lines
                            name='Remediation Phase',
                            marker=dict(color='#FF0000', size=10, symbol='circle',
                                    line=dict(color='#ffcc00', width=2))
                        ),
                        row=1, col=1
                    )
                
                # Create one unified trace for system health (all points connected by step sequence)
                all_x_health = sorted_indices  # All sorted indices
                all_y_health = [df.iloc[idx]['system_health'] for idx in all_x_health]
                
                # Add Single Green Line connecting all points in sequence (bottom subplot)
                fig.add_trace(
                    go.Scatter(
                        x=all_x_health, y=all_y_health,
                        mode='lines',
                        name='Step Sequence',
                        line=dict(color='#00FF00', width=2.5),
                        showlegend=False  # Don't repeat in legend
                    ),
                    row=2, col=1
                )
                
                # Add Chaos Phase for System Health (bottom subplot)
                if any(chaos_mask):
                    chaos_x = [idx for idx in sorted_indices if chaos_mask[idx]]
                    chaos_y = [df.iloc[idx]['system_health'] for idx in chaos_x]
                    
                    # Add red dotted markers for chaos phase system health
                    fig.add_trace(
                        go.Scatter(
                            x=chaos_x,
                            y=chaos_y,
                            mode='markers',
                            name='Chaos Health Markers',
                            marker=dict(
                                color='#FF0000',
                                size=10,
                                symbol='circle',
                                line=dict(color='#8B0000', width=2)
                            ),
                            showlegend=False
                        ),
                        row=2, col=1
                    )
                
                # Add Remediation Phase for System Health (bottom subplot)
                if any(remediation_mask):
                    remediation_x = [idx for idx in sorted_indices if remediation_mask[idx]]
                    remediation_y = [df.iloc[idx]['system_health'] for idx in remediation_x]
                    
                    # Add red dotted markers for remediation phase system health
                    fig.add_trace(
                        go.Scatter(
                            x=remediation_x,
                            y=remediation_y,
                            mode='markers',
                            name='Remediation Health Markers',
                            marker=dict(
                                color='#FF0000',
                                size=10,
                                symbol='circle',
                                line=dict(color='#8B0000', width=2)
                            ),
                            showlegend=False
                        ),
                        row=2, col=1
                    )
                
                # Update layout
                fig.update_layout(
                    height=600,
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#ffffff"),
                    showlegend=True
                )
                
                # Add explicit ranges to prevent "Infinite extent" warnings
                # Set fixed ranges for axes to prevent infinite extent warnings
                fig.update_xaxes(
                    title_text="Step Number", 
                    showgrid=True, 
                    gridwidth=1, 
                    gridcolor='rgba(211,211,211,0.3)',
                    range=[0, max(all_x) + 1 if all_x else 10]  # Provide explicit range
                )
                
                # Find min/max values for y-axes with fallbacks to prevent infinite extent warnings
                y1_min = min(all_y) if all_y else 0
                y1_max = max(all_y) if all_y else 1
                y2_min = min(all_y_health) if all_y_health else 0
                y2_max = max(all_y_health) if all_y_health else 1
                
                # Add padding to ranges (10%)
                y1_padding = (y1_max - y1_min) * 0.1
                y2_padding = (y2_max - y2_min) * 0.1
                
                # Update axes with explicit ranges
                fig.update_yaxes(
                    title_text="Anomaly Score", 
                    row=1, col=1, 
                    showgrid=True, 
                    gridwidth=1, 
                    gridcolor='rgba(211,211,211,0.3)',
                    range=[max(0, y1_min - y1_padding), min(1, y1_max + y1_padding)]  # Constrain to 0-1 range with padding
                )
                
                fig.update_yaxes(
                    title_text="System Health", 
                    row=2, col=1, 
                    showgrid=True, 
                    gridwidth=1, 
                    gridcolor='rgba(211,211,211,0.3)',
                    range=[max(0, y2_min - y2_padding), min(1, y2_max + y2_padding)]  # Constrain to 0-1 range with padding
                )
                
                # Display the figure
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error creating charts: {str(e)}")
                st.info("Try running a complete simulation again to collect better data.")
            
        else:
            st.warning("No simulation data available. Please run a simulation to see the timeline analysis.")
        
        st.subheader("Critical Security Vulnerabilities & Remediation")
        
        try:
            # Extract data for analysis with proper error handling
            import pandas as pd
            
            if len(st.session_state.chaos_actions) > 0:
                chaos_df = pd.DataFrame(st.session_state.chaos_actions)
            else:
                chaos_df = pd.DataFrame(columns=['step', 'description', 'anomaly_score'])
                
            if len(st.session_state.remediation_actions) > 0:
                remediation_df = pd.DataFrame(st.session_state.remediation_actions)
            else:
                remediation_df = pd.DataFrame(columns=['step', 'description', 'improvement', 'anomaly_before', 'anomaly_after'])
            
            # Find the critical system weaknesses and their remediation
            if not chaos_df.empty and not remediation_df.empty:
                # Remove duplicate actions and aggregate their impact
                # Group by description and calculate average anomaly scores
                if 'description' in chaos_df.columns:
                    # Group by description, aggregate and get unique actions with their average values
                    agg_functions = {
                        'anomaly_score': 'mean',
                        'step': lambda x: ', '.join(str(i) for i in x)  # Keep all step numbers as a comma-separated string
                    }
                    
                    # Group by description to remove duplicates
                    unique_chaos_df = chaos_df.groupby('description').agg(agg_functions).reset_index()
                    
                    # Sort by severity (anomaly score)
                    unique_chaos_df = unique_chaos_df.sort_values('anomaly_score', ascending=False)
                    
                    # Get the top 3 most critical vulnerabilities
                    critical_vulnerabilities = unique_chaos_df.head(3)
                else:
                    # Fallback if description column doesn't exist
                    chaos_df = chaos_df.sort_values('anomaly_score', ascending=False)
                    critical_vulnerabilities = chaos_df.head(3)
                
                # Create columns for side-by-side display
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🔴 Security Vulnerabilities Revealed")
                    for idx, row in critical_vulnerabilities.iterrows():
                        severity = "Critical" if row['anomaly_score'] > 0.8 else "High" if row['anomaly_score'] > 0.6 else "Medium"
                        step_num = row['step'] if 'step' in row else "Unknown"
                        st.markdown(f"**Step {step_num}**: {row['description']}")
                        st.markdown(f"**Impact**: {severity} (Score: {row['anomaly_score']:.4f})")
                        # Calculate estimated system health from anomaly score (1 - anomaly_score is a good approximation)
                        est_system_health = max(0.1, 1.0 - row['anomaly_score'])
                        st.markdown(f"**Risk**: System health dropped to {est_system_health*100:.2f}%")
                        st.markdown("---")
                
                with col2:
                    st.markdown("### 🟢 Security Remediation Actions")
                    
                    # For each critical vulnerability, find corresponding remediation
                    for idx, chaos_row in critical_vulnerabilities.iterrows():
                        if 'step' in chaos_row:
                            # Find remediation for this chaos action (matching chaos_step if exists)
                            matching_remediations = []
                            for _, rem_row in remediation_df.iterrows():
                                # Handle both single step values and comma-separated step strings
                                if ('chaos_step' in rem_row and str(rem_row['chaos_step']) == str(chaos_row['step'])) or \
                                   ('step' in rem_row and (
                                        # For single step values, do direct comparison
                                        (not isinstance(rem_row['step'], str) and int(rem_row['step']) == int(chaos_row['step']) + 1) or
                                        # For comma-separated step values, check if any step matches
                                        (isinstance(rem_row['step'], str) and any(int(s.strip()) == int(chaos_row['step']) + 1 for s in rem_row['step'].split(',')))
                                   )):
                                    matching_remediations.append(rem_row)
                            
                            if matching_remediations:
                                rem_row = matching_remediations[0]  # Take the first match
                                step_num = rem_row['step'] if 'step' in rem_row else "Unknown"
                                
                                # Calculate improvement metrics
                                improvement = rem_row['improvement'] if 'improvement' in rem_row else 0
                                effectiveness = "Excellent" if improvement > 0.7 else "Good" if improvement > 0.5 else "Fair"
                                
                                st.markdown(f"**Step {step_num}**: {rem_row['description']}")
                                st.markdown(f"**Effectiveness**: {effectiveness} (Improvement: {improvement:.4f})")
                                
                                if 'anomaly_before' in rem_row and 'anomaly_after' in rem_row:
                                    reduction = (rem_row['anomaly_before'] - rem_row['anomaly_after']) / rem_row['anomaly_before'] * 100
                                    st.markdown(f"**Result**: Reduced anomaly by {reduction:.1f}%")
                                st.markdown("---")
                            else:
                                # Generic remediation information based on the type of vulnerability
                                st.markdown(f"**Recommended Security Fix:**")
                                
                                # Tailored remediation recommendations based on vulnerability type
                                # No "No specific remediation found" messages - always provide meaningful recommendation
                                if "SQL injection" in chaos_row['description']:
                                    st.markdown("**Input Validation & Parameterization**: Replace dynamic SQL with parameterized queries to prevent SQL injection attacks")
                                    st.markdown("**WAF Configuration**: Deploy web application firewall rules to detect and block SQL injection patterns")
                                elif "Authentication" in chaos_row['description']:
                                    st.markdown("**Authentication Improvement**: Implement multi-factor authentication with secure token verification")
                                    st.markdown("**Session Hardening**: Implement strict session timeouts and device fingerprinting")
                                elif "Encryption" in chaos_row['description'] or "TLS" in chaos_row['description']:
                                    st.markdown("**Encryption Upgrade**: Apply TLS 1.3 with strong cipher suites and certificate rotation")
                                    st.markdown("**Key Management**: Implement proper key rotation and secure key storage")
                                elif "XSS" in chaos_row['description'] or "Cross-site" in chaos_row['description']:
                                    st.markdown("**Content Security**: Implement Content-Security-Policy headers and context-aware output encoding")
                                    st.markdown("**Input Sanitization**: Apply strict input validation and HTML sanitization libraries")
                                elif "IAM" in chaos_row['description'] or "privilege" in chaos_row['description'].lower():
                                    st.markdown("**Privilege Reduction**: Implement least privilege principle with regular access reviews")
                                    st.markdown("**Permission Monitoring**: Deploy real-time privilege escalation detection systems")
                                elif "DDoS" in chaos_row['description']:
                                    st.markdown("**Rate Limiting**: Implement adaptive rate limiting with client reputation scoring")
                                    st.markdown("**Traffic Distribution**: Deploy anycast network with traffic scrubbing centers")
                                elif "API" in chaos_row['description']:
                                    st.markdown("**API Security Gateway**: Implement an API gateway with token validation and schema validation")
                                    st.markdown("**Rate Limiting**: Configure resource-specific rate limits with automated IP blocking")
                                elif "Malware" in chaos_row['description']:
                                    st.markdown("**Malware Protection**: Deploy advanced endpoint protection with behavioral analysis")
                                    st.markdown("**Sandbox Processing**: Implement attachment/download sandboxing before user access")
                                elif "exfiltration" in chaos_row['description'].lower():
                                    st.markdown("**Data Loss Prevention**: Implement outbound traffic inspection and data classification")
                                    st.markdown("**Encryption**: Deploy transparent data encryption for sensitive information")
                                else:
                                    st.markdown("**Comprehensive Security Program**: Apply defense-in-depth strategy with layered controls")
                                    st.markdown("**Security Monitoring**: Implement real-time security event monitoring and alerting")
                                
                                st.markdown("---")
                        else:
                            # This shouldn't happen with proper data
                            pass
            else:
                st.info("Run a complete simulation to see critical system vulnerabilities and their remediation.")
                
        except Exception as e:
            st.error(f"Error analyzing system vulnerabilities: {str(e)}")
            st.info("Try running a new simulation to collect comprehensive data.")
                        
        # Add a section for most effective remediation actions
        st.subheader("Most Effective Remediation Actions")
        
        if len(st.session_state.remediation_actions) > 0:
            # Create a dataframe from remediation actions
            import pandas as pd
            remediation_df = pd.DataFrame(st.session_state.remediation_actions)
            
            # Sort by effectiveness (improvement) and show top 3 or all if less than 3
            if 'improvement' in remediation_df.columns and 'description' in remediation_df.columns:
                # First, group by description to get unique remediation actions
                agg_functions = {
                    'improvement': 'mean',
                    'step': lambda x: ', '.join(str(i) for i in x),
                    'success': 'mean'  # Take average of success (0/1) to determine overall success rate
                }
                
                # Group by description to consolidate duplicate actions
                unique_remediation_df = remediation_df.groupby('description').agg(agg_functions).reset_index()
                
                # Get the top 3 most effective remediation actions
                top_remediations = unique_remediation_df.sort_values(by='improvement', ascending=False).head(3)
                
                if len(top_remediations) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### Top Security Fixes")
                        
                        for i, (idx, row) in enumerate(top_remediations.iterrows()):
                            # Calculate effectiveness and get other metrics
                            improvement = row['improvement'] if 'improvement' in row else 0
                            step_num = row['step'] if 'step' in row else "Unknown"
                            success = row.get('success', True)  # Default to True if not present
                            
                            # Create a styled box with a colored border based on effectiveness
                            effectiveness_color = "#4CAF50" if improvement > 0.5 else "#FFC107" if improvement > 0.3 else "#FF5722"
                            
                            success_icon = "✅" if success else "⚠️"
                            success_text = "Successful" if success else "Partial success"
                            
                            st.markdown(f"""
                            <div style="border-left: 5px solid {effectiveness_color}; padding-left: 10px; margin-bottom: 15px;">
                                <h4>#{i+1}: Step {step_num} {success_icon}</h4>
                                <p><strong>Action:</strong> {row['description']}</p>
                                <p><strong>Effectiveness:</strong> {improvement:.4f} improvement ({success_text})</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with col2:
                        # Create a bar chart of top remediation effectiveness
                        import plotly.graph_objects as go
                        
                        # Create a simple horizontal bar chart
                        # For aggregated step values (comma-separated), just show as is without trying to convert to int
                        labels = [f"Step {row['step']}: {row['description'][:30]}..." for _, row in top_remediations.iterrows()]
                        values = [row['improvement'] for _, row in top_remediations.iterrows()]
                        
                        # Colors based on effectiveness
                        colors = ["#4CAF50" if v > 0.5 else "#FFC107" if v > 0.3 else "#FF5722" for v in values]
                        
                        fig = go.Figure(go.Bar(
                            x=values,
                            y=labels,
                            orientation='h',
                            marker=dict(color=colors),
                            text=[f"{v:.4f}" for v in values],
                            textposition='auto'
                        ))
                        
                        fig.update_layout(
                            title="Remediation Effectiveness",
                            xaxis_title="Improvement Score",
                            yaxis_title="Remediation Action",
                            height=300,
                            margin=dict(l=20, r=20, t=40, b=20),
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No effectiveness data available for remediation actions.")
            else:
                st.info("Remediation improvement data not available.")
        else:
            st.info("Run a complete simulation to see most effective remediation actions.")
            
    else:
        # Simulation has not been run yet
        st.warning("Run a chaos simulation to see impact analysis.")