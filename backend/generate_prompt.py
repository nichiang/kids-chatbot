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

if __name__ == "__main__":
    print(generate_prompt())
