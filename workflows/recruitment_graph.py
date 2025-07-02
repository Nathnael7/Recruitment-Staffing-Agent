from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from typing import TypedDict

from agents.job_loader       import load_job_role
from agents.culture_loader   import load_culture_doc
from agents.resume_fetcher   import get_resume_files
from agents.resume_parser    import parse_resume
from agents.resume_matcher   import match_resumes
from agents.result_writer    import output_results

class StateSchema(TypedDict):
    job: dict
    culture: str
    resumes: list
    parsed_resumes: list
    matches: list

def build_graph():
    wf = StateGraph(state_schema=StateSchema)
    wf.add_node("LoadJobRole",    RunnableLambda(load_job_role))
    wf.add_node("LoadCulture",    RunnableLambda(load_culture_doc))
    wf.add_node("GetResumes",     RunnableLambda(get_resume_files))
    wf.add_node("ParseResumes",   RunnableLambda(parse_resume))
    
    wf.add_node("MatchResumes",   RunnableLambda(match_resumes))
    wf.add_node("OutputResults",  RunnableLambda(output_results))

    wf.set_entry_point("LoadJobRole")
    wf.add_edge("LoadJobRole", "LoadCulture")
    wf.add_edge("LoadCulture", "GetResumes")
    wf.add_edge("GetResumes", "ParseResumes")
    wf.add_edge("ParseResumes", "MatchResumes")
    wf.add_edge("MatchResumes", "OutputResults")
    wf.add_edge("OutputResults", END)

    return wf.compile()
