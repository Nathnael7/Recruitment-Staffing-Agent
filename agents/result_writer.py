from services.sheets import write_results_to_results_tab

def output_results(state):
    job_title = state["job"]["title"]
    write_results_to_results_tab(job_title, state["matches"])
    return {"done": True}
