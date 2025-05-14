# utils/guardrail.py
import os
import logging
import re
from langchain_openai import OpenAI

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

llm = None
try:
    llm = OpenAI(temperature=0.4, model_name="gpt-3.5-turbo-instruct", max_tokens=250) # Slightly higher temp for more variation
    logger.info("Guardrail LLM (gpt-3.5-turbo-instruct) initialized.")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI LLM for guardrail: {e}. Guardrail will use basic fallbacks.")

def is_description_meaningful(description: str) -> bool:
    """Checks if the description is likely meaningful content vs. boilerplate."""
    if not description or len(description) < 25: # Too short
        return False
    # List of phrases indicating a poor/boilerplate description
    non_descriptive_phrases = [
        "no detailed description available",
        "no available appointments",
        "my planner", "my profile", "sign out",
        "exhibitor details", "more information",
        "javascript:", "function", "error"
    ]
    desc_lower = description.lower()
    for phrase in non_descriptive_phrases:
        if phrase in desc_lower:
            return False
    # Check for at least a few words that are not just common stop words or single characters
    meaningful_words = re.findall(r'\b[a-zA-Z]{3,}\b', description)
    return len(meaningful_words) > 5


def refine_outreach_message(
    original_message_context: str, # This can be a simple trigger phrase or key points
    company_name: str,
    company_description: str,
    event_name: str = "ISA Sign Expo 2025",
    user_name_for_signature: str = "Our Team" # For LLM context, not for direct inclusion
) -> str:
    """
    Refines an outreach message using an LLM, making it more natural and relevant.
    """
    if not llm:
        logger.warning("Guardrail LLM not initialized. Using a template-based fallback message.")
        # Fallback to a simpler template if LLM is not available
        meaningful_desc = is_description_meaningful(company_description)
        desc_snippet = company_description[:100].strip().rstrip('.') + "..." if meaningful_desc else "your work and presence"
        
        return (f"It was a pleasure to learn about {company_name} during {event_name}. "
                f"We were impressed by {desc_snippet} and see potential for collaboration. "
                f"Would you be open to a brief discussion?")

    # Determine if the provided description is useful for personalization
    meaningful_description_available = is_description_meaningful(company_description)
    
    description_for_prompt = ""
    if meaningful_description_available:
        description_for_prompt = f"Their specific focus seems to be on: '{company_description[:200]}'."
    else:
        description_for_prompt = "Their company description from the event page was not very detailed or appeared to be boilerplate."

    prompt = f"""
You are an expert Sales Development Representative, crafting a concise, polite, and engaging outreach email body.
The goal is to initiate a conversation.

Event: {event_name}
Company to Contact: {company_name}
Context about the company (use this to personalize if specific, otherwise make a general positive remark about their presence at the event):
"{description_for_prompt}"

Sender's Name (for context only, do NOT include in the message body): {user_name_for_signature}

Instructions for the refined message body:
1.  **Opening:** Start with a warm, professional opening that feels like a natural follow-up from the event. Examples:
    * "It was great to see {company_name}'s presence at {event_name}."
    * "Following {company_name}'s participation at {event_name}, I was particularly interested in..."
    * "Inspired by your company's showcase at {event_name}..."
    * "Hope you had a successful {event_name}."
2.  **Personalization & Value:**
    * If the company context indicates a specific focus (from "{description_for_prompt}"), briefly and naturally mention it to show genuine interest.
    * If the company context is generic or indicates a poor description, make a more general positive statement about their industry, their presence at the event, or an assumption of their general field based on the event type. For example: "Your company's contributions to the signage industry are noteworthy." or "We were impressed by the innovations showcased by companies like yours at the event."
    * Briefly suggest a potential for collaboration or mutual benefit without being overly salesy.
3.  **Call to Action:** Include a soft and clear call to action. Examples:
    * "Would you be open to a brief introductory call next week to explore this further?"
    * "I'd be happy to share a few ideas on how we might collaborate if you're available for a quick chat."
4.  **Tone:** Professional, respectful, concise, and genuinely interested. Avoid hype or overly casual language.
5.  **Length:** Keep the entire message body relatively short, ideally 3-5 sentences.
6.  **Output Format:** Provide ONLY the email body. Do NOT include "Subject:", "Dear [Name]," or any signature block (e.g., "Best regards..."). The signature will be added separately.
7.  **Crucial - Avoid Junk & Placeholders:** Absolutely NO placeholders like "[Your Name/Company]", "Rationale not extracted", or any HTML/JavaScript remnants like "My Planner", "function parse_query_string". The message must be clean and ready to send (once the signature is appended).

Refined Email Body:
    """

    try:
        refined_text = llm.invoke(prompt).strip()
        
        # Clean common LLM self-correction phrases or conversational fluff
        refined_text = refined_text.replace("Refined Email Body:", "").strip()
        common_llm_openers = ["Here's a refined email body:", "Certainly, here's the refined message:", "Okay, here's a version:"]
        for opener in common_llm_openers:
            if refined_text.startswith(opener):
                refined_text = refined_text[len(opener):].strip()
        
        # Ensure it doesn't end with a signature-like closing if the LLM adds one
        if re.search(r"(Best regards|Sincerely|Thanks),?$", refined_text, re.IGNORECASE):
            refined_text = re.sub(r"(Best regards|Sincerely|Thanks),?$", "", refined_text, flags=re.IGNORECASE).strip()


        if not refined_text or len(refined_text) < 50: # Check for empty or too short response
            logger.warning(f"LLM refinement for {company_name} was too short or empty. Using a more direct generic fallback.")
            desc_snippet = company_description[:70].strip().rstrip('.') + "..." if meaningful_description_available else "your company's work"
            return (f"Following {event_name}, I wanted to reach out regarding {company_name}. "
                    f"We were impressed by {desc_snippet} and see potential for collaboration. "
                    f"Would you be open to a brief discussion?")
        
        logger.info(f"Refined message for {company_name} (first 100 chars): {refined_text[:100]}...")
        return refined_text
    except Exception as e:
        logger.error(f"Error during guardrail LLM call for {company_name}: {e}")
        desc_snippet = company_description[:70].strip().rstrip('.') + "..." if meaningful_description_available else "your company's work"
        return (f"Following {event_name}, I wanted to reach out regarding {company_name}. "
                f"We were impressed by {desc_snippet} and see potential for collaboration. "
                f"Would you be open to a brief discussion?")

