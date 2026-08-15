# Smart Campus Token Management - Deployment Design

## Deployment Architecture Overview

The Smart Campus Token Management System is designed for multi-environment deployment with consistent architecture across development, staging, and production environments.

---

## Environment Progression

```
Development (Local)
    ↓ [Code Review + Testing]
Staging (Pre-Production)
    ↓ [Integration Testing + Performance Testing]
Production (Campus Deployment)
    ↓ [Blue-Green Deployment]
Rollback Ready
```

---

## Development Environment

### Local Development Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: campus_tokens_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cache Layer
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # S3-Compatible Storage (MinIO)
  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data_dev:/data
    command: server /data --console-address ":9001"

  # Backend API
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DEBUG: "True"
      DATABASE_URL: postgresql://dev_user:dev_password@postgres:5432/campus_tokens_dev
      REDIS_URL: redis://redis:6379/0
      AWS_S3_BUCKET: campus-photos-dev
      AWS_S3_ENDPOINT: http://minio:9000
      FACE_RECOGNITION_ENABLED: "False"  # Disabled by default in dev
      SECRET_KEY: dev-secret-key-12345
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_started
    volumes:
      - .:/app
    command: python manage.py runserver 0.0.0.0:8000

  # Frontend Development Server
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost:8000/api
    volumes:
      - ./frontend:/app
    command: npm start

volumes:
  postgres_data_dev:
  minio_data_dev:
```

### Development Initialization

```bash
# Setup
docker-compose up -d

# Initialize database
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Run tests
docker-compose exec backend python manage.py test

# Stop
docker-compose down
```

### Development Environment Variables

```bash
# .env.dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
SECRET_KEY=dev-secret-key-do-not-use-in-production

# Database
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/campus_tokens_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# S3 / MinIO
AWS_S3_BUCKET=campus-photos-dev
AWS_S3_REGION=us-east-1
AWS_S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin

# Face Recognition (Optional)
FACE_RECOGNITION_ENABLED=False

# OAuth2 (Google)
GOOGLE_OAUTH_CLIENT_ID=dev-client-id
GOOGLE_OAUTH_CLIENT_SECRET=dev-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/auth/google/callback

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## Staging Environment

### Staging Deployment (AWS ECS + RDS + ALB)

