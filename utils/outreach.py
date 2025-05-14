# utils/outreach.py
import random # Not strictly needed anymore if guardrail handles all variations
import logging
from .guardrail import refine_outreach_message 

logger = logging.getLogger(__name__)

def _generate_and_refine_message_for_single_lead(lead_dict: dict, user_signature: str, event_name: str = "ISA Sign Expo 2025", user_name_for_signature: str = "Our Team") -> str:
    """
    Prepares data and calls the guardrail LLM to generate and refine an outreach message.
    """
    company_name = lead_dict.get("name", "your company")
    # The description from search.py should be cleaner now
    description = lead_dict.get("description", "") 

    # The 'original_message_context' is minimal as the guardrail prompt is now more directive.
    initial_concept = f"Follow-up after seeing {company_name} at {event_name} regarding {description[:70]}..."

    # Call the guardrail to generate and refine the message body
    refined_body = refine_outreach_message(
        original_message_context=initial_concept, # Context for the LLM
        company_name=company_name,
        company_description=description, # Pass the (hopefully cleaner) description
        event_name=event_name,
        user_name_for_signature=user_name_for_signature
    )
    
    return f"{refined_body}{user_signature}"


def generate_outreach(leads_list: list, user_signature: str, user_name_for_signature: str, event_name: str = "ISA Sign Expo 2025") -> list:
    if not isinstance(leads_list, list):
        logger.error("generate_outreach expects a list of leads. Received: %s", type(leads_list))
        return [] 

    updated_leads = []
    for lead_item in leads_list:
        if not isinstance(lead_item, dict):
            logger.warning(f"Item in leads_list is not a dictionary, skipping: {type(lead_item)}")
            continue
        
        lead_copy = lead_item.copy()
        lead_copy["outreach_message"] = _generate_and_refine_message_for_single_lead(
            lead_copy, 
            user_signature, 
            event_name,
            user_name_for_signature
        )
        updated_leads.append(lead_copy)
    return updated_leads

if __name__ == "__main__":
    try:
        from .guardrail import refine_outreach_message
    except ImportError:
        print("WARNING: utils.guardrail.refine_outreach_message not found. Using a mock for testing outreach.py.")
        def refine_outreach_message(original_message_context, company_name, company_description, event_name, user_name_for_signature):
            return (f"It was a pleasure to learn about {company_name} regarding {event_name}. "
                    f"Context: {original_message_context} (mock refined by {user_name_for_signature}) "
                    f"Description hint: {company_description[:50]}")

    print("--- Testing outreach.py ---")
    dummy_user_name = "Alex Test"
    dummy_sig = f"\n\nBest regards,\n{dummy_user_name}\nTest Corp Inc."
    
    dummy_leads_data = [
        {"name": "Alpha Signs", "description": "Cutting-edge digital billboards and displays.", "raw_contacts_text": "Sarah VP, Sales Director John"},
        {"name": "Beta Wraps", "description": "Custom vehicle wraps and fleet graphics. My Planner My Profile", "raw_contacts_text": "Mike (Technician)"},
        {"name": "Gamma Prints", "description": "Large format printing services for events."},
        {"name": "Delta Corp", "description": "function parseIt() { return 'bad stuff'; }", "raw_contacts_text": "Hacker"}
    ]
        
    leads_with_messages = generate_outreach(dummy_leads_data, dummy_sig, dummy_user_name, event_name="Test Expo 2024")
    
    print(f"\nProcessed {len(leads_with_messages)} leads/items:")
    for i, lead in enumerate(leads_with_messages):
      if isinstance(lead, dict):
        print(f"\n--- Lead {i+1}: {lead.get('name')} ---")
        print(f"Original Description: {lead.get('description')}")
        print(f"Outreach Message:\n{lead.get('outreach_message')}")
      else:
        print(f"\n--- Skipped Non-Dict Item {i+1} ---")
        print(lead)
    print("-" * 30)

 
 
 

# utils/outreach.py
# import random
# import logging
# from .guardrail import refine_outreach_message 

# logger = logging.getLogger(__name__)

# def _generate_initial_draft_for_single_lead(lead_dict: dict, event_name: str = "ISA Sign Expo 2025") -> str:
#     """
#     Generates a basic initial draft outreach message for a single lead dictionary.
#     This draft will be passed to the guardrail LLM for refinement.
#     """
#     company_name = lead_dict.get("name", "your company")
#     # The description might still contain "My Planner..." or other noise if search.py didn't fully clean it.
#     # The guardrail prompt is designed to handle this.
#     description = lead_dict.get("description", "their interesting work at the event") 
    
