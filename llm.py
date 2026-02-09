import os
from dotenv import load_dotenv
import google.genai as genai
load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))



def call_llm(system_prompt:str,user_prompt:str)->str:

    full_prompt = f"""
    {system_prompt}

    User Task:
    {user_prompt}
    """
    

    response = client.models.generate_content(
        model = "gemini-2.0-flash",
        contents = full_prompt
    )

    return response.text
