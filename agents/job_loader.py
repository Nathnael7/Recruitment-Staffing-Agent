from services.sheets import read_job_role

def load_job_role(state):
    # Just return the job already in state
    return {"job": state["job"]}