#     # Provide a simple, information-rich draft.
#     # The guardrail LLM will be instructed to rephrase the opening (e.g., "It was a pleasure...")
#     # and to use the description contextually.
#     initial_draft_body = (
#         f"Our team was particularly interested in {company_name} during {event_name}, "
#         f"especially regarding their work related to '{description[:150].strip().rstrip('.')}...'. "
#         f"We believe there could be strong potential for collaboration."
#     )
#     return initial_draft_body

# def generate_outreach_messages(leads_list: list, user_signature: str, event_name: str = "ISA Sign Expo 2025") -> list:
#     """
#     Takes a list of lead dictionaries, generates an initial draft message,
#     refines it using a guardrail LLM, and adds the final outreach_message to each.
#     This is the function that should be called from enrichment.py.
#     """
#     if not isinstance(leads_list, list):
#         logger.error("generate_outreach_messages expects a list of leads. Received: %s", type(leads_list))
#         return [] # Return empty list or raise error

#     updated_leads = []
#     for lead_item in leads_list:
#         if not isinstance(lead_item, dict):
#             logger.warning(f"Item in leads_list is not a dictionary, skipping: {type(lead_item)}")
#             # updated_leads.append(lead_item) # Optionally pass through non-dict items
#             continue
        
#         lead_copy = lead_item.copy()
        
#         company_name_for_refinement = lead_copy.get("name", "the company")
#         description_for_refinement = lead_copy.get("description", "their work")

#         initial_draft = _generate_initial_draft_for_single_lead(lead_copy, event_name)
        
#         # Call the guardrail to refine this initial draft.
#         refined_body = refine_outreach_message(
#             original_message=initial_draft,
#             company_name=company_name_for_refinement,
#             company_description=description_for_refinement,
#             event_name=event_name
#         )
        
#         # Append the user's signature to the refined body
#         lead_copy["outreach_message"] = f"{refined_body}{user_signature}"
#         updated_leads.append(lead_copy)
        
#     return updated_leads

# # Renamed the main function that enrichment.py calls to be more descriptive
# # If your enrichment.py still calls `generate_outreach`, you can rename this function
# # back to `generate_outreach` or update the call in enrichment.py
# # For clarity with the previous conversation, I'll keep it as `generate_outreach`
# # to match what enrichment.py was likely calling.

# def generate_outreach(leads_list: list, user_signature: str, event_name: str = "ISA Sign Expo 2025") -> list:
#     return generate_outreach_messages(leads_list, user_signature, event_name)


# if __name__ == "__main__":
#     # This section is for direct testing of outreach.py
#     # You'll need to have a utils/guardrail.py with a mock or real refine_outreach_message for this test to run.
#     # For now, let's create a mock guardrail for testing purposes if utils.guardrail doesn't exist
#     try:
#         from .guardrail import refine_outreach_message
#     except ImportError:
#         print("WARNING: utils.guardrail.refine_outreach_message not found. Using a mock for testing outreach.py.")
#         def refine_outreach_message(original_message, company_name, company_description, event_name):
#             # Mock refinement: just appends "(refined)" and uses a standard opening
#             return f"It was a pleasure to learn about {company_name} regarding {event_name}.\n{original_message} (mock refined)"

#     print("--- Testing outreach.py ---")
#     dummy_sig = "\n\nBest regards,\nTest User\nTest Corp"
    
#     dummy_leads_data = [
#         {"name": "Alpha Signs", "description": "Cutting-edge digital billboards and displays.", "raw_contacts_text": "Sarah VP, Sales Director John"},
#         {"name": "Beta Wraps", "description": "Custom vehicle wraps and fleet graphics. My Planner My Profile", "raw_contacts_text": "Mike (Technician)"},
#         {"name": "Gamma Prints", "description": "Large format printing services for events."}, # No raw_contacts_text
#         {"name": "Delta Corp", "description": "function parseIt() { return 'bad stuff'; }", "raw_contacts_text": "Hacker"}
#     ]
    
#     # Add a non-dict item to test robustness
#     dummy_leads_data_with_error = dummy_leads_data + ["This is not a dict", None]
    
#     leads_with_messages = generate_outreach(dummy_leads_data_with_error, dummy_sig, event_name="Test Expo 2024")
    
#     print(f"\nProcessed {len(leads_with_messages)} leads/items:")
#     for i, lead in enumerate(leads_with_messages):
#       if isinstance(lead, dict):
#         print(f"\n--- Lead {i+1}: {lead.get('name')} ---")
#         print(f"Original Description: {lead.get('description')}")
#         print(f"Outreach Message:\n{lead.get('outreach_message')}")
#       else:
#         print(f"\n--- Skipped Non-Dict Item {i+1} ---")
#         print(lead)
#     print("-" * 30)