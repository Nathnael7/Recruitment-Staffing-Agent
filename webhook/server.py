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
import requests
from database.mongo import store_result

import traceback

load_dotenv()

DRIVE_WEBHOOK_URL = os.getenv("DRIVE_WEBHOOK_URL")
if not DRIVE_WEBHOOK_URL:
    raise RuntimeError("Missing DRIVE_WEBHOOK_URL in environment")


app = FastAPI()
app_workflow = build_graph()

def get_files_in_folder(folder_id):
    print(f"Fetching files in folder: {folder_id}")
    creds = get_google_credentials()
    drive = build("drive", "v3", credentials=creds)
    results = drive.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        orderBy="createdTime desc"
    ).execute()
    print("getting files")
    return results.get("files", [])


def process_all_roles():
    print("Starting process_all_roles")
    roles = read_job_role()
    for role in roles:
        folder_id = role["folder_id"]
        job_title = role["title"]
        files = get_files_in_folder(folder_id)
        if not files:
            print(f"No resumes found for {job_title}")
            continue
        state = {
            "job": {
                "title": role["title"],
                "responsibilities": role["responsibilities"],
                "folder_id": role["folder_id"],  # <-- FIX: include folder_id inside job
            },
            "resumes": [{"id": f["id"], "name": f["name"]} for f in files],
            "culture": "",
            "parsed_resumes": [],
            "matches": []
        }
        result = app_workflow.invoke(state)
        # print("result:", result)
        matches = result.get("matches", [])
        print("matches sample after workflow:", matches[:1], type(matches[0]) if matches else None)
        # Safely convert matches if needed
        if matches and isinstance(matches, list) and matches and isinstance(matches[0], list):
            matches = [
                {"name": m[0], "score": m[1], "status": m[2], "email": m[3]}
                for m in matches
            ]
        elif matches and isinstance(matches, list) and matches and isinstance(matches[0], dict):
            pass  # already correct
        else:
            print("WARNING: matches is not a list of dicts or lists!", matches)
        # Always write results after conversion/validation
        write_results_to_results_tab(job_title, matches)
        print("LAST process_all_roles")
    print("Finished process_all_roles")  # <-- Place at the end, after all roles
channel_to_folder = {}

def register_webhook_for_subfolder(folder_id, webhook_url):
    creds = get_google_credentials()
    drive = build("drive", "v3", credentials=creds)
    channel_id = str(uuid.uuid4())
    body = {
        "id": channel_id,
        "type": "webhook",
        "address": webhook_url,
    }
    watch = drive.files().watch(fileId=folder_id, body=body).execute()
    print(f"Registered webhook for subfolder {folder_id}: {watch}")
    # 2. Store the mapping
    channel_to_folder[watch["id"]] = folder_id
import threading
import time

def refresh_roles_periodically(interval=60):
    """
    Periodically refresh roles and register webhooks for new folders.
    """
    while True:
        print("Refreshing roles and registering webhooks...")
        roles = read_job_role()
        for role in roles:
            folder_id = role["folder_id"]
            register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)
        process_all_roles()
        time.sleep(interval)  # Check every 60 seconds (adjust as needed)

@app.on_event("startup")
def register_all_subfolder_webhooks():
    """
    Register a Drive push notification channel (watch) for each subfolder at startup.
    """
    roles = read_job_role()
    for role in roles:
        folder_id = role["folder_id"]
        register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)
from fastapi import Body

@app.post("/refresh_roles")
async def refresh_roles(payload: dict = Body(...)):
    print("Received /refresh_roles POST request with payload:", payload)
    folder_id = payload.get("folder_id")
    job_title = payload.get("title")
    responsibilities = payload.get("responsibilities")

    # Only proceed if all fields are present and non-empty
    if not (folder_id and job_title and responsibilities):
        return {"status": "error", "message": "Missing folder_id, title, or responsibilities in payload"}

    # Register webhook for this new folder if not already registered
    if folder_id not in channel_to_folder.values():
        register_webhook_for_subfolder(folder_id, DRIVE_WEBHOOK_URL)

    files = get_files_in_folder(folder_id)
    if not files:
        print(f"No resumes found for {job_title}")
        return {"status": f"No resumes found for {job_title}"}

    for file in files:
        print(f"Processing file: {file['name']} (ID: {file['id']})")
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
        result = app_workflow.invoke(state)
        matches = result.get("matches", [])
        write_results_to_results_tab(job_title, matches)
        for match in matches:
            store_result(job_title, match)

    return {"status": f"Processed all files for {job_title}"}

PROCESSED_FILES = set()  
@app.post("/webhook/drive")
async def google_drive_webhook(
    request: Request,
    x_goog_channel_id: str = Header(None),
    x_goog_resource_state: str = Header(None),
    x_goog_resource_id: str = Header(None),
    x_goog_message_number: str = Header(None),
):
    print("\n🔔 Webhook Triggered")
    print("Channel ID:", x_goog_channel_id)
    print("Resource State:", x_goog_resource_state)
    print("Resource ID:", x_goog_resource_id)
    print("Message Number:", x_goog_message_number)

    if x_goog_resource_state not in ("add", "update"):
        print("Ignored: Not a new file upload or update.")
        return JSONResponse(content={"status": "ignored"})

    try:
        # Use the channel_to_folder mapping to get the correct folder_id
        folder_id = channel_to_folder.get(x_goog_channel_id)
        if not folder_id:
            print("No matching folder found for this webhook event.")
            return JSONResponse(content={"status": "no matching folder"})

        roles = read_job_role()
        job_title = None
        for role in roles:
            if role["folder_id"] == folder_id:
                job_title = role["title"]
                break

        if not job_title:
            print("No matching job title found for this folder.")
            return JSONResponse(content={"status": "no matching job title"})

        # Get the latest file in the folder
        creds = get_google_credentials()
        drive = build("drive", "v3", credentials=creds)
        results = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            orderBy="createdTime desc",
            pageSize=1
        ).execute()
        files = results.get("files", [])
        if not files:
            print("No files found in folder.")
            return JSONResponse(content={"status": "no files in folder"})

        latest_file = files[0]
        print(f"Processing file: {latest_file['name']} (ID: {latest_file['id']})")

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
        result = app_workflow.invoke(state)
        matches = result.get("matches", [])
        write_results_to_results_tab(job_title, matches)
        for match in matches:
            store_result(job_title, match)
        return JSONResponse(content={"status": "processed latest file"})
    except Exception as e:
        print("❌ Error during processing file:", e)
        traceback.print_exc()
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)