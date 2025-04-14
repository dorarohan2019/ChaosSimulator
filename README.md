# AWS Chaos Engineering Dashboard

An advanced chaos engineering platform that proactively detects, simulates, and mitigates infrastructure security vulnerabilities using machine learning techniques in isolated AWS environments.

## Features

- Interactive visualization of system health metrics and security posture
- Chaos simulation for testing infrastructure resilience
- Anomaly detection using machine learning
- Automated remediation suggestions and actions
- Comprehensive impact analysis
- Infrastructure topology visualization
- Slack integration for approvals and notifications

## Prerequisites

Before deploying this application, you need:

1. **Python 3.11 or higher**
2. **Required Python packages**:
   - streamlit >= 1.44.1
   - plotly >= 5.18.0
   - pandas >= 2.0.0
   - numpy >= 1.22.0
   - scikit-learn >= 1.0.0
   - slack_sdk (optional, for Slack notifications)

3. **AWS Account** (for real infrastructure interaction)
   - AWS credentials with appropriate permissions
   - Or LocalStack for local development

4. **Streamlit Cloud account** (for Streamlit Cloud deployment)

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/aws-chaos-engineering.git
   cd aws-chaos-engineering
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```
   or
   ```bash
   streamlit run simplified_app.py
   ```

## Deploying to Streamlit Cloud

### 1. Prepare Your Repository

Ensure your repository includes:
- The main application file (app.py or simplified_app.py)
- requirements.txt file listing all dependencies
- .streamlit/config.toml with server configuration
- models/ directory for ML model storage

### 2. Sign in to Streamlit Cloud

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign in with your GitHub, GitLab, or Google account

### 3. Deploy Your App

1. Click "New app"
2. Select your repository, branch, and main Python file (app.py or simplified_app.py)
3. Configure advanced settings:
   - Set Python version to 3.11
   - Add any required secrets (see Environment Variables below)
4. Click "Deploy"

### 4. Configuration Settings

Your application should include a `.streamlit/config.toml` file with:

```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000

[theme]
primaryColor = "#4B0082"
backgroundColor = "#F5F7F9"
secondaryBackgroundColor = "#EAEAEA"
textColor = "#262730"
font = "sans serif"
```

## Environment Variables

Configure these secrets in Streamlit Cloud for full functionality:

| Variable | Description | Required |
|----------|-------------|----------|
| AWS_ACCESS_KEY_ID | AWS access key credential | For AWS integration |
| AWS_SECRET_ACCESS_KEY | AWS secret access key | For AWS integration |
| AWS_DEFAULT_REGION | Default AWS region | For AWS integration |
| SLACK_API_TOKEN | Slack API token for notifications | For Slack integration |
| SLACK_CHANNEL_NAME | Slack channel name for notifications | For Slack integration |

## Usage

1. **Dashboard**: View system metrics, anomaly detection, and security status
2. **Simulation Orchestration**: Run chaos experiments with automated or manual approval
3. **Impact Analysis**: Analyze simulation results and see remediation effectiveness
4. **Model Training**: Train and evaluate anomaly detection and remediation models

## Troubleshooting

- **Model Loading Errors**: Ensure the models/ directory exists and contains required model files
- **AWS Connection Issues**: Verify AWS credentials are correctly configured
- **Slack Integration Failures**: Check Slack API token and channel name

## License

[MIT License](LICENSE)

## Contact

For questions or support, please open an issue on GitHub or contact [your-email@example.com](mailto:your-email@example.com).