```yaml
# Kubernetes manifest: k8s/staging/deployment.yaml

apiVersion: v1
kind: Namespace
metadata:
  name: campus-tokens-staging

---

apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: campus-tokens-staging
data:
  DEBUG: "False"
  DATABASE_HOST: postgres-staging.c123456789.us-east-1.rds.amazonaws.com
  REDIS_HOST: campus-redis-staging.abc123.ng.0001.use1.cache.amazonaws.com
  AWS_S3_BUCKET: campus-photos-staging
  AWS_S3_REGION: us-east-1
  FACE_RECOGNITION_ENABLED: "True"
  FACE_RECOGNITION_BACKEND: face_recognition_library
  LOG_LEVEL: INFO

---

apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: campus-tokens-staging
type: Opaque
stringData:
  DATABASE_PASSWORD: <stored-in-secrets-manager>
  REDIS_PASSWORD: <stored-in-secrets-manager>
  SECRET_KEY: <stored-in-secrets-manager>
  AWS_ACCESS_KEY_ID: <stored-in-secrets-manager>
  AWS_SECRET_ACCESS_KEY: <stored-in-secrets-manager>
  GOOGLE_OAUTH_CLIENT_ID: <stored-in-secrets-manager>
  GOOGLE_OAUTH_CLIENT_SECRET: <stored-in-secrets-manager>

---

apiVersion: apps/v1
kind: Deployment
metadata:
  name: campus-tokens-backend
  namespace: campus-tokens-staging
spec:
  replicas: 2  # 2 replicas in staging
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: campus-tokens-backend
  template:
    metadata:
      labels:
        app: campus-tokens-backend
    spec:
      containers:
      - name: backend
        image: 123456789.dkr.ecr.us-east-1.amazonaws.com/campus-tokens:staging-1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DEBUG
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DEBUG
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DATABASE_PASSWORD
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

---

apiVersion: v1
kind: Service
metadata:
  name: campus-tokens-backend-service
  namespace: campus-tokens-staging
spec:
  type: LoadBalancer
  selector:
    app: campus-tokens-backend
  ports:
  - protocol: TCP
    port: 443
    targetPort: 8000

---

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: campus-tokens-backend-hpa
  namespace: campus-tokens-staging
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: campus-tokens-backend
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Staging Infrastructure

```yaml
# AWS CloudFormation template
Resources:
  # RDS PostgreSQL Cluster (staging)
  PostgresDBCluster:
    Type: AWS::RDS::DBCluster
    Properties:
      Engine: aurora-postgresql
      EngineVersion: 14.6
      DatabaseName: campus_tokens_staging
      MasterUsername: staging_user
      MasterUserPassword: !Sub '{{resolve:secretsmanager:rds-password:SecretString:password}}'
      StorageEncrypted: true
      KmsKeyId: !Sub 'arn:aws:kms:${AWS::Region}:${AWS::AccountId}:key/xxxxxxxx'
      BackupRetentionPeriod: 7
      EnableCloudwatchLogsExports:
        - postgresql
      DBSubnetGroupName: !Ref DBSubnetGroup
      VpcSecurityGroupIds:
        - !Ref DBSecurityGroup

  # Redis ElastiCache Cluster (staging)
  RedisCluster:
    Type: AWS::ElastiCache::ReplicationGroup
    Properties:
      Engine: redis
      CacheNodeType: cache.t3.micro
      NumCacheClusters: 2
      AutomaticFailover: enabled
      CacheSubnetGroupName: !Ref CacheSubnetGroup
      SecurityGroupIds:
        - !Ref CacheSecurityGroup
      AtRestEncryptionEnabled: true
      TransitEncryptionEnabled: true
      KmsKeyId: !Sub 'arn:aws:kms:${AWS::Region}:${AWS::AccountId}:key/xxxxxxxx'

  # S3 Bucket for photos (staging)
  PhotosBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: campus-photos-staging
      VersioningConfiguration:
        Status: Enabled
      ServerSideEncryptionConfiguration:
        - ServerSideEncryptionByDefault:
            SSEAlgorithm: aws:kms
            KMSMasterKeyID: !Sub 'arn:aws:kms:${AWS::Region}:${AWS::AccountId}:key/xxxxxxxx'
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: DeleteOldPhotos
            Status: Enabled
            ExpirationInDays: 90
            NoncurrentVersionExpirationInDays: 30

  # ALB (Application Load Balancer)
  ApplicationLoadBalancer:
    Type: AWS::ElasticLoadBalancingV2::LoadBalancer
    Properties:
      Scheme: internet-facing
      Type: application
      Subnets:
        - !Ref PublicSubnet1
        - !Ref PublicSubnet2
      SecurityGroups:
        - !Ref ALBSecurityGroup
      Tags:
        - Key: Name
          Value: campus-tokens-staging-alb
