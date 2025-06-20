import logging
import json
import requests
import importlib
from odoo.exceptions import UserError
from odoo import _
from .api_service import APIService
from .prompt_service import PromptService
from .context_service import ContextService

_logger = logging.getLogger(__name__)


class ExtractionService:
    """Service class for handling document extraction with AI models"""
    
    @staticmethod
    def parse_ai_response_to_json(response_text):
        """
        Parse AI response text to JSON, handling markdown formatting and fallback to raw text
        
        Args:
            response_text (str): The raw response text from AI API
            
        Returns:
            dict or str: Parsed JSON object if successful, otherwise raw text
        """
        if not response_text:
            return response_text
            
        try:
            # Remove any markdown formatting if present
            cleaned_text = response_text
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text.replace('```', '').strip()
            
            # Parse and return the clean JSON
            return json.loads(cleaned_text)
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, return the raw response text
            return response_text
    
    @staticmethod
    def extract_data_from_attachment(env, agent, file_info, record_info=None):
        """Main method to extract structured data from attachment using AI models"""
        if not agent.llm_model:
            raise UserError(_("No LLM model configured for this agent"))
        
        # For Gemini models, use the external service Gemini API processing
        if 'gemini' in agent.llm_model.lower():
            return ExtractionService.extract_with_gemini_api(env, agent, file_info, record_info)
        
        # For non-Gemini models, use the original AI module methods
        return ExtractionService.extract_with_original_ai_module(env, agent, file_info, record_info)
    
    @staticmethod
    def extract_with_gemini_api(env, agent, file_info, record_info):
        """Extract data using Gemini API (including 2.0 Flash)"""
        try:
            # Get the Google API key
            api_key = env['ir.config_parameter'].sudo().get_param('ai.google_key')
            if not api_key:
                raise UserError(_("Google AI API key not configured"))
            
            # Find the actual attachment record
            attachment = env['ir.attachment'].browse(file_info.get('attachment_id'))
            if not attachment.exists():
                return {
                    "error": "Attachment not found",
                    "filename": file_info['filename']
                }
            
            # Get context about the current Odoo record and model
            context_info = ContextService.prepare_odoo_context(record_info, attachment)
            
            # Generate prompt using the service
            prompt = PromptService.generate_prompt_for_file(agent, context_info, file_info)
            
            # Use the appropriate Gemini API endpoint
            if agent.llm_model == 'gemini-2.0-flash':
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            else:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            
            # Prepare the API payload with the file data
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": attachment.mimetype,
                                    "data": attachment.datas.decode('utf-8')  # Base64 data
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,  # Very low temperature for precise extraction
                    "maxOutputTokens": 8192,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                timeout=90  # Longer timeout for document processing
            )
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and result['candidates']:
                if 'content' in result['candidates'][0] and result['candidates'][0]['content']['parts']:
                    extracted_text = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Use the reusable JSON parsing function
                    return ExtractionService.parse_ai_response_to_json(extracted_text)
            
            raise UserError(_("Invalid response from Gemini API"))
            
        except requests.exceptions.Timeout:
            _logger.error("Gemini API timeout for document processing")
            raise UserError(_("Gemini API timeout - Document processing took too long. Try with a smaller file."))
        except requests.exceptions.HTTPError as e:
            _logger.error(f"Gemini API HTTP error: {str(e)}")
            raise UserError(_(f"Gemini API error: {str(e)}"))
        except Exception as e:
            _logger.error(f"Gemini document extraction error: {str(e)}")
            raise UserError(_(f"Document extraction error: {str(e)}"))
    
    @staticmethod
    def extract_with_original_ai_module(env, agent, file_info, record_info):
        """Extract data using the original AI module's LLMApiService directly"""
        try:
            # Check provider and API key first
            provider = APIService.get_provider_from_model(agent.llm_model)
            if not provider:
                raise UserError(_(f"No provider found for model: {agent.llm_model}"))
            
            # Check API key availability
            api_key_error = APIService.check_api_key_for_provider(env, provider)
            if api_key_error:
                raise UserError(_(api_key_error))
            
            # Prepare context and prompt
            attachment = None
            if file_info.get('attachment_id'):
                attachment = env['ir.attachment'].browse(file_info.get('attachment_id'))
                if not attachment.exists():
                    attachment = None
                    
            context_info = ContextService.prepare_odoo_context(record_info, attachment)
            
            # Generate prompt using the service
            prompt = PromptService.generate_prompt_for_file(agent, context_info, file_info)
            
            # Try to use the original AI module's LLMApiService if available
            try:
                # Check if the ai module is installed and available
                if 'ai.agent' in env:
                    # Try to get the LLMApiService class through Odoo's module system
                    ai_agent_model = env['ai.agent']
                    
                    # Try to access the LLMApiService through the ai module
                    # This will work only if the ai module (enterprise) is installed
                    ai_utils = importlib.import_module('odoo.addons.ai.utils.llm_api_service')
                    LLMApiService = ai_utils.LLMApiService
                    
                    api_service = LLMApiService(env=env, provider=provider)
                    
                    messages = [
                        {'role': 'system', 'content': f'You are an AI assistant specialized in document analysis for {context_info}'},
                        {'role': 'user', 'content': prompt}
                    ]
                    
                    api_response = api_service.get_completion(
                        model=agent.llm_model,
                        messages=messages,
                        temperature=0.2  # Low temperature for accurate extraction
                    )
                    
                    if api_response and 'choices' in api_response and api_response['choices']:
                        content = api_response['choices'][0]['message']['content']
                        # Use the reusable JSON parsing function
                        return ExtractionService.parse_ai_response_to_json(content)
                    else:
                        raise UserError(_("No valid response from API"))
                else:
                    # AI module not available, fall back to direct API calls
                    _logger.info("AI module not available, using direct API call")
                    return ExtractionService.direct_api_extraction(env, agent, file_info, record_info, provider)
                    
            except (ImportError, ModuleNotFoundError, AttributeError) as e:
                # If we can't import LLMApiService or ai module not available, fall back to direct API calls
                _logger.warning(f"Could not use AI module LLMApiService ({str(e)}), using direct API call")
                return ExtractionService.direct_api_extraction(env, agent, file_info, record_info, provider)
                    
        except Exception as e:
            # If everything fails, provide helpful error message
            _logger.error(f"Document extraction with original AI module failed: {str(e)}")
            raise UserError(_(f"Document extraction failed: {str(e)}"))
    
    @staticmethod
    def direct_api_extraction(env, agent, file_info, record_info, provider):
        """Direct API extraction without channel context"""
        try:
            # Try to get attachment if available
            attachment = None
            if file_info.get('attachment_id'):
                attachment = env['ir.attachment'].browse(file_info.get('attachment_id'))
                if not attachment.exists():
                    attachment = None
            
            context_info = ContextService.prepare_odoo_context(record_info, attachment)
            
            # Generate prompt using the service
            prompt = PromptService.generate_prompt_for_file(agent, context_info, file_info)
            
            # Call API directly based on provider using service
            response = APIService.call_api_by_provider(env, provider, prompt, agent.llm_model, 0.2)
            
            # Use the reusable JSON parsing function
            return ExtractionService.parse_ai_response_to_json(response)
            
        except Exception as e:
            _logger.error(f"Direct API extraction failed: {str(e)}")
            raise UserError(_(f"Direct API extraction failed: {str(e)}"))
