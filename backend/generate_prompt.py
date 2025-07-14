from pathlib import Path
import csv

def load_file(file_path):
    return Path(file_path).read_text().strip()

def load_vocabulary(csv_path):
    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader: #the file holds everything in a single row
            return row
            
def generate_prompt():
    intro_system_role_text = load_file("intro_prompt.txt")
    vocab_list = load_vocabulary("vocab.csv")
    vocab_text =",".join(vocab_list)
    vocab_section = f"Here is an example list of vocabulary words for a 2nd or 3rd grader: {vocab_text} "
    story_steps_text = load_file("story_steps_prompt.txt")
    full_prompt = "\n".join([intro_system_role_text,vocab_section,story_steps_text])
    return(full_prompt)

def generate_fun_facts_prompt(scenario, topic=None, fact_number=None, previous_facts=None):
    """
    Generate prompts for fun facts mode using external prompt files
    
    Args:
        scenario: 'first_fact', 'continuing_fact', or 'new_topic'
        topic: The topic for the fun fact
        fact_number: Current fact number (for continuing facts)
        previous_facts: String of previous facts to avoid repeating
    
    Returns:
        Complete prompt ready for LLM
    """
    # Load engaging content instructions
    instructions = load_file("fun_facts_instructions.txt")
    
    # Load base prompt templates
    base_prompts_text = load_file("fun_facts_base_prompts.txt")
    
    # Parse the base prompts file to extract templates
    base_prompts = {}
    current_key = None
    current_content = []
    
    for line in base_prompts_text.split('\n'):
        if line.endswith(':') and line.count(':') == 1:
            # Save previous prompt if exists
            if current_key:
                base_prompts[current_key] = '\n'.join(current_content).strip()
            # Start new prompt
            current_key = line[:-1]  # Remove the colon
            current_content = []
        elif current_key:
            current_content.append(line)
    
    # Save the last prompt
    if current_key:
        base_prompts[current_key] = '\n'.join(current_content).strip()
    
    # Select appropriate template based on scenario
    template_map = {
        'first_fact': 'FIRST_FACT_PROMPT',
        'continuing_fact': 'CONTINUING_FACT_PROMPT', 
        'new_topic': 'NEW_TOPIC_PROMPT'
    }
    
    template_key = template_map.get(scenario, 'FIRST_FACT_PROMPT')
    base_prompt = base_prompts.get(template_key, '')
    
    # Format the template with provided variables
    if scenario == 'continuing_fact':
        base_prompt = base_prompt.format(
            topic=topic or '',
            fact_number=fact_number or 1,
            previous_facts=previous_facts or 'None'
        )
    else:
        base_prompt = base_prompt.format(topic=topic or '')
    
    # Combine instructions with the specific prompt
    full_prompt = f"{instructions}\n\n{base_prompt}"
    
    return full_prompt

if __name__ == "__main__":
    print(generate_prompt())
