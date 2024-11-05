import os
import streamlit as st
import json
import openAiKey
from openai import OpenAI

client = OpenAI()

from datetime import datetime
from rapidfuzz import process

# Load JSON data
def load_json(file_path):
    with open(file_path) as f:
        return json.load(f)

patent_data = load_json('patents.json')
company_data = load_json('company_products.json')
patent_id = st.text_input('Please enter Patent ID')
company_name = st.text_input('Please enter Company Name')
# Define the load_reports function
def load_reports():
    try:
        with open('saved_reports.json') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []  # Return an empty list if the file is empty or contains invalid JSON
    except FileNotFoundError:
        return []  # Return an empty list if the file does not exist

# Define the save_report function
def save_report(report):
    reports = load_reports()
    reports.append(report)
    with open('saved_reports.json', 'w') as f:
        json.dump(reports, f, indent=4)

def fuzzy_search(query, choices):
    # Extract the best match, which includes match, score, and index
    result = process.extractOne(query, choices)
    if result:
        best_match, score, _ = result  # Unpack match, score, ignore index
        return best_match, score
    return None, 0  # Return None if no match is found

# Helper function to find patent by ID with fuzzy matching
def find_patent_by_id(patent_id):
    patent_ids = [p["publication_number"] for p in patent_data]
    best_match, score = fuzzy_search(patent_id, patent_ids)
    return next((p for p in patent_data if p["publication_number"] == best_match), None)

# Helper function to find company by name with fuzzy matching
def find_company_by_name(company_name):
    company_names = [c["name"] for c in company_data["companies"]]
    best_match, score = fuzzy_search(company_name, company_names)
    return next((c for c in company_data["companies"] if c["name"] == best_match), None)

# Function to find "id" using the publication number (patent_id)
def get_id_by_publication_number(publication_number):
    # Search for a patent with the specified publication number
    patent = next((p for p in patent_data if p["publication_number"] == publication_number), None)
    if patent:
        return patent["id"]  # Return the "id" if a match is found
    return None  # Return None if no match is found

# Enhanced function to find patent by ID or company name
def find_patent_and_id(patent_id, company_name):
    # First, try to find the company
    company = find_company_by_name(company_name)
    if not company:
        return None, None, None

    # If company is found, try to find the patent within the company's products
    patent = find_patent_by_id(patent_id)
    if not patent:
        # If patent is not found, try to find a patent related to the company
        for product in company["products"]:
            potential_patent = find_patent_by_id(product["name"])
            if potential_patent:
                return potential_patent, company, get_id_by_publication_number(potential_patent["publication_number"])
        return None, company, None

    return patent, company, get_id_by_publication_number(patent["publication_number"])

# Set OpenAI API key
os.environ['OPENAI_API_KEY'] = openAiKey.OPENAI_API_KEY

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

if st.button("Check Infringement") and patent_id and company_name:
    patent, company, analysis_id = find_patent_and_id(patent_id, company_name)

    if not patent:
        st.error(f"No close match found for Patent ID '{patent_id}'. Please try again.")
    elif not company:
        st.error(f"No close match found for Company '{company_name}'. Please try again.")
    else:
        claims = "\n".join(patent["claims"]) if isinstance(patent["claims"], list) else patent["claims"]
        products = "\n".join([f"{prod['name']}: {prod['description']}" for prod in company["products"]])

        # Define the prompt for OpenAI
        prompt = (
            f"Analyze potential patent infringement. Here is the patent information:\n"
            f"Patent ID: {patent['publication_number']}\n"
            f"Claims:\n{claims}\n\n"
            f"Company: {company['name']}\n"
            f"Products:\n{products}\n\n"
            f"Identify the top two products that might infringe this patent. "
            f"Include:\n- Infringement likelihood\n- Relevant claims\n"
            f"- Explanation of why these claims may be relevant to each product's features\n"
        )       
        
        chat_completion = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5000,
            temperature=0.3
        )

        # Extract and display the generated response
        generated_text = chat_completion["choices"][0]["message"]["content"]

        # Display results
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        result = {
            "analysis_id": analysis_id,
            "patent_id": patent["publication_number"],
            "company_name": company["name"],
            "analysis_date": analysis_date,
            "Infringement Analysis": generated_text
        }

        st.write(result)

        # Add a button to save the report
        if st.button("Save Report"):
            save_report(result)
            st.success("Report saved successfully!")

# Option to view previous reports
st.sidebar.title("Saved Reports")
if st.sidebar.button("Load Reports"):
    saved_reports = load_reports()
    if saved_reports:
        for report in saved_reports:
            st.sidebar.write(report)
    else:
        st.sidebar.write("No saved reports found.")
