from googleapiclient.discovery import build
from services.auth import get_google_credentials
from config.settings import GOOGLE_SHEET_ID

def get_sheets_service():
    creds = get_google_credentials()
    return build('sheets', 'v4', credentials=creds)

def read_job_role():
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
    return roles
def write_results_to_results_tab(job_title, matches):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    SHEET_NAME = "Results"
    RANGE = f"{SHEET_NAME}!A:E"

    # Ensure header exists
    # header = ["Candidate", "Score", "Status", "Email", "Job Title"]
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
        sheet.values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=RANGE,
            valueInputOption="RAW",
            body={"values": [[name, score, status, email, job_title]]}
        ).execute()


