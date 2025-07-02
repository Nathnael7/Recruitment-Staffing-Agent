import os
import fitz    # PyMuPDF
import docx
import textract
import spacy
from services.drive import download_file

nlp = spacy.load("en_core_web_sm")

def parse_resume(state):
    os.makedirs("tmp", exist_ok=True)
    parsed = []

    for file in state["resumes"]:
        fid, name = file["id"], file["name"]
        path = f"tmp/{name}"
        download_file(fid, path)

        text = ""
        try:
            if name.endswith(".pdf"):
                with fitz.open(path) as d:
                    text = "\n".join(p.get_text() for p in d)

            elif name.endswith(".docx"):
                d = docx.Document(path)
                text = "\n".join(p.text for p in d.paragraphs)
                for tbl in d.tables:
                    for row in tbl.rows:
                        for cell in row.cells:
                            text += "\n" + cell.text

            elif name.endswith(".doc"):
                text = textract.process(path).decode("utf-8")

            else:
                print(f"[Warning] Unsupported file type: {name}")

        except Exception as e:
            print(f"[Error] Parsing {name}: {e}")

        doc_nlp = nlp(text)
        skills = [ent.text for ent in doc_nlp.ents if ent.label_ == "SKILL"]

        parsed.append({
            "name": name,
            "text": text,
            "skills": skills
        })

    return {"parsed_resumes": parsed}
