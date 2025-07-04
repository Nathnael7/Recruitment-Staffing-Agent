import os
import uuid
from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from googleapiclient.discovery import build
from services.auth import get_google_credentials
from workflows.recruitment_graph import build_graph
from dotenv import load_dotenv
from services.sheets import read_job_role, write_results_to_results_tab
import uuid
from database.mongo import store_result
import traceback
import logging


# Setup logging
log_dir = ".logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "webhook.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()

DRIVE_WEBHOOK_URL = os.getenv("DRIVE_WEBHOOK_URL")
if not DRIVE_WEBHOOK_URL:
    raise RuntimeError("Missing DRIVE_WEBHOOK_URL in environment")


app = FastAPI()
app_workflow = build_graph()

def get_files_in_folder(folder_id):
    logging.info(f"Fetching files in folder: {folder_id}")
    try:
        creds = get_google_credentials()
        drive = build("drive", "v3", credentials=creds)
        results = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            orderBy="createdTime desc"
        ).execute()
        logging.info("Files fetched successfully from folder.")
        return results.get("files", [])
    except Exception as e:
        logging.error(f"Error fetching files in folder {folder_id}: {e}", exc_info=True)
        return []


def process_all_roles():
    logging.info("Starting process_all_roles")
    try:
        roles = read_job_role()
        for role in roles:
            folder_id = role["folder_id"]
            job_title = role["title"]
            files = get_files_in_folder(folder_id)
            if not files:
                logging.info(f"No resumes found for job title: {job_title}")
                continue
            state = {
                "job": {
                    "title": role["title"],
                    "responsibilities": role["responsibilities"],
                    "folder_id": role["folder_id"],
                },
                "resumes": [{"id": f["id"], "name": f["name"]} for f in files],
                "culture": "",
                "parsed_resumes": [],
                "matches": []
            }
            try:
                result = app_workflow.invoke(state)
                matches = result.get("matches", [])
                if matches and isinstance(matches, list) and matches and isinstance(matches[0], list):
                    matches = [
                        {"name": m[0], "score": m[1], "status": m[2], "email": m[3]}
                        for m in matches
                    ]
                elif matches and isinstance(matches, list) and matches and isinstance(matches[0], dict):
                    pass
                else:
                    logging.warning(f"Matches format unexpected for job title {job_title}: {matches}")
                write_results_to_results_tab(job_title, matches)
            except Exception as e:
                logging.error(f"Error processing role {job_title}: {e}", exc_info=True)
        logging.info("Finished process_all_roles")
    except Exception as e:
        logging.error(f"Error in process_all_roles: {e}", exc_info=True)

channel_to_folder = {}

def register_webhook_for_subfolder(folder_id, webhook_url):
    try:
        creds = get_google_credentials()
        drive = build("drive", "v3", credentials=creds)
        channel_id = str(uuid.uuid4())
        body = {
            "id": channel_id,
            "type": "webhook",
            "address": webhook_url,
        }
        watch = drive.files().watch(fileId=folder_id, body=body).execute()
        logging.info(f"Registered webhook for subfolder {folder_id}: Channel ID {watch.get('id')}")
        channel_to_folder[watch["id"]] = folder_id
    except Exception as e:
        logging.error(f"Error registering webhook for folder {folder_id}: {e}", exc_info=True)

import threading
import time

def refresh_roles_periodically(interval=60):
    """
    Periodically refresh roles and register webhooks for new folders.
    """
    while True:
        logging.info("Refreshing roles and registering webhooks...")
        try:
            roles = read_job_role()
            for role in roles:
                folder_id = role["folder_id"]
                register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)
            process_all_roles()
        except Exception as e:
            logging.error(f"Error during periodic refresh: {e}", exc_info=True)
        time.sleep(interval)

@app.on_event("startup")
def register_all_subfolder_webhooks():
    """
    Register a Drive push notification channel (watch) for each subfolder at startup.
    """
    try:
        roles = read_job_role()
        for role in roles:
            folder_id = role["folder_id"]
            register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)
        logging.info("All subfolder webhooks registered at startup.")
    except Exception as e:
        logging.error(f"Error registering subfolder webhooks at startup: {e}", exc_info=True)

