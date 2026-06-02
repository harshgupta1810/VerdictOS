import os
import random
from locust import HttpUser, task, between

class VerdictOSUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_deal_and_trigger_pipeline(self):
        pdf_dir = "testing_pdfs"
        pdfs = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        selected_pdf = random.choice(pdfs) if pdfs else "dummy.pdf"
        
        payload = {
            "client_id": "client_locust",
            "document_paths": [os.path.join(pdf_dir, selected_pdf)],
            "metadata_json": {"source": "locust_load_test"}
        }
        self.client.post("/api/v1/deals", json=payload)

    @task(3)
    def check_health(self):
        self.client.get("/api/v1/health")
