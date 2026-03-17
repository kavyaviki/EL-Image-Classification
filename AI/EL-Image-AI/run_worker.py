# El-image-ai/run_worker.py
# entrypoint for SQS worker(s)
from app.workers.inference import start_worker

if __name__ == "__main__":
    start_worker()