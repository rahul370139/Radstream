# Mukul Rayana - Platform & Autoscaling Lead

## 🎯 **Responsibilities**

- **EKS Cluster**: Setup, configuration, and management
- **Container Orchestration**: Kubernetes deployments and services
- **Autoscaling**: HPA configuration and optimization
- **Performance Monitoring**: CloudWatch, metrics, and alerts

## 📁 **My Components**

### Inference (`inference/`)
- `Dockerfile.triton` - NVIDIA Triton Inference Server container
- `model_config.pbtxt` - Model configuration for 3 model types
- `health_check.py` - Container health monitoring
- `start_triton.sh` - Container startup script
- `deploy_manifest.yaml` - Kubernetes deployment with HPA

---

## 🚀 **STEP-BY-STEP SETUP GUIDE**

### **Week 1: Prerequisites & Preparation**

#### **Day 1: Install Tools**

**Step 1: Install eksctl (15 minutes)**

**macOS:**
```bash
brew install eksctl
```

**Linux:**
```bash
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version  # Verify installation
```

**Windows:**
```powershell
choco install eksctl
```

**Step 2: Install kubectl (15 minutes)**

**macOS:**
```bash
brew install kubectl
```

**Linux:**
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client  # Verify installation
```

**Windows:**
```powershell
choco install kubernetes-cli
```

**Step 3: Install Docker (30 minutes)**
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Verify:
```bash
docker --version
docker ps  # Should run without errors
```

**Step 4: Configure AWS CLI (10 minutes)**
```bash
aws configure
```
Enter:
- AWS Access Key ID: [your access key]
- AWS Secret Access Key: [your secret key]
- Default region name: `us-east-1`
- Default output format: `json`

**Test:**
```bash
aws sts get-caller-identity
```

---

### **Week 1-2: EKS Cluster Setup (After Karthik Completes IAM Roles)**

#### **Day 1: Wait for Infrastructure**

**Step 5: Verify Prerequisites (30 minutes)**
1. **Wait for Karthik's confirmation** that infrastructure is ready
2. Verify IAM role exists:
   ```bash
   aws iam get-role --role-name RadStreamEKSNodeGroupRole
   ```
3. Verify role has necessary permissions:
   - ECR pull access
   - CloudWatch logs access
   - S3 read access

**Checkpoint**: Wait for Karthik's confirmation that IAM roles are ready.

---

#### **Day 2: Create EKS Cluster**

**Step 6: Create EKS Cluster (30 minutes)**
```bash
eksctl create cluster \
  --name radstream-cluster \
  --region us-east-1 \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --with-oidc \
  --managed \
  --ssh-access \
  --ssh-public-key ~/.ssh/id_rsa.pub
```

**What this does**:
- Creates EKS cluster in us-east-1
- Creates node group with 2 t3.medium instances
- Sets up autoscaling (1-4 nodes)
- Enables OIDC provider for IAM integration
- Uses managed node groups

**Expected output**:
```
[ℹ]  eksctl version 0.x.x
[ℹ]  using region us-east-1
...
[✓]  EKS cluster "radstream-cluster" in "us-east-1" region is ready
```

**Time**: 15-20 minutes for cluster creation

**Step 7: Configure kubectl (10 minutes)**
```bash
aws eks update-kubeconfig --name radstream-cluster --region us-east-1
```

**Verify connection:**
```bash
kubectl get nodes
```

**Expected output:**
```
NAME                          STATUS   ROLES    AGE   VERSION
ip-xxx-xxx-xxx-xxx.ec2...    Ready    <none>   5m    v1.28.x
ip-xxx-xxx-xxx-xxx.ec2...    Ready    <none>   5m    v1.28.x
```

**Step 8: Verify Cluster (15 minutes)**
1. Go to EKS Console → Clusters → `radstream-cluster`
2. Verify:
   - Cluster status: Active
   - Kubernetes version: 1.28+
   - Node group: 2 nodes running
   - IAM role: RadStreamEKSNodeGroupRole attached

---

#### **Day 3: ECR Repository Setup**

**Step 9: Create ECR Repository (30 minutes)**
```bash
aws ecr create-repository \
  --repository-name radstream-triton \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

**Manual Configuration**:
1. Go to ECR Console → Repositories → `radstream-triton`
2. Configure lifecycle policy:
   - Go to "Lifecycle policy" tab
   - Create policy:
   ```json
   {
     "rules": [
       {
         "rulePriority": 1,
         "description": "Keep last 10 images",
         "selection": {
           "tagStatus": "any",
           "countType": "imageCountMoreThan",
           "countNumber": 10
         },
         "action": {
           "type": "expire"
         }
       }
     ]
   }
   ```
3. Enable image scanning: Already enabled

**Note the ECR URI**: `{account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton`

---

#### **Day 3-4: Container Build & Push**