if __name__ == "__main__":
    print("--- Testing guardrail.py (ensure OPENAI_API_KEY is set) ---")
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. LLM calls in smoke test will likely fail or use mock if implemented.")
    
    test_cases = [
        {"name": "Alpha Innovations", "desc": "Leading provider of AI-driven logistics solutions and advanced robotics for warehouse automation.", "event": "Supply Chain Expo"},
        {"name": "Beta Graphics", "desc": "My Planner My Profile Recommendations Sign Out", "event": "Visual Arts Fair"},
        {"name": "Gamma Tech", "desc": "function parseIt() { return 'bad stuff'; }", "event": "Dev Conference"},
        {"name": "Delta Solutions", "desc": "Provides innovative software for small businesses.", "event": "SMB Summit"},
        {"name": "Epsilon Energy", "desc": "", "event": "Green Energy Forum"}
    ]
    user_name = "Alex Demo"

    for case in test_cases:
        print(f"\n--- Refining for: {case['name']} ---")
        print(f"Original Description: '{case['desc']}'")
        refined_msg_body = refine_outreach_message(
            original_message_context="Initial interest.", # Context for LLM
            company_name=case['name'],
            company_description=case['desc'],
            event_name=case['event'],
            user_name_for_signature=user_name # For LLM context
        )
        final_email = f"{refined_msg_body}\n\nBest regards,\n{user_name}\nDemoCorp"
        print(f"Full Outreach Example:\n{final_email}")
        print("-" * 30)

