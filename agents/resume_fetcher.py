from services.drive import list_resumes
import logging
import os

# Setup logging
log_dir = ".logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "agents.log")
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_resume_files(state):
    # If resumes already provided (from webhook), don't fetch all files again
    if state.get("resumes"):
        return {"resumes": state["resumes"]}
    folder_id = state["job"]["folder_id"]
    resumes = list_resumes(folder_id)
    logging.info(f"Fetched {len(resumes)} resumes from folder {folder_id}")
    return {"resumes": resumes}