from fastapi import Body

@app.post("/refresh_roles")
async def refresh_roles(payload: dict = Body(...)):
    logging.info("Received /refresh_roles POST request.")
    folder_id = payload.get("folder_id")
    job_title = payload.get("title")
    responsibilities = payload.get("responsibilities")

    if not (folder_id and job_title and responsibilities):
        logging.warning("Missing folder_id, title, or responsibilities in payload.")
        return {"status": "error", "message": "Missing folder_id, title, or responsibilities in payload"}

    try:
        if folder_id not in channel_to_folder.values():
            register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)

        files = get_files_in_folder(folder_id)
        if not files:
            logging.info(f"No resumes found for job title: {job_title}")
            return {"status": f"No resumes found for {job_title}"}

        for file in files:
            logging.info(f"Processing file for job title {job_title}: File ID {file['id']}")
            state = {
                "job": {
                    "title": job_title,
                    "responsibilities": responsibilities,
                    "folder_id": folder_id,
                },
                "resumes": [{"id": file["id"], "name": file["name"]}],
                "culture": "",
                "parsed_resumes": [],
                "matches": []
            }
            try:
                result = app_workflow.invoke(state)
                matches = result.get("matches", [])
                write_results_to_results_tab(job_title, matches)
                for match in matches:
                    store_result(job_title, match)
            except Exception as e:
                logging.error(f"Error processing file {file['id']} for job {job_title}: {e}", exc_info=True)

        return {"status": f"Processed all files for {job_title}"}
    except Exception as e:
        logging.error(f"Error in /refresh_roles endpoint: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

PROCESSED_FILES = set()

@app.post("/webhook/drive")
async def google_drive_webhook(
    request: Request,
    x_goog_channel_id: str = Header(None),
    x_goog_resource_state: str = Header(None),
    x_goog_resource_id: str = Header(None),
    x_goog_message_number: str = Header(None),
):
    logging.info("Webhook triggered: Channel ID %s, Resource State %s, Resource ID %s, Message Number %s",
                 x_goog_channel_id, x_goog_resource_state, x_goog_resource_id, x_goog_message_number)

    if x_goog_resource_state not in ("add", "update"):
        logging.info("Webhook event ignored: Not a new file upload or update.")
        return JSONResponse(content={"status": "ignored"})

    try:
        folder_id = channel_to_folder.get(x_goog_channel_id)
        if not folder_id:
            logging.warning("No matching folder found for webhook event: Channel ID %s", x_goog_channel_id)
            return JSONResponse(content={"status": "no matching folder"})

        roles = read_job_role()
        job_title = None
        for role in roles:
            if role["folder_id"] == folder_id:
                job_title = role["title"]
                break

        if not job_title:
            logging.warning("No matching job title found for folder: %s", folder_id)
            return JSONResponse(content={"status": "no matching job title"})

        creds = get_google_credentials()
        drive = build("drive", "v3", credentials=creds)
        results = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            orderBy="createdTime desc",
            pageSize=1
        ).execute()
        files = results.get("files", [])
        if not files:
            logging.info("No files found in folder: %s", folder_id)
            return JSONResponse(content={"status": "no files in folder"})

        latest_file = files[0]
        logging.info(f"Processing latest file for job title {job_title}: File ID {latest_file['id']}")

        state = {
            "job": {
                "title": job_title,
                "responsibilities": next(role["responsibilities"] for role in roles if role["folder_id"] == folder_id),
                "folder_id": folder_id,
            },
            "resumes": [{"id": latest_file["id"], "name": latest_file["name"]}],
            "culture": "",
            "parsed_resumes": [],
            "matches": []
        }
        try:
            result = app_workflow.invoke(state)
            matches = result.get("matches", [])
            write_results_to_results_tab(job_title, matches)
            for match in matches:
                store_result(job_title, match)
            logging.info("Processed latest file for job title: %s", job_title)
            return JSONResponse(content={"status": "processed latest file"})
        except Exception as e:
            logging.error(f"Error processing latest file for job {job_title}: {e}", exc_info=True)
            return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)
    except Exception as e:
        logging.error(f"Error in webhook handler: {e}", exc_info=True)
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)