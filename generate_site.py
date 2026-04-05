import openai
import json
import os

# Groq Configuration (TRULY FREE)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "your_groq_api_key_here")
MODEL_ID = "llama-3.3-70b-versatile"

client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

def generate_website(lead):
    # Field Fallbacks to prevent KeyErrors
    name = lead.get('name', 'Elite Business')
    niche = lead.get('niche', lead.get('search_query', 'Professional Service').split(' in ')[0])
    city = lead.get('city', 'Your City')
    address = lead.get('address', 'Local Area')
    phone = lead.get('phone', 'Available on Request')
    
    print(f"  [WORKFLOW_STEP_1] Generating elite website for {name} ({niche})...")
    
    prompt = f"""Create a complete, premium, high-converting one-page HTML website for a local business.
    
    Business details:
    - Name: {name}
    - Category: {niche}
    - Location: {city}
    - Full Address: {address}
    - Phone: {phone}
    
    Design Requirements:
    - Use a extremely premium, modern aesthetic (Glassmorphism, sleek gradients, deep offsets).
    - Use Inter/Outfit fonts via Google Fonts.
    - All CSS must be INLINE inside a <style> tag.
    - Include:
        1. A Hero section with a massive, punchy headline like "The Best {niche} in {city}".
        2. A "Trust & Reputation" section mentioning their 4.0+ Star Rating.
        3. A "Services" grid with 6 relevant services for a {niche}.
        4. A "Book Appointment" button that pops up the phone number {phone}.
    - The colors should be professional (e.g., Deep Blues and Gold for Lawyers, Clean Teal and White for Dentists).
    - Make it fully mobile responsive.
    
    IMPORTANT: Return ONLY the raw HTML. No markdown, no "Here is your code". Start with <!DOCTYPE html>."""

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}]
        )
        html_content = response.choices[0].message.content
        
        # Clean up if model added markdown backticks
        if "```html" in html_content:
            html_content = html_content.split("```html")[-1].split("```")[0].strip()
        elif "```" in html_content:
            html_content = html_content.split("```")[-1].split("```")[0].strip()
            
        return html_content
    except Exception as e:
        print(f"  [ERROR] AI Generation failed: {str(e)}")
        raise e

def save_all_sites():
    os.makedirs("sites", exist_ok=True)
    
    with open("leads.json", "r") as f:
        leads = json.load(f)
    
    for lead in leads:
        safe_name = lead['name'].replace(" ", "_").replace("/", "_")
        filepath = f"sites/{safe_name}.html"
        
        try:
            html = generate_website(lead)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            lead['html_file'] = filepath
            print(f"  Saved: {filepath}")
        except Exception as e:
            print(f"  Failed: {lead['name']} - {e}")
    
    # Save updated leads with file paths
    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=2)
    
    print(f"\nWebsites generation attempt complete!")

import argparse

def save_single_site(index):
    os.makedirs("sites", exist_ok=True)
    
    with open("leads.json", "r") as f:
        leads = json.load(f)
    
    if index < 0 or index >= len(leads):
        print(f"Error: Index {index} out of range.")
        return

    lead = leads[index]
    safe_name = lead['name'].replace(" ", "_").replace("/", "_")
    filepath = f"sites/{safe_name}.html"
    
    html = generate_website(lead)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    lead['html_file'] = filepath
    print(f"  Saved: {filepath}")
    
    # Save updated leads with file paths
    with open("leads.json", "w") as f:
        json.dump(leads, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, help="Index of the lead to generate site for")
    args = parser.parse_args()

    if args.index is not None:
        save_single_site(args.index)
    else:
        save_all_sites()
