from langchain.llms import OpenAI

def judge_message(message: dict):
    """
    Guardrail: check for hallucinations, toxicity, phishing tone.
    Returns 'OK' or JSON list of issues.
    """
    llm = OpenAI(temperature=0)
    check = (
        "Evaluate this message for hallucinated facts, toxicity/profanity, "
        "or phishing style. Return 'OK' if clean, otherwise JSON list of issues."
    )
    prompt = check + "\n\nMessage:\n" + str(message)
    return llm(prompt)
