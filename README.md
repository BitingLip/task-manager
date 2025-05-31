# Task Manager Module

🚧 **Status: In Development**

The Task Manager handles task scheduling, queuing, and lifecycle management for the BitingLip AI inference platform.

## Features

- ✅ Task creation and scheduling
- ✅ Task queue management  
- ✅ Task status tracking
- ✅ RESTful API endpoints
- 🚧 Task result storage (planned)
- 🚧 Task retry and failure handling (planned)
- 🚧 Database integration (planned)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python app/main.py
```

The service will start on `http://localhost:8004`

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health check with metrics
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task details
- `GET /tasks` - List tasks with filtering
- `PUT /tasks/{task_id}/status` - Update task status
- `DELETE /tasks/{task_id}` - Delete a task
- `GET /metrics` - Get task manager metrics

## Documentation

See [docs/](docs/) for detailed documentation:
- [Architecture](docs/architecture.md) (planned)
- [API Reference](docs/api.md) (planned)
- [Development Guide](docs/development.md) (planned)

## Integration

The Task Manager integrates with:
- **Gateway Manager**: Receives task requests
- **Cluster Manager**: Distributes tasks to workers
- **Model Manager**: Coordinates model loading

For shared data models and utilities, see the `common/` module at the project root.

**🎯 Key Goal: Ensure seamless operation and testing of the distributed, submodule-based BitingLip system.**

## 🏗️ System Architecture (Conceptual View from Task Manager)

The `task-manager` oversees the interaction of the following submodules:

```
                                      ┌─────────────────┐
                                      │  User Interface │ (Frontend)
                                      └─────────────────┘
                                              │ (Interacts with)
                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Task Manager    │───▶│ Gateway Manager │───▶│ Cluster Manager │───▶│ Model Manager   │
│ (Orchestration, │    │ (API Entry)     │    │ (Worker Control)│    │ (Model Storage  │
│  Testing, Docs) │    └─────────────────┘    └─────────────────┘    │  & Access)      │
└─────────────────┘                                                       └─────────────────┘
```
- **User Interface**: Provides the user-facing interaction layer.
- **Gateway Manager**: Exposes the system's capabilities via an API.
- **Cluster Manager**: Manages the distributed workers and computational resources.
- **Model Manager**: Handles the storage, retrieval, and management of AI models.

The `task-manager` contains scripts and tests that touch all these areas to ensure they function correctly together.

## 📁 Project Structure within Task Manager

The `task-manager` submodule itself might contain:
- `tests/`: Directory for integration tests, end-to-end tests.
    - `test_end_to_end_inference.py`
    - `test_system_deployment.py`
- `scripts/`: Deployment scripts, helper utilities.
    - `deploy_all.ps1` / `deploy_all.sh`
    - `start_system.ps1`
    - `stop_system.ps1`
    - `validate_migration.py` (as created previously)
- `docs/`: System-level documentation, architecture diagrams.
    - `architecture.md`
    - `deployment_guide.md`
- `config/`: Example configurations for system-wide deployment.
- `README.md`: This file.

