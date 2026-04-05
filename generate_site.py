import openai
import json
import os

# Groq Configuration (TRULY FREE)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "your_groq_api_key_here")
MODEL_ID = "llama-3.3-70b-versatile"

import time

client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

def safe_json_read(filepath):
    for _ in range(5):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.5)
    return []

def safe_json_write(filepath, data):
    for _ in range(5):
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
                return True
        except PermissionError:
            time.sleep(0.5)
    return False

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
        if GROQ_API_KEY == "your_groq_api_key_here":
            raise Exception("API Key not configured")

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
        print(f"  [WARNING] AI Generation failed or key missing, using elite fallback template: {str(e)}")
        # Premium Fallback Template
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} | Elite Experience</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --primary: #00f0ff; --surface: #0a0a0c; --glass: rgba(255,255,255,0.03); }}
        body {{ background: var(--surface); color: white; font-family: 'Outfit', sans-serif; margin: 0; overflow-x: hidden; }}
        .hero {{ height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: radial-gradient(circle at center, #1a1a2e 0%, #0a0a0c 100%); text-align: center; padding: 20px; }}
        h1 {{ font-size: 5rem; margin: 0; background: linear-gradient(to right, #fff, var(--primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        p {{ color: rgba(255,255,255,0.6); font-size: 1.2rem; max-width: 600px; }}
        .badge {{ background: var(--primary); color: black; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 20px; }}
        .btn {{ margin-top: 30px; padding: 15px 40px; background: rgba(255,255,255,0.05); border: 1px solid var(--primary); color: var(--primary); border-radius: 50px; font-weight: bold; cursor: pointer; transition: all 0.3s; text-decoration: none; }}
        .btn:hover {{ background: var(--primary); color: black; box-shadow: 0 0 30px var(--primary); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; padding: 100px 50px; background: #070708; }}
        .card {{ background: var(--glass); border: 1px solid rgba(255,255,255,0.05); padding: 30px; border-radius: 30px; transition: 0.3s; }}
        .card:hover {{ border-color: var(--primary); transform: translateY(-10px); }}
    </style>
</head>
<body>
    <section class="hero">
        <div class="badge">Elite Partner in {city}</div>
        <h1>{name}</h1>
        <p>Experience the pinnacle of {niche} in {address}. We are recognized for our 4.0+ Star reputation and commitment to excellence.</p>
        <a href="tel:{phone}" class="btn">Connect Now</a>
    </section>
    <div class="grid">
        <div class="card"><h3>Premium Excellence</h3><p>Providing top-tier {niche} solutions tailored for the elite residents of {city}.</p></div>
        <div class="card"><h3>Verified Authority</h3><p>Consistent high-quality service with a proven track record in the {city} community.</p></div>
        <div class="card"><h3>Modern Innovation</h3><p>Utilizing state-of-the-art technology to redefine the {niche} experience.</p></div>
    </div>
</body>
</html>"""

def save_all_sites():
    os.makedirs("sites", exist_ok=True)
    
    leads = safe_json_read("leads.json")
    
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
    safe_json_write("leads.json", leads)
    
    print(f"\nWebsites generation attempt complete!")

import argparse

def save_single_site(index):
    os.makedirs("sites", exist_ok=True)
    
    leads = safe_json_read("leads.json")
    
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
    safe_json_write("leads.json", leads)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, help="Index of the lead to generate site for")
    args = parser.parse_args()

    if args.index is not None:
        save_single_site(args.index)
    else:
        save_all_sites()
