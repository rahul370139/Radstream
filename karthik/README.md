# Karthik Ramanathan - Security, Edge & Evaluation Lead

## 🎯 Responsibilities

- **Security**: IAM, WAF, GuardDuty, CloudTrail
- **Monitoring**: QuickSight dashboards, CloudWatch
- **Evaluation**: A/B testing, performance analysis
- **Compliance**: HIPAA, audit trails, data governance

## 📁 My Components

### Security (`security/`)
- `iam_roles.json` - IAM roles and policies with least-privilege access
- Security configurations for HIPAA compliance
- Network security and monitoring setup

## 🚀 Quick Start

1. **Set up IAM roles and policies**
   ```bash
   # Create IAM roles using the JSON definitions
   aws iam create-role --role-name RadStreamLambdaExecutionRole --assume-role-policy-document file://security/iam_roles.json
   ```

2. **Enable security services**
   ```bash
   # Enable CloudTrail
   aws cloudtrail create-trail --name radstream-trail --s3-bucket-name radstream-telemetry-{account-id}
   
   # Enable GuardDuty
   aws guardduty create-detector --enable
   
   # Set up WAF
   aws wafv2 create-web-acl --name radstream-waf --scope REGIONAL
   ```

3. **Create QuickSight dashboards**
   - Connect to Athena data source
   - Create performance, security, and cost dashboards
   - Set up real-time monitoring

## 📊 Security Targets

- **Attack detection**: 100% of simulated attacks blocked
- **Compliance**: 100% HIPAA compliance
- **Audit trail**: Complete API call logging
- **Response time**: < 5 minutes to detect threats

## 🔗 Dependencies

- **Depends on Rahul**: Telemetry data for dashboards (Week 4-5)
- **Depends on Mukul**: EKS metrics for monitoring (Week 4)
- **Provides to Rahul & Mukul**: IAM policies (Week 1-2)
- **Provides to All**: Security evaluation and final report (Week 7-8)

## 🛠️ Development Workflow

1. Create feature branch: `git checkout -b feature/karthik-description`
2. Make changes and test locally
3. Push and create PR to `develop`
4. Request review from team members
5. Merge after approval

## 📈 A/B Testing Scenarios

1. **WAF enabled vs disabled**
2. **GuardDuty sensitivity levels**
3. **Encryption methods comparison**
4. **Access control policies**

## 🔧 Tools and Technologies

- **AWS IAM**: Identity and access management
- **AWS WAF**: Web application firewall
- **AWS GuardDuty**: Threat detection
- **AWS CloudTrail**: API auditing
- **Amazon QuickSight**: Data visualization
- **AWS Security Hub**: Security posture

## 📊 Evaluation Metrics

- **Security posture**: Attack blocking rate, threat detection
- **Performance impact**: Latency with security enabled
- **Cost analysis**: Security service costs vs benefits
- **Compliance score**: HIPAA compliance percentage

## 📞 Contact

- **Role**: Security, Edge & Evaluation Lead
- **Focus**: Security, monitoring, evaluation, compliance