**Step 10: Get ECR Login (5 minutes)**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {account-id}.dkr.ecr.us-east-1.amazonaws.com
```

Replace `{account-id}` with your AWS account ID.

**Step 11: Build Container (30-60 minutes)**
```bash
cd RadStream
docker build -t radstream-triton:latest -f mukul/inference/Dockerfile.triton .
```

**What this does**:
- Builds Docker image with Triton Inference Server
- Includes model configuration
- Sets up required dependencies

**Monitor build progress** - This may take 30-60 minutes depending on:
- Model size
- Network speed
- Docker image layers

**Step 12: Tag Image (1 minute)**
```bash
docker tag radstream-triton:latest {account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest
```

**Step 13: Push to ECR (10-30 minutes)**
```bash
docker push {account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest
```

**Monitor push progress** - Image size affects upload time.

**Verify in ECR Console**:
1. Go to ECR Console → Repositories → `radstream-triton`
2. Verify image exists
3. Check image scan results (if enabled)

---

### **Week 2-3: Kubernetes Deployment**

#### **Day 1: Update Deployment Manifest**

**Step 14: Update deploy_manifest.yaml (15 minutes)**
1. Open `mukul/inference/deploy_manifest.yaml`
2. Replace placeholders:
   - `{account-id}` → Your AWS account ID
   - `{ECR-URI}` → `{account-id}.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest`
   - `{region}` → `us-east-1`

**Example:**
```yaml
image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/radstream-triton:latest
```

**Step 15: Create Namespace (5 minutes)**
```bash
kubectl create namespace radstream
```

**Verify:**
```bash
kubectl get namespaces
```

---

#### **Day 2: Deploy to EKS**

**Step 16: Deploy Application (15 minutes)**
```bash
kubectl apply -f mukul/inference/deploy_manifest.yaml
```

**Verify deployment:**
```bash
kubectl get pods -n radstream
```

**Expected output:**
```
NAME                                   READY   STATUS    RESTARTS   AGE
triton-inference-server-xxxxxxxxxx-xxx  1/1     Running   0          2m
```

**Step 17: Verify Services (10 minutes)**
```bash
kubectl get services -n radstream
```

**Expected output:**
```
NAME                       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                         AGE
triton-inference-service   ClusterIP   10.100.xxx.xxx   <none>        8000/TCP,8001/TCP,8002/TCP      2m
```

**Step 18: Check Pod Logs (15 minutes)**
```bash
kubectl logs -f <pod-name> -n radstream
```

**Look for:**
- Triton server started successfully
- Models loaded
- HTTP server listening on port 8000

**Common issues**:
- Image pull errors → Check ECR permissions
- Container crashes → Check logs for errors
- Resource limits → Check pod resource requests

---

#### **Day 3: HPA Configuration**

**Step 19: Verify HPA (15 minutes)**
```bash
kubectl get hpa -n radstream
```

**Expected output:**
```
NAME           REFERENCE                         TARGETS         MINPODS   MAXPODS   REPLICAS   AGE
triton-hpa     Deployment/triton-inference-server  <unknown>/70%   1         5         1          5m
```

**Check HPA details:**
```bash
kubectl describe hpa triton-hpa -n radstream
```

**Step 20: Test Autoscaling (1 hour)**
1. **Generate Load**:
   ```bash
   kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh
   ```
   Inside the pod:
   ```bash
   while true; do wget -q -O- http://triton-inference-service:8000/v2/health/ready; done
   ```

2. **Monitor Scaling**:
   ```bash
   kubectl get hpa -n radstream --watch
   ```
   
   Watch for:
   - CPU utilization increasing
   - Replicas scaling up
   - Target reached

3. **Verify Pods Scaling**:
   ```bash
   kubectl get pods -n radstream --watch
   ```
   
   Should see new pods being created as load increases.

4. **Stop Load Generator**:
   - Exit the load-generator pod
   - Watch pods scale down after load decreases

**Expected behavior**:
- Scale up when CPU > 70%
- Scale down when CPU < 70%
- Scale up takes 2-3 minutes
- Scale down takes 5-10 minutes

---

### **Week 3-4: Monitoring & Integration**

#### **Day 1: CloudWatch Container Insights**

**Step 21: Enable Container Insights (30 minutes)**
1. Go to CloudWatch Console → Container Insights
2. Select EKS cluster: `radstream-cluster`
3. Click "Enable Container Insights"
4. Wait for metrics to appear (5-10 minutes)

**Verify metrics**:
1. Go to CloudWatch → Metrics → Container Insights
2. Check metrics:
   - CPU utilization
   - Memory utilization
   - Network I/O
   - Pod status

**Step 22: Create Custom Metrics Dashboard (1 hour)**
1. Go to CloudWatch → Dashboards → Create dashboard
2. Name: `radstream-eks-dashboard`
3. Add widgets:
   - Pod CPU utilization
   - Pod memory utilization
   - Pod count
   - Request latency
   - Error rate
4. Save dashboard

---

#### **Day 2: Provide EKS Endpoint**

**Step 23: Get Service Endpoint (15 minutes)**
```bash
kubectl get svc triton-inference-service -n radstream
```

**For internal access (ClusterIP)**:
- Endpoint: `triton-inference-service.radstream.svc.cluster.local:8000`
- Use this for Step Functions integration

**For external access (if LoadBalancer)**:
```bash
kubectl get svc triton-inference-service -n radstream -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**Step 24: Test Endpoint (15 minutes)**
```bash
# From within cluster
kubectl run -i --tty test-pod --rm --image=curlimages/curl --restart=Never -- /bin/sh
```

Inside the pod:
```bash
curl http://triton-inference-service:8000/v2/health/ready
curl http://triton-inference-service:8000/v2/health/live
```

**Step 25: Share Endpoint with Rahul (5 minutes)**
1. Provide endpoint URL to Rahul
2. Provide test instructions
3. Coordinate integration testing

---

### **Week 4-5: Performance Optimization**

#### **Day 1-2: Load Testing**

**Step 26: Coordinate Load Tests (2-3 hours)**
1. **Burst Test** (Coordinate with Rahul):
   - 50 images in 1 minute
   - Monitor autoscaling behavior
   - Measure convergence time

2. **Sustained Test**:
   - 10 images/min for 30 minutes
   - Monitor pod count
   - Measure resource utilization

3. **Monitor Metrics**:
   ```bash
   # Watch pod count
   kubectl get pods -n radstream --watch
   
   # Watch HPA
   kubectl get hpa -n radstream --watch
   
   # Check pod logs
   kubectl logs -f <pod-name> -n radstream
   ```

**Step 27: Measure Performance (1 hour)**
1. **Autoscaling Metrics**:
   - Time to scale up: Target < 2 minutes
   - Time to scale down: Target < 5 minutes
   - Pod startup time: Target < 30 seconds

2. **Resource Utilization**:
   - CPU utilization: Target > 80% during inference
   - Memory utilization: Target < 80%
   - GPU utilization: If using GPU, target > 80%

3. **Availability**:
   - Pod restarts: Should be 0
   - Error rate: Should be < 1%

---

#### **Day 3-4: Optimization**

**Step 28: Tune HPA Parameters (2 hours)**
1. Edit HPA configuration:
   ```bash
   kubectl edit hpa triton-hpa -n radstream
   ```
2. Adjust parameters:
   - `targetCPUUtilizationPercentage`: Try 60, 70, 80
   - `minReplicas`: Start with 1, increase if needed
   - `maxReplicas`: Based on expected load
3. Test different configurations
4. Measure impact

**Step 29: Optimize Resource Requests/Limits (2 hours)**
1. Edit deployment:
   ```bash
   kubectl edit deployment triton-inference-server -n radstream
   ```
2. Adjust:
   - CPU requests: Based on actual usage
   - Memory requests: Based on actual usage
   - Limits: 1.5x requests
3. Test and measure

**Step 30: Document Optimization Results (1 hour)**
1. Document baseline metrics
2. Document optimized metrics
3. Calculate improvements
4. Prepare for final report

---

### **Week 7-8: Demo Preparation**

**Step 31: Demo Environment Setup (2-3 hours)**
1. Prepare test data
2. Create demo scripts
3. Document scaling behavior
4. Prepare performance metrics

**Step 32: Performance Documentation (2-3 hours)**
1. Document autoscaling behavior
2. Create performance reports
3. Prepare presentation materials

---

## 📊 **Performance Targets**

- **Autoscaling response**: < 2 minutes
- **Pod startup time**: < 30 seconds
- **GPU utilization**: > 80% during inference
- **Availability**: > 99.9%

## 🔗 **Dependencies**

- **Depends on Karthik**: IAM roles (Week 1) - BLOCKS YOU
- **Depends on Rahul**: Model container requirements (Week 3) - Optional
- **Provides to Rahul**: EKS endpoint URL (Week 2-3)
- **Provides to Karthik**: CloudWatch metrics for dashboards (Week 4)

## 🛠️ **Development Workflow**

1. Create feature branch: `git checkout -b feature/mukul-description`
2. Make changes and test locally
3. Push and create PR to `develop`
4. Request review from team members
5. Merge after approval

## 📈 **Optimization Areas**

1. **Resource allocation** - CPU, memory, GPU
2. **Scaling policies** - HPA thresholds and behavior
3. **Container optimization** - Image size, startup time
4. **Network performance** - Load balancing, service mesh

## 🔧 **Tools and Technologies**

- **Kubernetes**: Container orchestration
- **Docker**: Containerization
- **NVIDIA Triton**: Model serving
- **EKS**: Managed Kubernetes
- **CloudWatch**: Monitoring and metrics
- **HPA**: Horizontal Pod Autoscaler

## 📞 **Contact**

- **Role**: Platform & Autoscaling Lead
- **Focus**: Infrastructure, scaling, performance

---

**Remember**: Wait for Karthik's IAM roles before creating EKS cluster. Once roles are ready, you can proceed with cluster creation! 🚀