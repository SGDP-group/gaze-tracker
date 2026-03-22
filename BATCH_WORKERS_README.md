# Batch Processing Workers

This document describes how to set up and manage dedicated Celery workers for batch processing of focus tracking sessions.

## Architecture

The batch processing system uses dedicated Celery workers that:
- Process frame directories asynchronously
- Handle auto-calibration using first 10 seconds of frames
- Clean up frames and directories after processing
- Run on separate queues to avoid blocking other operations

## Quick Start

### 1. Install Dependencies

```bash
# Install additional dependencies for workers
pip install psutil
```

### 2. Start Redis

```bash
# Start Redis server
redis-server --port 6380
```

### 3. Start Batch Workers

```bash
# Start 2 batch processing workers
cd /home/lahirud/gaze_tracker
./scripts/manage_batch_workers.sh start

# Or specify number of workers
WORKERS=4 ./scripts/manage_batch_workers.sh start
```

### 4. Check Status

```bash
# Check worker status
./scripts/manage_batch_workers.sh status

# View logs
./scripts/manage_batch_workers.sh logs
```

## Worker Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis server host |
| `REDIS_PORT` | 6380 | Redis server port |
| `REDIS_DB` | 0 | Redis database number |
| `WORKERS` | 2 | Number of worker processes |
| `WORKER_CONCURRENCY` | 1 | Tasks per worker process |
| `LOG_LEVEL` | INFO | Logging level |

### Worker Settings

- **Queue**: `batch_processing`
- **Concurrency**: 1 task per worker (resource-intensive)
- **Max Tasks per Child**: 5 (restart after 5 tasks)
- **Time Limit**: 1 hour per batch processing task
- **Rate Limit**: 10 tasks per minute

## Management Commands

### Start Workers
```bash
./scripts/manage_batch_workers.sh start
```

### Stop Workers
```bash
./scripts/manage_batch_workers.sh stop
```

### Restart Workers
```bash
./scripts/manage_batch_workers.sh restart
```

### Scale Workers
```bash
# Scale to 4 workers
./scripts/manage_batch_workers.sh scale 4
```

### Check Status
```bash
./scripts/manage_batch_workers.sh status
```

### View Logs
```bash
./scripts/manage_batch_workers.sh logs
```

## Systemd Service

For production deployment, use the provided systemd service:

```bash
# Install service
sudo cp scripts/gaze-tracker-batch-worker@.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable gaze-tracker-batch-worker@1.service
sudo systemctl start gaze-tracker-batch-worker@1.service
```

## Monitoring

### Resource Monitoring
Workers automatically monitor and report:
- CPU usage percentage
- Memory usage and availability
- Disk space availability
- Task progress updates

### Health Checks
Monitor worker health:
```bash
# Check Celery stats
cd /home/lahirud/gaze_tracker
python3 -c "
from src.services.celery_app import celery_app
inspect = celery_app.control.inspect()
print(inspect.stats())
"
```

## Queue Configuration

The system uses separate queues for different task types:

| Queue | Purpose | Tasks |
|-------|---------|-------|
| `batch_processing` | Frame batch processing | `process_session_frames_async` |
| `ml_training` | ML model training | `train_user_model_async`, `generate_recommendations_async` |
| `maintenance` | Cleanup tasks | `cleanup_old_tasks` |
| `default` | Other tasks | - |

## Performance Tuning

### Worker Scaling
- **Start with 2-4 workers** for moderate load
- **Scale based on queue length** and resource usage
- **Monitor CPU and memory** during peak usage

### Resource Limits
- Each worker processes **1 task at a time** (resource-intensive)
- Workers restart after **5 tasks** to prevent memory leaks
- **1 hour timeout** per batch processing task

### Directory Structure
```
/home/lahirud/gaze_tracker/
├── scripts/
│   ├── start_batch_worker.sh
│   ├── manage_batch_workers.sh
│   └── gaze-tracker-batch-worker@.service
├── src/services/
│   ├── batch_worker.py          # Worker configuration
│   ├── batch_service.py         # Batch processing logic
│   └── celery_app.py            # Celery configuration
└── logs/
    └── batch_worker_*.log       # Worker logs
```

## Troubleshooting

### Common Issues

1. **Workers not starting**
   - Check Redis connection
   - Verify file permissions
   - Check systemd service status

2. **Tasks stuck in queue**
   - Verify worker is listening to correct queue
   - Check worker logs for errors
   - Restart workers if needed

3. **High memory usage**
   - Workers automatically restart after 5 tasks
   - Monitor with resource monitoring
   - Scale workers if needed

### Debug Mode
```bash
# Start worker in debug mode
celery -A src.services.batch_worker worker --loglevel=debug --queues=batch_processing
```

## Security Considerations

- Workers run with limited privileges
- File access restricted to specific directories
- Network access limited to Redis
- Automatic cleanup of temporary files
