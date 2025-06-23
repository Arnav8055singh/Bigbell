import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

JENKINS_URL = os.getenv("JENKINS_URL")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")

logging.basicConfig(level=logging.INFO)

def get_all_jobs():
    url = f"{JENKINS_URL}/api/json"
    try:
        res = requests.get(url, auth=(JENKINS_USERNAME, JENKINS_TOKEN), timeout=5)
        if res.status_code == 200:
            jobs = res.json().get("jobs", [])
            return [job["name"] for job in jobs]
        else:
            logging.error(f"Failed to fetch jobs. Status Code: {res.status_code}")
            return []
    except Exception as e:
        logging.error(f"Error fetching jobs: {e}")
        return []

def get_jobs_by_customer(customer):
    all_jobs = get_all_jobs()
    return [job for job in all_jobs if job.lower().startswith(customer.lower())]

def trigger_build(job_name):
    url = f"{JENKINS_URL}/job/{job_name}/build"
    try:
        res = requests.post(url, auth=(JENKINS_USERNAME, JENKINS_TOKEN), timeout=5)
        if res.status_code in [201, 200]:
            logging.info(f"Triggered build for job: {job_name}")
            return True
        else:
            logging.error(f"Failed to trigger build. Status Code: {res.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error triggering job '{job_name}': {e}")
        return False

def get_job_status(job_name):
    url = f"{JENKINS_URL}/job/{job_name}/lastBuild/api/json"
    try:
        res = requests.get(url, auth=(JENKINS_USERNAME, JENKINS_TOKEN), timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get("result", "IN_PROGRESS") or "IN_PROGRESS"
        else:
            logging.error(f"Failed to get job status. Status Code: {res.status_code}")
            return "ERROR"
    except Exception as e:
        logging.error(f"Error getting status for job '{job_name}': {e}")
        return "ERROR"

def get_latest_build_number(job_name):
    url = f"{JENKINS_URL}/job/{job_name}/lastBuild/api/json"
    try:
        res = requests.get(url, auth=(JENKINS_USERNAME, JENKINS_TOKEN), timeout=5)
        if res.status_code == 200:
            data = res.json()
            return data.get("number")
        else:
            logging.error(f"Failed to get build number. Status Code: {res.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error getting build number for job '{job_name}': {e}")
        return None
