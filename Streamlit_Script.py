import os
import streamlit as st
import json
import openAiKey
import openai
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

# Set OpenAI API key
openai.api_key = openAiKey.OPENAI_API_KEY

# Rest of your functions...

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

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5000,
            temperature=0.3
        )

        # Extract and display the generated response
        generated_text = response["choices"][0]["message"]["content"]

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
