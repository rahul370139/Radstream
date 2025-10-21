# Mukul Rayana - Platform & Autoscaling Lead

## 🎯 Responsibilities

- **EKS Cluster**: Setup, configuration, and management
- **Container Orchestration**: Kubernetes deployments and services
- **Autoscaling**: HPA configuration and optimization
- **Performance Monitoring**: CloudWatch, metrics, and alerts

## 📁 My Components

### Inference (`inference/`)
- `Dockerfile.triton` - NVIDIA Triton Inference Server container
- `model_config.pbtxt` - Model configuration for 3 model types
- `health_check.py` - Container health monitoring
- `start_triton.sh` - Container startup script
- `deploy_manifest.yaml` - Kubernetes deployment with HPA

## 🚀 Quick Start

1. **Set up EKS cluster**
   ```bash
   eksctl create cluster --name radstream-cluster --region us-east-1
   ```

2. **Build and push model container**
   ```bash
   docker build -t radstream-triton:latest -f inference/Dockerfile.triton .
   docker tag radstream-triton:latest {account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest
   docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest
   ```

3. **Deploy to EKS**
   ```bash
   kubectl apply -f inference/deploy_manifest.yaml
   ```

4. **Verify deployment**
   ```bash
   kubectl get pods -n radstream
   kubectl get services -n radstream
   ```

## 📊 Performance Targets

- **Autoscaling response**: < 2 minutes
- **Pod startup time**: < 30 seconds
- **GPU utilization**: > 80% during inference
- **Availability**: > 99.9%

## 🔗 Dependencies

- **Depends on Rahul**: Model container requirements (Week 3)
- **Depends on Karthik**: Security policies and monitoring setup (Week 1-2)
- **Provides to Rahul**: EKS endpoint URL for Step Functions (Week 2-3)
- **Provides to Karthik**: CloudWatch metrics for dashboards (Week 4)

## 🛠️ Development Workflow

1. Create feature branch: `git checkout -b feature/mukul-description`
2. Make changes and test locally
3. Push and create PR to `develop`
4. Request review from team members
5. Merge after approval

## 📈 Optimization Areas

1. **Resource allocation** - CPU, memory, GPU
2. **Scaling policies** - HPA thresholds and behavior
3. **Container optimization** - Image size, startup time
4. **Network performance** - Load balancing, service mesh

## 🔧 Tools and Technologies

- **Kubernetes**: Container orchestration
- **Docker**: Containerization
- **NVIDIA Triton**: Model serving
- **EKS**: Managed Kubernetes
- **CloudWatch**: Monitoring and metrics
- **HPA**: Horizontal Pod Autoscaler

## 📞 Contact

- **Role**: Platform & Autoscaling Lead
- **Focus**: Infrastructure, scaling, performance