```

### Staging Testing Pipeline

```yaml
# .github/workflows/staging-deploy.yml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run unit tests
        run: python manage.py test
      
      - name: Run integration tests
        run: python manage.py test --tag=integration
      
      - name: Security scanning (Bandit)
        run: bandit -r . -ll
      
      - name: Dependency scanning (Safety)
        run: safety check --json

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/campus-tokens:staging-${{ github.sha }} .
      
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
          docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/campus-tokens:staging-${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster campus-tokens-staging \
            --service campus-tokens-backend \
            --force-new-deployment \
            --region us-east-1
      
      - name: Run smoke tests
        run: |
          curl -f https://staging-api.campus.edu/health || exit 1
          python test_smoke.py
```

---

## Production Environment

### Production Deployment (Multi-Region, High Availability)

```yaml
# Production infrastructure architecture

┌─────────────────────────────────────────────────────────────────┐
│                         Global Load Balancer                    │
│                      (CloudFlare / AWS Route53)                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────────┐        ┌───────────────────┐
│  US-EAST Region   │        │  EU-WEST Region   │
├───────────────────┤        ├───────────────────┤
│ Primary ALB       │        │ Secondary ALB     │
│ - EKS Cluster     │        │ - EKS Cluster     │
│   (5+ replicas)   │        │   (3+ replicas)   │
│ - Auto-scaling    │        │ - Auto-scaling    │
│ - Canary deploy   │        │ - Blue-green      │
└─────────┬─────────┘        └─────────┬─────────┘
          │                            │
          ├────────────────────────────┤
          │    Cross-region replication
          │
          ▼
┌─────────────────────────────────────────┐
│   Primary RDS Aurora PostgreSQL         │
│   - Multi-AZ failover                   │
│   - Read replicas in multiple regions   │
│   - Automated backups (35-day retention)│
│   - Encryption at rest (KMS)            │
│   - Encryption in transit (TLS 1.3)     │
│   - PITR enabled                        │
│   - Performance Insights enabled        │
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│   ElastiCache Redis Cluster             │
│   - Multi-AZ deployment                 │
│   - Automatic failover                  │
│   - Encryption at rest + in transit     │
│   - Automatic backups                   │
│   - Auto-scaling enabled                │
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│   S3 with Cross-Region Replication      │
│   - Versioning enabled                  │
│   - MFA delete protection               │
│   - Encryption (customer-managed KMS)   │
│   - Access logging + CloudTrail         │
│   - Automatic lifecycle policies        │
│   - Same-region failover bucket         │
└─────────────────────────────────────────┘
```

### Production Environment Variables (Secrets Manager)

```bash
# AWS Secrets Manager: /prod/campus-tokens/config

{
  "database_url": "postgresql://prod_user:XXXXX@aurora-cluster.us-east-1.rds.amazonaws.com/campus_tokens",
  "redis_url": "rediss://prod_user:XXXXX@prod-redis.abc123.ng.0001.use1.cache.amazonaws.com:6379/0",
  "aws_s3_bucket": "campus-photos-prod",
  "aws_kms_master_key_id": "arn:aws:kms:us-east-1:ACCOUNT_ID:key/12345678-1234-1234-1234-123456789012",
  "secret_key": "XXXXX-long-random-secret-XXXXX",
  "debug": "False",
  "allowed_hosts": "api.campus.edu,api.staging.campus.edu",
  "google_oauth_client_id": "XXXXX.apps.googleusercontent.com",
  "google_oauth_client_secret": "XXXXX",
  "face_recognition_enabled": "True",
  "face_recognition_backend": "face_recognition_library",
  "email_backend": "django_anymail.backends.sendgrid.EmailBackend",
  "sendgrid_api_key": "XXXXX"
}
```

### Production Deployment Process

```bash
# 1. Prepare release
git tag -a v1.0.0 -m "Production release 1.0.0"
git push origin v1.0.0

# 2. Build image
docker build -t campus-tokens:1.0.0 .
docker tag campus-tokens:1.0.0 123456789.dkr.ecr.us-east-1.amazonaws.com/campus-tokens:prod-1.0.0
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/campus-tokens:prod-1.0.0

# 3. Run pre-deployment checks
kubectl run pre-deploy-tests --image=campus-tokens:prod-1.0.0 -- pytest test_production.py

# 4. Canary deployment (5% traffic)
kubectl set image deployment/campus-tokens-backend-canary \
  backend=campus-tokens:prod-1.0.0 --record

sleep 30
# Monitor metrics (error rate, latency, success rate)

# 5. Blue-green deployment (50% traffic split)
kubectl set image deployment/campus-tokens-backend-green \
  backend=campus-tokens:prod-1.0.0 --record

# 6. Full production rollout (100% traffic)
kubectl set image deployment/campus-tokens-backend-blue \
  backend=campus-tokens:prod-1.0.0 --record

# 7. Monitor and validate
# Continue monitoring for 24 hours
```

### Production Monitoring & Alerting

```yaml
# Prometheus scrape config
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - alertmanager:9093

rule_files:
  - '/etc/prometheus/rules.yml'

scrape_configs:
  - job_name: 'campus-tokens-backend'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: campus-tokens-backend

---

# Alert rules
groups:
  - name: production_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          severity: "critical"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
        for: 5m
        annotations:
          summary: "API latency high (p95 > 2s)"
          severity: "warning"

      - alert: DatabaseConnectionPoolExhausted
        expr: database_connections_in_use > database_connections_limit * 0.9
        for: 5m
        annotations:
          summary: "Database connection pool utilization > 90%"
          severity: "critical"

      - alert: PhotoValidationFailureRate
        expr: rate(photo_validation_failures_total[5m]) > 0.1
        for: 10m
        annotations:
          summary: "Photo validation failure rate > 10%"
          severity: "warning"

      - alert: FaceRecognitionDown
        expr: face_recognition_available == 0
        for: 5m
        annotations:
          summary: "Face recognition service unavailable"
          severity: "warning"

      - alert: S3UploadFailures
        expr: rate(s3_upload_failures_total[5m]) > 0.01
        for: 5m
        annotations:
          summary: "S3 upload failure rate elevated"
          severity: "critical"

      - alert: RedisDown
        expr: redis_connected_clients == 0
        for: 2m
        annotations:
          summary: "Redis cluster unreachable"
          severity: "critical"
```

---

## Database Migration Strategy

### Migration Process (Zero-Downtime)

```bash
# 1. Pre-migration validation
python manage.py makemigrations --check --dry-run

# 2. Create migration
python manage.py makemigrations

# 3. Staging deployment
python manage.py migrate --database=staging

# 4. Validation on staging
./run_tests.sh staging

# 5. Production migration (during low-traffic period)
# Step A: Deploy new application code (backwards-compatible)
kubectl set image deployment/campus-tokens-backend \
  backend=campus-tokens:prod-new --record

# Step B: Run migration with zero-downtime strategy
python manage.py migrate --database=production --add-column-safely

# Specific pattern for adding columns:
# 1. Add column as nullable
# 2. Deploy code that populates column
# 3. Add NOT NULL constraint (if needed)
# 4. Deploy code that uses column

# 6. Monitor and validate
kubectl logs -l app=campus-tokens-backend -f
```

### Rollback Strategy

```bash
# Automated rollback on deployment failure
# 1. Canary deployment fails (error rate > 5%)
kubectl rollout undo deployment/campus-tokens-backend-canary

# 2. Blue-green deployment monitored
# If issues detected in first 30 minutes:
kubectl set image deployment/campus-tokens-backend-blue \
  backend=campus-tokens:prod-previous --record

# 3. Database rollback (if migration fails)
# Maintain multiple versions of migrations
# Use feature flags to disable new features
python manage.py migrate 0001_previous_stable_migration
```

---

## Disaster Recovery & Backups

### Backup Strategy

```yaml
# Backup retention policy
Database Backups:
  - Hourly snapshots: 7-day retention
  - Daily snapshots: 30-day retention
  - Monthly archives: 1-year retention
  - Location: Multi-region S3

Photos Storage (S3):
  - Versioning: Unlimited
  - Cross-region replication: Enabled
  - Backup bucket: Separate account

Encryption Keys (KMS):
  - Master key: AWS-managed, rotated annually
  - Data encryption key: Rotated every 90 days
  - Backups: Encrypted with separate key

Configuration & Secrets:
  - Backup: AWS Secrets Manager
  - Replication: Multi-region
  - Audit logging: CloudTrail
```

### Disaster Recovery Procedure

```bash
# RTO (Recovery Time Objective): 15 minutes
# RPO (Recovery Point Objective): 1 hour

# 1. Database recovery from latest snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier campus-tokens-prod-restored \
  --snapshot-identifier campus-tokens-prod-snapshot-latest \
  --engine aurora-postgresql

# 2. Update application to point to recovered database
kubectl set env deployment/campus-tokens-backend \
  DATABASE_URL=postgresql://user:pass@campus-tokens-prod-restored.rds.amazonaws.com

# 3. Verify data integrity
python manage.py check --deploy
pytest test_disaster_recovery.py

# 4. Failover to secondary region (if primary region down)
# Applications automatically failover to secondary region
# via Route53 health check + failover routing policy

# 5. Monitor recovery
kubectl logs -l app=campus-tokens-backend -f
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections
```

---

## Scaling & Performance

### Horizontal Scaling

```yaml
# Auto-scaling triggers

CPU Utilization:
  - Scale up: > 70% for 5 minutes
  - Scale down: < 30% for 10 minutes
  - Max replicas: 10 (production)

Memory Utilization:
  - Scale up: > 80% for 5 minutes
  - Scale down: < 40% for 10 minutes
  - Max replicas: 10

Request Queue Depth:
  - Scale up: > 100 queued requests
  - Scale down: < 10 queued requests

Network Throughput:
  - Scale up: > 1 Gbps
  - Scale down: < 100 Mbps
```

### Vertical Scaling

```
Development:
├─ Backend: 1 node (t3.small)
├─ Database: db.t3.micro (1 CPU, 1GB RAM)
└─ Redis: cache.t3.micro

Staging:
├─ Backend: 2 nodes (t3.medium)
├─ Database: db.r5.large (2 CPU, 16GB RAM)
└─ Redis: cache.r5.large

Production:
├─ Backend: 5+ nodes (m5.large auto-scaling)
├─ Database: db.r6g.2xlarge (8 CPU, 64GB RAM)
└─ Redis: cache.r6g.xlarge (4 CPU, 26GB RAM)
```

---

## Cost Optimization

### Production Cost Breakdown (Monthly Estimate)

| Component | Usage | Cost |
|-----------|-------|------|
| EKS Cluster | 5 m5.large nodes | $640 |
| RDS Aurora | db.r6g.2xlarge | $1,800 |
| ElastiCache | cache.r6g.xlarge | $420 |
| S3 Photos | 500 GB storage + transfer | $250 |
| Data Transfer | 1 TB/month out | $85 |
| KMS Keys | 2 keys | $2/month |
| CloudWatch | Logs + monitoring | $200 |
| **Total** | | **~$3,397/month** |

### Cost Optimization Strategies

1. **Reserved Instances**: Commit to 1-3 year terms for 30-50% savings
2. **Spot Instances**: Use for non-critical workloads (20-70% savings)
3. **S3 Lifecycle Policies**: Archive old photos to Glacier
4. **Data Transfer Optimization**: Use CloudFront CDN for public assets
5. **Database Read Replicas**: Balance read load to reduce single-instance cost

---

## Security & Compliance in Deployment

### Network Security

```yaml
# VPC Architecture
VPC: 10.0.0.0/16
├─ Public Subnets: 10.0.1.0/24, 10.0.2.0/24
│  ├─ ALB (Load Balancer)
│  └─ NAT Gateway
├─ Private Subnets: 10.0.10.0/24, 10.0.11.0/24
│  ├─ EKS Nodes (Backend)
│  └─ Elasticache
└─ Database Subnets: 10.0.20.0/24, 10.0.21.0/24
   └─ RDS Database

Security Groups:
├─ ALB: Inbound 80, 443 (from 0.0.0.0/0)
├─ EKS: Inbound 8000 (from ALB only)
├─ RDS: Inbound 5432 (from EKS only)
└─ Redis: Inbound 6379 (from EKS only)
```

### Secrets Management

```bash
# All secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name /prod/campus-tokens/db-password \
  --secret-string 'XXXXX' \
  --kms-key-id arn:aws:kms:...

# Application retrieves at startup
python manage.py fetch_secrets --environment=prod
```

### Compliance & Audit

```bash
# CloudTrail logging (all API calls)
aws cloudtrail create-trail \
  --name campus-tokens-audit-trail \
  --s3-bucket-name audit-logs-bucket \
  --is-multi-region-trail

# VPC Flow Logs (network traffic)
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxx \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs

# Config rules (compliance checking)
aws configservice put-config-rule \
  --config-rule file://rules.json
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-15  
**DevOps Architect**: [Your Name/Team]  
**Status**: Phase 0 - Design Complete
