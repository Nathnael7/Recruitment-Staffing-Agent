from workflows.recruitment_graph import build_graph

if __name__ == "__main__":
    app = build_graph()
    result = app.invoke({})
    print("Done:", result)