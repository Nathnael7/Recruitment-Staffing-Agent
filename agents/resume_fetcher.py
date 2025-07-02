from services.drive import list_resumes

def get_resume_files(state):
    # If resumes already provided (from webhook), don't fetch all files again
    if state.get("resumes"):
        return {"resumes": state["resumes"]}
    folder_id = state["job"]["folder_id"]
    resumes = list_resumes(folder_id)
    return {"resumes": resumes}