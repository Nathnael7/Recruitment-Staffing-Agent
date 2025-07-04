from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from typing import TypedDict

from agents.job_loader       import load_job_role
from agents.culture_loader   import load_culture_doc
from agents.resume_fetcher   import get_resume_files
from agents.resume_parser    import parse_resume
from agents.resume_matcher   import match_resumes
from agents.result_writer    import output_results

# Define the schema for the workflow state
class StateSchema(TypedDict):
    job: dict
    culture: str
    resumes: list
    parsed_resumes: list
    matches: list

def build_graph():
    # Create a new stateful workflow graph with the defined schema
    wf = StateGraph(state_schema=StateSchema)
    
    # Add nodes for each workflow step, wrapping each function as a runnable
    wf.add_node("LoadJobRole",    RunnableLambda(load_job_role))      # Load job role information
    wf.add_node("LoadCulture",    RunnableLambda(load_culture_doc))   # Load company culture document
    wf.add_node("GetResumes",     RunnableLambda(get_resume_files))   # Fetch resume files
    wf.add_node("ParseResumes",   RunnableLambda(parse_resume))       # Parse resumes
    
    wf.add_node("MatchResumes",   RunnableLambda(match_resumes))      # Match parsed resumes to job/culture
    wf.add_node("OutputResults",  RunnableLambda(output_results))     # Output the matching results

    # Set the entry point of the workflow
    wf.set_entry_point("LoadJobRole")
    # Define the order of execution by connecting nodes with edges
    wf.add_edge("LoadJobRole", "LoadCulture")
    wf.add_edge("LoadCulture", "GetResumes")
    wf.add_edge("GetResumes", "ParseResumes")
    wf.add_edge("ParseResumes", "MatchResumes")
    wf.add_edge("MatchResumes", "OutputResults")
    wf.add_edge("OutputResults", END)  # Mark the end of the workflow

    # Compile and return the workflow graph
    return wf.compile()
