# app/services/context_builder.py
from typing import Dict, List, Any

# This function must be defined here, before it is called by build_context_and_prompt.
def format_tech_for_context(tech: Dict) -> str:
    """Creates a clean, readable text block from a technology JSON object for the LLM."""
    innovators = ", ".join([i.get('name', 'N/A') for i in tech.get('innovators', [])])
    advantages = ", ".join(tech.get('advantages', []))
    applications = ", ".join(tech.get('applications', []))
    use_cases = ", ".join(tech.get('useCases', []))
    
    return f"""---
Technology Name: {tech.get('name', 'N/A')}
Docket ID: {tech.get('docket', 'N/A')}
Description: {tech.get('detailedDescription') or tech.get('overview') or tech.get('description', 'N/A')}
Domain/Genre: {tech.get('genre', 'N/A')}
Key Advantages: {advantages or 'N/A'}
Potential Applications: {applications or 'N/A'}
Example Use Cases: {use_cases or 'N/A'}
Lead Innovators: {innovators or 'N/A'}
TRL: {tech.get('trl', 'N/A')}
Patent Status: {tech.get('patent', 'N/A')}
---"""

def build_context_and_prompt(intent_data: Dict, all_technologies: List[Dict]) -> Dict[str, str]:
    """
    Builds the context string and the system prompt for the final LLM call
    based on the detected intents.
    """
    context_parts = []
    
    intents = intent_data.get("intents", [])
    
    has_tech_query = any(intent['type'] == 'tech_query' for intent in intents)
    has_trl_assessment = any(intent['type'] == 'trl_assessment' for intent in intents)
    
    # --- Part 1: Build Context from Data ---
    if has_tech_query:
        found_techs = set() # Use a set to avoid duplicate tech entries
        for intent in intents:
            if intent['type'] == 'tech_query':
                entities = intent.get('entities', {})
                name_query = entities.get('name', '').lower().strip()
                genre_query = entities.get('genre', '').lower().strip()
                
                # Fix for handling keywords as either a list or a string
                keyword_entity = entities.get('keywords', []) 
                if isinstance(keyword_entity, list):
                    keyword_query = " ".join(keyword_entity).lower().strip()
                else:
                    keyword_query = str(keyword_entity).lower().strip()

                for tech in all_technologies:
                    # Create searchable text fields for each technology
                    tech_name = tech.get('name', '').lower()
                    tech_desc = tech.get('description', '').lower()
                    tech_genre = tech.get('genre', '').lower()
                    tech_apps = ' '.join(tech.get('applications', [])).lower()
                    tech_use_cases = ' '.join(tech.get('useCases', [])).lower()
                    
                    # Match by name (most specific)
                    if name_query and name_query in tech_name:
                        found_techs.add(tech['id'])
                        continue # Prioritize direct name matches

                    # Match by genre
                    if genre_query and genre_query in tech_genre:
                        found_techs.add(tech['id'])
                    
                    # Match by keyword in various text fields
                    if keyword_query:
                        if (keyword_query in tech_desc or 
                            keyword_query in tech_apps or
                            keyword_query in tech_use_cases or
                            keyword_query in tech_name):
                            found_techs.add(tech['id'])

        if found_techs:
            context_parts.append("CONTEXT ON AVAILABLE TECHNOLOGIES:")
            techs_to_add = [tech for tech in all_technologies if tech['id'] in list(found_techs)[:5]]
            for tech in techs_to_add:
                # This call now works because the function is defined above
                context_parts.append(format_tech_for_context(tech))
    
    # --- Part 2: Construct the Final System Prompt ---
    system_prompt_parts = [
        """You are "Tech-Transfer Pal", a friendly and professional AI assistant for the Office of Tech-Transfer and Management (OTMT) at IIIT-Delhi. Your primary purpose is to answer questions about OTMT, its processes, and its technologies, and to help users assess the TRL of new ideas. 
        About IIIT-Delhi (Indraprastha Institute of Information Technology, Delhi):
IIIT-Delhi is an autonomous state university located in Delhi, India, established by the Government of NCT of Delhi.
It is a research-oriented university focused on education and research in Information Technology and allied areas such as Computer Science, Electronics & Communications, Computational Biology, Artificial Intelligence, Design, and Digital Humanities.
IIIT-Delhi aims to be a global center of excellence in IT education, research, and development, fostering innovation and entrepreneurship.

About OTMT (Office of Technology Management and Transfer):
The Office of Technology Management and Transfer (OTMT) at IIIT-Delhi is dedicated to facilitating the protection, management, and commercialization of intellectual property (IP) generated from research activities within the institute.
Key functions of OTMT include:
- Promoting IP awareness and education among faculty, staff, and students.
- Assisting researchers in the invention disclosure process and evaluating patentability.
- Managing the institute's IP portfolio, including patents, copyrights, and designs.
- Facilitating technology licensing and transfer to industry for societal and economic benefit.
- Supporting startups and spin-offs incubated at IIIT-Delhi with IP-related matters.
- Fostering collaborations between academia and industry to translate research into practical applications.
- Conducting due diligence and market assessment for institute technologies.

Key Contact for Licensing and Related Doubts:
For inquiries regarding technology licensing, collaborations, or other specific doubts related to technology transfer, please contact:
Mr. Alok Nikhil Jha
Email: alok@iiitd.ac.in
        """
    ]
    
    if has_tech_query:
        if context_parts:
             system_prompt_parts.append("\n\nINSTRUCTION: Use the provided 'CONTEXT ON AVAILABLE TECHNOLOGIES' to answer the user's technology-related questions. Do not use outside knowledge for this. If the answer is not in the context, say so.")
        else:
            system_prompt_parts.append("\n\nINSTRUCTION: You were asked about technologies but could not find a match in the database. Inform the user and ask them to clarify or try searching by a different domain (e.g., AI, CV, Health).")

    if has_trl_assessment:
        system_prompt_parts.append("\n\nINSTRUCTION: The user wants to assess the TRL of a new project. Guide them through the process by asking relevant questions to determine their stage of development from TRL 1 to 9.")

    system_prompt_parts.append("\n\nRULE: Always be helpful, professional, and stay on topic. Do not provide legal advice. If you don't know an answer, say so and suggest contacting Mr. Alok Nikhil Jha.")
    
    final_system_prompt = "".join(system_prompt_parts)
    final_context = "\n".join(context_parts)
    
    return {"system_prompt": final_system_prompt, "context": final_context}