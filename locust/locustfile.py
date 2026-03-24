from locust import HttpUser, between, task


class AuthAndPrimeUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def login(self):
        payload = {"username": "alice", "password": "alice_password"}
        self.client.post("/login", json=payload, name="/login")

    @task(2)
    def check_prime(self):
        self.client.get("/check-prime", params={"number": 104729}, name="/check-prime")

    @task(1)
    def list_primes_small(self):
        self.client.get("/primes", params={"n": 50000}, name="/primes")

    @task(1)
    def async_prime_job(self):
        response = self.client.post("/prime-jobs", json={"n": 300000, "segment_size": 50000}, name="/prime-jobs")
        if response.status_code == 200:
            job_id = response.json().get("job_id")
            if job_id:
                self.client.get(f"/prime-jobs/{job_id}", name="/prime-jobs/{id}")
