import google.generativeai as genai
from datetime import datetime
from typing import Dict, Any
from backend.config import Config
from backend.database import Database

class RAGChatbot:
    def __init__(self, db: Database = None):
        self.db = db or Database()
        genai.configure(api_key=Config.GEMINI_API_KEY)
        
        # Get database date range for constraints
        data_range = self.db.get_data_range()
        self.earliest_date = data_range['earliest'] if data_range else '2018-01-01 00:00'
        self.latest_date = data_range['latest'] if data_range else datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # Define function declarations as dictionaries (new API format)
        self.tools = [
            {
                "function_declarations": [
                    {
                        "name": "query_date_range",
                        "description": f"Query PM2.5 statistics (average, min, max, count) for a specific date range. Available data: {self.earliest_date} to {self.latest_date}",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start datetime in format 'YYYY-MM-DD HH:MM'"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End datetime in format 'YYYY-MM-DD HH:MM'"
                                }
                            },
                            "required": ["start_date", "end_date"]
                        }
                    },
                    {
                        "name": "query_exact_datetime",
                        "description": "Get exact PM2.5 value at a specific datetime",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "datetime_str": {
                                    "type": "string",
                                    "description": "Datetime in format 'YYYY-MM-DD HH:MM'"
                                }
                            },
                            "required": ["datetime_str"]
                        }
                    },
                    {
                        "name": "query_worst_day",
                        "description": "Find the day with highest average PM2.5 in a date range",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in format 'YYYY-MM-DD HH:MM'"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in format 'YYYY-MM-DD HH:MM'"
                                }
                            },
                            "required": ["start_date", "end_date"]
                        }
                    },
                    {
                        "name": "query_monthly_average",
                        "description": "Get average PM2.5 for a specific month",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "year": {
                                    "type": "integer",
                                    "description": "Year (e.g., 2023)"
                                },
                                "month": {
                                    "type": "integer",
                                    "description": "Month (1-12)"
                                }
                            },
                            "required": ["year", "month"]
                        }
                    }
                ]
            }
        ]
        
        # Initialize model with tools
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=self.tools
        )
    
    def execute_function(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute the database query function"""
        try:
            if function_name == "query_date_range":
                return self.db.query_date_range(args['start_date'], args['end_date'])
            elif function_name == "query_exact_datetime":
                return self.db.query_exact_datetime(args['datetime_str'])
            elif function_name == "query_worst_day":
                return self.db.query_worst_day(args['start_date'], args['end_date'])
            elif function_name == "query_monthly_average":
                return self.db.query_monthly_average(args['year'], args['month'])
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def query_data(self, user_query: str) -> str:
        """Process user query using Gemini function calling"""
        try:
            system_instruction = f"""You are an air quality assistant analyzing PM2.5 data from Taiwan (土城 monitoring station).

Available data range: {self.earliest_date} to {self.latest_date}
Current datetime: {datetime.now().strftime('%Y-%m-%d %H:%M')}

When users ask about air quality:
1. Use the appropriate function to query the database
2. Interpret results with health context:
   - Good (0-12 μg/m³): Air quality is satisfactory
   - Moderate (13-35 μg/m³): Acceptable for most people
   - Unhealthy for Sensitive (36-55 μg/m³): May affect sensitive groups
   - Unhealthy (56-150 μg/m³): Everyone may experience health effects
   - Very Unhealthy (151-250 μg/m³): Health alert
   - Hazardous (250+ μg/m³): Emergency conditions

3. Provide concise, helpful responses (2-3 sentences)
4. If asked about dates outside available range, inform user politely"""
            
            chat = self.model.start_chat(history=[])
            full_prompt = f"{system_instruction}\n\nUser question: {user_query}"
            response = chat.send_message(full_prompt)
            
            # Handle function calls
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                
                if not response.candidates:
                    break
                    
                parts = response.candidates[0].content.parts
                if not parts:
                    break
                
                # Check for function calls
                function_calls = [part for part in parts if hasattr(part, 'function_call') and part.function_call]
                
                if not function_calls:
                    # No function calls, check for text response
                    text_parts = [part.text for part in parts if hasattr(part, 'text')]
                    if text_parts:
                        return ''.join(text_parts)
                    break
                
                # Process ALL function calls before sending back
                function_responses = []
                for part in function_calls:
                    function_call = part.function_call
                    function_name = function_call.name
                    
                    # Skip if function name is empty
                    if not function_name:
                        print(f"[WARN] Skipping function call with empty name")
                        continue
                    
                    # Check if args exists
                    if function_call.args is not None:
                        function_args = dict(function_call.args)
                    else:
                        function_args = {}
                    
                    print(f"[DEBUG] Gemini called: {function_name}({function_args})")
                    
                    # Execute function
                    result = self.execute_function(function_name, function_args)
                    print(f"[DEBUG] Function result: {result}")
                    
                    # Collect function response
                    function_responses.append({
                        "function_response": {
                            "name": function_name,
                            "response": {"result": result}
                        }
                    })
                
                # If no valid function calls were processed, break
                if not function_responses:
                    print("[WARN] No valid function calls to process")
                    break
                
                # Send ALL function responses back at once
                response = chat.send_message({"parts": function_responses})

            return "I couldn't generate a response. Please try rephrasing your question."
        
        except Exception as e:
            print(f"[ERROR] RAG query failed: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, I encountered an error processing your query. Please try again."
    
    def get_current_status(self) -> str:
        """Get current PM2.5 status with AI-generated advice"""
        try:
            latest = self.db.get_last_n_hours(1)
            if not latest:
                return "No current data available."
            
            current_pm25 = latest[0]['pm25']
            current_datetime = latest[0]['datetime']
            
            predictions = self.db.get_latest_predictions()
            next_hour = predictions[0]['predicted_pm25'] if predictions else None
            
            query = f"The current PM2.5 level is {current_pm25} μg/m³ at {current_datetime}."
            if next_hour:
                query += f" The predicted PM2.5 for the next hour is {next_hour} μg/m³."
            query += " Provide brief health advice (2 sentences max)."
            
            model_simple = genai.GenerativeModel('gemini-2.5-flash')
            response = model_simple.generate_content(query)
            return response.text
        
        except Exception as e:
            print(f"[ERROR] Status query failed: {e}")
            return "Unable to retrieve current status."