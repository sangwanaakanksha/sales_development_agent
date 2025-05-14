# utils/guardrail.py
import os
import logging
from langchain_openai import OpenAI # Updated import

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize LLM once if possible, or ensure API key is available
try:
    llm = OpenAI(temperature=0.2, model_name="gpt-3.5-turbo-instruct") # Using a slightly more capable model for refinement
except Exception as e:
    logger.error(f"Failed to initialize OpenAI LLM for guardrail: {e}. Ensure OPENAI_API_KEY is set.")
    llm = None

def refine_outreach_message(original_message: str, company_name: str, company_description: str, event_name: str = "ISA Sign Expo 2025") -> str:
    """
    Refines a given outreach message using an LLM to make it more natural,
    corrective, and ensure it's appropriate.
    Defaults to a generic safe message if refinement fails or input is problematic.
    """
    if not llm:
        logger.warning("Guardrail LLM not initialized. Returning original message or a generic one.")
        if "My Planner" in original_message or len(original_message) < 50 : # Crude check for bad generation
             return f"Dear team at {company_name},\n\nIt was a pleasure to learn about your work in relation to {event_name}. We are impressed with your company and would be keen to explore potential synergies.\n\nBest regards,\n[Your Name/Company]"
        return original_message

    # Clean up common boilerplate from description if it slipped through
    cleaned_description = company_description.replace("My Planner", "").replace("My Profile", "").replace("Recommendations", "").replace("Sign Out", "").strip()
    if not cleaned_description or len(cleaned_description) < 20: # If description is too short or junk
        description_context = f"their presence at {event_name}"
    else:
        description_context = f"their work in '{cleaned_description[:100].strip().rstrip('.')}' showcased around {event_name}"


    prompt_template = f"""
    You are an expert sales development representative.
    Your task is to refine an initial draft of an outreach email.
    The goal is to make it sound natural, engaging, and professional.
    It should imply a positive interaction or observation related to {event_name}.

    Original company description context: "{description_context}"
    Company Name: {company_name}

    Initial Draft:
    "{original_message}"

    Refinement Instructions:
    1. Rewrite the message to be more conversational and engaging.
    2. Start with a warm opening, such as "It was a pleasure connecting with your team at {event_name}," or "Following the insightful discussions at {event_name}," or "Inspired by your presence at {event_name},".
    3. Ensure the message refers to the company's work or focus, using the provided description context if it's meaningful. If the description context seems like boilerplate or is unhelpful (e.g., just navigation text), then make a more general positive statement about the company.
    4. Remove any awkward phrasing, code snippets, or placeholder text like "[Your Name/Company]" from the body (the signature will be added later).
    5. Ensure the tone is polite, professional, and expresses genuine interest.
    6. If the initial draft is nonsensical, contains JavaScript, or is clearly just boilerplate HTML text, discard it and generate a new, concise, and appropriate message based on the company name and the event. A generic good message would be: "It was great to learn about {company_name} in the context of {event_name}. We're impressed with your company's focus and see potential for collaboration. Would you be open to a brief chat?"
    7. The refined message should be just the email body, without "Subject:", "Dear...", or a signature block.

    Refined Message (email body only):
    """

    try:
        refined_text = llm.invoke(prompt_template).strip()
        
        # Basic safety/quality checks on LLM output
        if not refined_text or len(refined_text) < 30 or "My Planner" in refined_text: # crude check for bad refinement
            logger.warning(f"Refinement for {company_name} resulted in a problematic message. Using generic fallback.")
            return f"It was great to learn about {company_name} in the context of {event_name}. We're impressed with your company's focus and see potential for collaboration. Would you be open to a brief chat?"
        return refined_text
    except Exception as e:
        logger.error(f"Error during guardrail LLM call for {company_name}: {e}")
        # Fallback to a very generic message if LLM refinement fails
        return f"It was great to learn about {company_name} in the context of {event_name}. We're impressed with your company's focus and see potential for collaboration. Would you be open to a brief chat?"

if __name__ == "__main__":
    # Test the guardrail
    test_bad_message = "Hi team at TestCorp,\n\nNoticed TestCorp from the ISA Sign Expo exhibitor list. Your focus on 'My Planner My Profile Recommendations Sign Out...' particularly stood out.\n\nBest regards,\n[Your Name/Company]"
    test_company = "TestCorp"
    test_description = "My Planner My Profile Recommendations Sign Out"
    
    print("Testing with bad description:")
    refined = refine_outreach_message(test_bad_message, test_company, test_description)
    print(f"Original:\n{test_bad_message}\nRefined:\n{refined}")

    print("\nTesting with decent description:")
    test_good_description = "innovative digital displays"
    test_good_message = f"Hi team at {test_company},\n\nYour work in '{test_good_description}' caught my eye. Would be great to connect."
    refined_good = refine_outreach_message(test_good_message, test_company, test_good_description)
    print(f"Original:\n{test_good_message}\nRefined:\n{refined_good}")

    print("\nTesting with nonsensical message (simulating JS code):")
    test_js_message = "function parse_query_string(query) { var vars = query.split('&');"
    refined_js = refine_outreach_message(test_js_message, "JS Corp", "Data Analytics")
    print(f"Original:\n{test_js_message}\nRefined:\n{refined_js}")