*(The detailed project structure from the old monolithic `amd-cluster/README.md` is now distributed among the respective submodules. This README should focus on the `task-manager`'s contents and its role in managing the collection of submodules.)*

## 🚦 Quick Start / Key Operations

### 1. Setting up the Environment
Ensure all submodules are cloned and initialized:
```bash
git clone --recurse-submodules <main_repo_url>
cd biting-lip 
# (or if already cloned)
# git submodule update --init --recursive
```

### 2. Running Integration Tests
(Example command, actual script may vary)
```powershell
cd task-manager
python -m pytest tests/ 
# or specific test files:
# python tests/test_end_to_end_inference.py 
```

### 3. Deploying the System
(Example command, actual script may vary)
```powershell
cd task-manager/scripts
./deploy_all.ps1 
```

## Key Files Previously Mentioned (and their new context)

- **`docker-compose.yml`**: If it manages infrastructure common to multiple components (like a central Redis), it might reside in the main `biting-lip` repository root or within `task-manager` if it's primarily for orchestrating a full-system deployment for testing. If it's specific to `cluster-manager` (e.g., for its own Redis instance), it would be in `cluster-manager/`.
- **`start_cluster.bat`**: Likely superseded by more granular start scripts in each submodule and a master orchestration script in `task-manager/scripts/`.
- **`manage-cluster.ps1`**: Parts of this might be refactored into `cluster-manager` for worker-specific management, while system-wide management aspects could be in `task-manager/scripts/`.
- **`test_cluster.py`**: This would evolve into more specific integration tests within `task-manager/tests/`.
- **`validate_cluster.py`**: Similar to `test_cluster.py`, its functionality would be part of the integration tests or specific validation scripts in `task-manager`.

The `task-manager` ensures that all these individual pieces, now in their respective submodules, can be brought together to form a functional system.

## 🎯 Live Test Results

**✅ Successfully Tested:**
- **LLM Inference**: GPT-2 model generating coherent text responses
- **Response Time**: 5-18 seconds for 50-100 token generation
- **Task Processing**: Celery workers processing without errors
- **API Endpoints**: All REST endpoints functional
- **GPU Detection**: All 5 AMD GPUs detected and available

**Sample Test Output:**
```
[TEST] LLM Inference - GPT-2 Model
Input: "Write a short story about AI"
Response: "Write a short story about AI and the future of humanity. The story is set in the year 2050..."
Status: ✅ SUCCESS (Generated 87 tokens in 12.3 seconds)
```

## 🔧 Configuration

### API Gateway Configuration (`.env`)

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO

# Security
API_KEY_REQUIRED=false
RATE_LIMIT_ENABLED=true
```

### Worker Configuration (`.env`)

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# GPU Configuration
WORKER_GPU_INDEX=0
DIRECTML_DEVICE_INDEX=0

# Model Configuration
MODELS_CACHE_DIR=./models
MAX_MODEL_MEMORY_GB=8
MODEL_TIMEOUT_SECONDS=300

# Worker Configuration (IMPORTANT: Use solo pool for Windows)
WORKER_CONCURRENCY=1
WORKER_LOG_LEVEL=INFO
WORKER_POOL=solo
```

## 🔧 Critical Windows Fixes Applied

**⚠️ Windows-Specific Configuration:**
The cluster includes critical fixes for Windows compatibility:

1. **Celery Pool Configuration**: Uses `solo` pool instead of `prefork` to prevent `ValueError: not enough values to unpack` errors
2. **Task Name Mapping**: Fixed inconsistent task names between API gateway and workers
3. **DirectML Integration**: Proper GPU device selection for AMD GPUs on Windows

These fixes are already applied in the startup scripts and configuration files.

## 📊 Monitoring and Management

### Web Interfaces

- **API Documentation:** http://localhost:8080/docs (Swagger UI)
- **Flower (Celery Monitor):** http://localhost:5555
- **Redis Commander:** http://localhost:8081
- **Prometheus Metrics:** http://localhost:8080/metrics

### Management Scripts

```powershell
# PowerShell management script
.\manage-cluster.ps1 -Action start     # Start all services
.\manage-cluster.ps1 -Action stop      # Stop all services
.\manage-cluster.ps1 -Action status    # Check service status
.\manage-cluster.ps1 -Action restart   # Restart all services
```

## 🎯 Supported AI Tasks

### 1. Large Language Model (LLM) Inference

```json
{
  "task_type": "llm",
  "payload": {
    "text": "Write a short story about AI",
    "max_tokens": 100,
    "temperature": 0.7,
    "model": "microsoft/DialoGPT-medium"
  }
}
```

### 2. Stable Diffusion Image Generation

```json
{
  "task_type": "stable_diffusion",
  "payload": {
    "prompt": "A beautiful sunset over mountains",
    "negative_prompt": "blurry, low quality",
    "num_inference_steps": 20,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512
  }
}
```

### 3. Text-to-Speech (TTS)

```json
{
  "task_type": "tts",
  "payload": {
    "text": "Hello, this is a test of text-to-speech synthesis",
    "voice": "en-US-AriaNeural",
    "rate": "medium",
    "pitch": "medium"
  }
}
```

### 4. Image-to-Text

```json
{
  "task_type": "image_to_text",
  "payload": {
    "image_data": "base64_encoded_image_data",
    "model": "Salesforce/blip-image-captioning-base"
  }
}
```

## 📡 API Reference

### Submit Task
```http
POST /submit
Content-Type: application/json

{
  "task_type": "llm|stable_diffusion|tts|image_to_text",
  "payload": { /* task-specific parameters */ }
}
```

### Check Task Status
```http
GET /status/{task_id}
```

### Get Task Result
```http
GET /result/{task_id}
```

### Cluster Health
```http
GET /health
GET /cluster/status
```

### Metrics
```http
GET /metrics
```

## 🔄 Production Deployment

### Windows Service Installation

For production deployment, install services using NSSM:

```powershell
# Install NSSM
choco install nssm

# Install API Gateway as Windows Service
nssm install AMDClusterAPI
nssm set AMDClusterAPI Application "C:\Python310\python.exe"
nssm set AMDClusterAPI AppParameters "-m uvicorn api_gateway.app.main:app --host 0.0.0.0 --port 8080"
nssm set AMDClusterAPI AppDirectory "d:\amd-cluster"
nssm start AMDClusterAPI

# Install Worker Services (repeat for each GPU)
for ($i=0; $i -lt 5; $i++) {
    nssm install "AMDClusterWorker$i"
    nssm set "AMDClusterWorker$i" Application "C:\Python310\python.exe"
    nssm set "AMDClusterWorker$i" AppParameters "-m celery -A worker.app.tasks worker --loglevel=info"
    nssm set "AMDClusterWorker$i" AppDirectory "d:\amd-cluster"
    nssm set "AMDClusterWorker$i" AppEnvironmentExtra "WORKER_GPU_INDEX=$i"
    nssm start "AMDClusterWorker$i"
}
```

### Load Balancing

For high availability, you can run multiple API gateway instances behind a load balancer:

```powershell
# Start multiple API instances
uvicorn api_gateway.app.main:app --host 0.0.0.0 --port 8080
uvicorn api_gateway.app.main:app --host 0.0.0.0 --port 8081
uvicorn api_gateway.app.main:app --host 0.0.0.0 --port 8082
```

## 🧪 Testing

### Automated Testing

```powershell
# Run comprehensive test suite
python test_cluster.py

# Run specific test categories
python test_cluster.py --test-type health
python test_cluster.py --test-type llm
python test_cluster.py --test-type stable_diffusion
```

### Manual Testing

```powershell
# Test health endpoints
curl http://localhost:8080/health
curl http://localhost:8080/cluster/status

# Submit test tasks
curl -X POST http://localhost:8080/submit -H "Content-Type: application/json" -d @test_llm.json
curl -X POST http://localhost:8080/submit -H "Content-Type: application/json" -d @test_sd.json
```

## 🛠️ Troubleshooting

### Common Issues

1. **DirectML Device Not Found**
   - Ensure AMD drivers are properly installed
   - Check GPU index configuration in worker .env files
   - Verify DirectML installation: `python -c "import torch_directml; print(torch_directml.device_count())"`

2. **Redis Connection Failed**
   - Verify Redis is running: `docker ps | grep redis`
   - Check Redis configuration in .env files
   - Test connection: `redis-cli ping`

3. **Worker Not Processing Tasks**
   - Check worker logs for errors
   - Verify GPU memory availability
   - Restart worker process

4. **Model Loading Errors**
   - Check internet connection for model downloads
   - Verify models cache directory permissions
   - Clear model cache if corrupted: `Remove-Item worker\app\models\* -Recurse -Force`
   - Use model download script: `cd worker\models && python download_models.py`

5. **🔴 ValueError: not enough values to unpack (RESOLVED)**
   - **Root Cause**: Celery prefork pool incompatibility with Windows thread-local storage
   - **Solution**: Changed to `solo` pool in worker configuration (already applied)
   - **Verification**: Test with `python test_cluster.py`

### Log Files

- **API Gateway:** Check console output or configure file logging
- **Workers:** Check Celery worker logs
- **Redis:** `docker logs amd-cluster-redis-1`

### Performance Tuning

1. **GPU Memory Optimization**
   - Adjust `MAX_MODEL_MEMORY_GB` in worker configuration
   - Use model quantization for larger models
   - Monitor GPU memory usage

2. **Task Concurrency**
   - Adjust `WORKER_CONCURRENCY` for each GPU's capacity
   - Balance between throughput and memory usage

3. **Model Caching**
   - Pre-load frequently used models
   - Configure appropriate cache sizes
   - Use model quantization where applicable

## 📈 Performance Metrics

### Expected Performance (per GPU)

- **LLM Inference:** 10-50 tokens/second (GPT-2: ~8 tokens/sec tested ✅)
- **Stable Diffusion:** 2-10 seconds per image (512x512)
- **TTS:** Real-time to 2x real-time processing
- **Image-to-Text:** 1-5 seconds per image

**Tested Results:**
- GPT-2 (124M parameters): 5-18 seconds for 50-100 tokens
- Response quality: Coherent and contextually appropriate text generation

### Scaling Considerations

- Each GPU can handle 1-4 concurrent tasks depending on model size
- Memory usage scales with model size and batch size
- Network I/O may become bottleneck for large models

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- AMD for DirectML support
- Microsoft for DirectML and ONNX Runtime
- Hugging Face for transformer models
- FastAPI and Celery communities

---

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Open an issue on GitHub with detailed information

**System Requirements:**
- Windows 11 Pro
- AMD GPU with DirectML support
- Python 3.10+
- 16GB+ RAM recommended
- SSD storage for model caching
