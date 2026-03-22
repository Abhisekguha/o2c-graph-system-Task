# Deployment Guide - SAP O2C Graph System

## Table of Contents
1. [Local Development](#local-development)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment Options](#cloud-deployment-options)

---

## Local Development

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git
- Gemini API Key

### Initial Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd sap-o2c-graph-system
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add GEMINI_API_KEY
   python app.py
   ```

3. **Frontend Setup** (in new terminal)
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Verify**
   - Backend: http://localhost:8000/api/health
   - Frontend: http://localhost:3000

---

## Production Deployment

### Backend (FastAPI)

#### Option 1: Using Gunicorn + Uvicorn

```bash
# Install production server
pip install gunicorn uvicorn[standard]

# Run with Gunicorn
gunicorn app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

#### Option 2: Using Uvicorn directly

```bash
uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --timeout-keep-alive 120
```

### Frontend (React)

```bash
# Build production bundle
cd frontend
npm run build

# Serve with production server
npm install -g serve
serve -s build -l 3000

# Or use nginx (recommended)
```

### Nginx Configuration

```nginx
# Backend proxy
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com;

    root /var/www/sap-o2c-frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

---

## Docker Deployment

### Dockerfile - Backend

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Dockerfile - Frontend

Create `frontend/Dockerfile`:

```dockerfile
# Build stage
FROM node:16-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### docker-compose.yml

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: sap-o2c-backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PORT=8000
    volumes:
      - ../:/data  # Mount dataset directory
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: sap-o2c-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
    environment:
      - REACT_APP_API_URL=http://backend:8000

networks:
  default:
    name: sap-o2c-network
```

### Running with Docker

```bash
# Set environment variables
export GEMINI_API_KEY=your_api_key_here

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Cloud Deployment Options

### AWS

#### EC2 Deployment

1. **Launch EC2 Instance**
   - AMI: Ubuntu 22.04
   - Instance type: t3.medium (2 vCPU, 4 GB RAM)
   - Security group: Allow ports 80, 443, 8000

2. **Setup**
   ```bash
   # SSH to instance
   ssh -i key.pem ubuntu@<instance-ip>

   # Install Docker
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker ubuntu

   # Clone and run
   git clone <repo>
   cd sap-o2c-graph-system
   docker-compose up -d
   ```

3. **Setup Domain (Optional)**
   - Point DNS to EC2 IP
   - Install certbot for SSL
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

#### ECS (Elastic Container Service)

1. Push images to ECR
2. Create task definitions
3. Create ECS service
4. Use Application Load Balancer

### Google Cloud

#### Cloud Run (Serverless)

```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/project-id/sap-o2c-backend
gcloud run deploy sap-o2c-backend \
  --image gcr.io/project-id/sap-o2c-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy frontend to Cloud Storage + Cloud CDN
npm run build
gsutil rsync -R build/ gs://bucket-name/
```

### Heroku

#### Backend

Create `Procfile` in backend/:
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

Deploy:
```bash
heroku create sap-o2c-backend
heroku config:set GEMINI_API_KEY=your_key
git subtree push --prefix backend heroku main
```

#### Frontend

Deploy to Netlify or Vercel (easier than Heroku for React):

**Netlify:**
```bash
npm run build
netlify deploy --prod --dir=build
```

### Azure

#### App Service

```bash
# Create resource group
az group create --name sap-o2c-rg --location eastus

# Create App Service plan
az appservice plan create \
  --name sap-o2c-plan \
  --resource-group sap-o2c-rg \
  --sku B1 \
  --is-linux

# Create Web App for backend
az webapp create \
  --resource-group sap-o2c-rg \
  --plan sap-o2c-plan \
  --name sap-o2c-backend \
  --runtime "PYTHON|3.9"

# Deploy frontend to Static Web App
az staticwebapp create \
  --name sap-o2c-frontend \
  --resource-group sap-o2c-rg \
  --source ./frontend \
  --location eastus
```

---

## Environment Variables

### Production Environment Variables

**Backend:**
```bash
GEMINI_API_KEY=your_production_key
PORT=8000
DATA_PATH=/data/sap-o2c
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Frontend:**
```bash
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_ENV=production
```

---

## Performance Tuning

### Backend

**Increase workers:**
```bash
# For CPU-bound tasks
workers = (2 x $NUM_CORES) + 1

# Example: 4 cores
gunicorn ... --workers 9
```

**Connection pooling:**
```python
# Add to config.py
MAX_CONNECTIONS = 100
TIMEOUT = 120
```

### Frontend

**Build optimization:**
```json
{
  "scripts": {
    "build": "GENERATE_SOURCEMAP=false react-scripts build"
  }
}
```

**Enable gzip compression in nginx:**
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

---

## Monitoring

### Health Checks

```bash
# Backend health
curl https://api.yourdomain.com/api/health

# Expected response
{"status":"healthy","graph_loaded":true}
```

### Logging

**Backend:**
```python
# Add to app.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
```

**Log aggregation:**
- Use CloudWatch (AWS)
- Use Stackdriver (GCP)
- Use Application Insights (Azure)

### Metrics

Monitor:
- Request rate
- Response time
- Error rate
- Memory usage
- CPU usage

Tools:
- Prometheus + Grafana
- DataDog
- New Relic

---

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Set strong CORS policies
- [ ] Rate limit API endpoints
- [ ] Sanitize user inputs
- [ ] Use environment variables for secrets
- [ ] Enable firewall rules
- [ ] Regular security updates
- [ ] Backup data regularly
- [ ] Monitor for suspicious activity

---

## Troubleshooting

**Container won't start:**
```bash
docker-compose logs backend
docker-compose logs frontend
```

**Out of memory:**
- Increase container memory limits
- Add swap space
- Optimize graph loading (sample data)

**Slow graph loading:**
- Pre-compute graph statistics
- Implement caching
- Use pagination for large datasets

---

## Backup Strategy

**Data:**
```bash
# Backup JSONL files
tar -czf backup-$(date +%Y%m%d).tar.gz *.jsonl

# Upload to S3
aws s3 cp backup-*.tar.gz s3://backup-bucket/
```

**Database (if using Neo4j):**
```bash
neo4j-admin dump --database=neo4j --to=/backups/neo4j.dump
```

---

## Scaling Considerations

**Horizontal Scaling:**
- Add more backend workers/containers
- Use load balancer (ALB, NLB)
- Distribute frontend via CDN

**Vertical Scaling:**
- Increase instance size
- Add more memory/CPU

**Database Scaling:**
- Migrate to Neo4j for large graphs (>1M nodes)
- Use read replicas
- Implement caching layer (Redis)

---

## Cost Optimization

**AWS:**
- Use Reserved Instances (40-70% savings)
- Auto-scaling groups
- S3 lifecycle policies

**Google Cloud:**
- Committed use discounts
- Cloud Run (pay per request)
- Cloud CDN for frontend

**Azure:**
- Reserved VM instances
- Azure CDN
- App Service plans

---

**Need help? Contact support or check logs for detailed error messages.**
