from googleapiclient.discovery import build
from services.auth import get_google_credentials
from config.settings import GOOGLE_SHEET_ID
import logging
import os

# Setup logging
log_dir = ".logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "services.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_sheets_service():
    try:
        logging.info("Getting Google Sheets service.")
        creds = get_google_credentials()
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        logging.error("Failed to get Google Sheets service: %s", e, exc_info=True)
        raise

def read_job_role():
    try:
        logging.info("Reading job roles from sheet.")
        svc = get_sheets_service().spreadsheets()
        vals = svc.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Roles!A2:C"
        ).execute().get("values", [])
        roles = []
        for row in vals:
            if len(row) >= 3:
                roles.append({
                    "title": row[0],
                    "responsibilities": row[1],
                    "folder_id": row[2]
                })
        logging.info("Successfully read %d job roles.", len(roles))
        return roles
    except Exception as e:
        logging.error("Error reading job roles: %s", e, exc_info=True)
        raise

def write_results_to_results_tab(job_title, matches):
    try:
        logging.info("Writing results to Results tab for job title: %s", job_title)
        service = get_sheets_service()
        sheet = service.spreadsheets()
        SHEET_NAME = "Results"
        RANGE = f"{SHEET_NAME}!A:E"

        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{SHEET_NAME}!A1:E"
        ).execute()
        values = result.get("values", [])[1:]  

        spreadsheet = sheet.get(spreadsheetId=GOOGLE_SHEET_ID).execute()
        sheet_id = next(s['properties']['sheetId'] for s in spreadsheet['sheets'] if s['properties']['title'] == SHEET_NAME)

        for match in matches:
            name = match["name"]
            score = match["score"]
            status = match.get("status", "")
            email = match.get("email", "").strip().lower()
            jt = job_title.strip().lower()

            rows_to_delete = []
            for idx, row in enumerate(values):
                row_email = row[3].strip().lower() if len(row) > 3 else ""
                row_jt = row[4].strip().lower() if len(row) > 4 else ""
                if row_email == email and row_jt == jt:
                    rows_to_delete.append(idx + 2)  

            for row_idx in reversed(rows_to_delete):
                logging.info("Deleting duplicate row at index %d for email/job_title.", row_idx)
                sheet.batchUpdate(
                    spreadsheetId=GOOGLE_SHEET_ID,
                    body={
                        "requests": [
                            {
                                "deleteDimension": {
                                    "range": {
                                        "sheetId": sheet_id,
                                        "dimension": "ROWS",
                                        "startIndex": row_idx - 1,
                                        "endIndex": row_idx
                                    }
                                }
                            }
                        ]
                    }
                ).execute()

            # Append the new result
            logging.info("Appending result for candidate: %s, job title: %s", name, job_title)
            sheet.values().append(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=RANGE,
                valueInputOption="RAW",
                body={"values": [[name, score, status, email, job_title]]}
            ).execute()
        logging.info("Finished writing results for job title: %s", job_title)
    except Exception as e:
        logging.error("Error writing results to Results tab: %s", e, exc_info=True)
        raise

