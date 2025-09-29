import os
import json
import re
from openai import OpenAI
from langfuse.decorators import observe, langfuse_context

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@observe(name="llm_data_extraction")
def extract_user_data(user_input: str) -> dict:
    """
    Extract structured data from user's natural language input using OpenAI.
    
    Args:
        user_input: Natural language description from user
        
    Returns:
        Dictionary with extracted data: gender, age, time_5km_seconds
    """
    
    system_prompt = """Jesteś asystentem ekstrakcji danych dla systemu predykcji półmaratonu.

Twoim zadaniem jest wydobycie następujących informacji z tekstu użytkownika:
1. Płeć (mężczyzna/kobieta/M/K)
2. Wiek (w latach, jako liczba całkowita)
3. Czas biegu na 5km (przekonwertuj na sekundy jako liczba całkowita)

Formaty czasu które możesz napotkać:
- "23:45" lub "23 minuty 45 sekund" = 1425 sekund
- "27 minut" = 1620 sekund
- "0:24:30" lub "24:30" = 1470 sekund

Zwróć TYLKO prawidłowy obiekt JSON z tą dokładną strukturą:
{
    "gender": "male" lub "female" lub null,
    "age": liczba całkowita lub null,
    "time_5km_seconds": liczba całkowita lub null
}

Zasady:
- Przekonwertuj każdy wariant płci (M/K/mężczyzna/kobieta/męski/żeński) na "male" lub "female"
- Wiek musi być rozsądną liczbą (15-90 lat)
- Czas musi być przekonwertowany na całkowitą liczbę sekund
- Jeśli informacja brakuje lub jest niejasna, użyj null
- Zwróć TYLKO obiekt JSON, bez wyjaśnień

Przykłady:

Wejście: "Jestem 30-letnim mężczyzną i mój czas na 5km to 23:45"
Wyjście: {"gender": "male", "age": 30, "time_5km_seconds": 1425}

Wejście: "28-letnia kobieta, biegam 5km w 27 minut"
Wyjście: {"gender": "female", "age": 28, "time_5km_seconds": 1620}

Wejście: "Biegacz męski, wiek 45"
Wyjście: {"gender": "male", "age": 45, "time_5km_seconds": null}"""

    try:
        # Track LLM call with Langfuse
        langfuse_context.update_current_observation(
            input=user_input,
            metadata={"model": "gpt-4o-mini", "task": "data_extraction"}
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            extracted_data = json.loads(json_str)
        else:
            extracted_data = json.loads(response_text)
        
        # Validate and normalize data
        result = {
            'gender': None,
            'age': None,
            'time_5km_seconds': None
        }
        
        # Validate gender
        if extracted_data.get('gender'):
            gender = str(extracted_data['gender']).lower()
            if gender in ['male', 'm', 'man', 'męski', 'mężczyzna']:
                result['gender'] = 'male'
            elif gender in ['female', 'f', 'woman', 'kobieta', 'żeński']:
                result['gender'] = 'female'
        
        # Validate age
        if extracted_data.get('age'):
            age = int(extracted_data['age'])
            if 15 <= age <= 90:
                result['age'] = age
        
        # Validate 5km time
        if extracted_data.get('time_5km_seconds'):
            time_seconds = int(extracted_data['time_5km_seconds'])
            # Reasonable 5km time: 15 minutes (900s) to 60 minutes (3600s)
            if 900 <= time_seconds <= 3600:
                result['time_5km_seconds'] = time_seconds
        
        # Track output
        langfuse_context.update_current_observation(
            output=result,
            metadata={
                "tokens_used": response.usage.total_tokens,
                "raw_response": response_text
            }
        )
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response was: {response_text}")
        
        langfuse_context.update_current_observation(
            output={"error": "json_parse_error"},
            level="ERROR"
        )
        
        return {
            'gender': None,
            'age': None,
            'time_5km_seconds': None
        }
        
    except Exception as e:
        print(f"Error in extract_user_data: {e}")
        
        langfuse_context.update_current_observation(
            output={"error": str(e)},
            level="ERROR"
        )
        
        return {
            'gender': None,
            'age': None,
            'time_5km_seconds': None
        }


def parse_time_to_seconds(time_str: str) -> int:
    """
    Fallback function to parse time strings to seconds.
    
    Args:
        time_str: Time string in various formats
        
    Returns:
        Time in seconds
    """
    try:
        # Remove common words
        time_str = time_str.lower().replace('minutes', '').replace('seconds', '').replace('min', '').replace('sec', '').strip()
        
        # Format: MM:SS or HH:MM:SS
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        # Format: just minutes as number
        time_num = float(time_str)
        if time_num < 100:  # Assume it's minutes if less than 100
            return int(time_num * 60)
        else:  # Assume it's seconds if greater than 100
            return int(time_num)
            
    except:
        return None