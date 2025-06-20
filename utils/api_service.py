import logging
import requests
from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)


class APIService:
    """Service class for handling direct API calls to AI providers"""
    
    @staticmethod
    def call_openai_api(env, prompt, model, temperature=0.2):
        """Direct OpenAI API call"""
        try:
            api_key = env['ir.config_parameter'].sudo().get_param('ai.openai_key')
            if not api_key:
                raise UserError(_("OpenAI API key not configured"))
            
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 4000
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                timeout=45
            )
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and result['choices']:
                return [result['choices'][0]['message']['content']]
            
            raise UserError(_("Invalid response from OpenAI API"))
            
        except requests.exceptions.Timeout:
            _logger.error("OpenAI API timeout")
            raise UserError(_("OpenAI API timeout. Please try again."))
        except requests.exceptions.HTTPError as e:
            _logger.error(f"OpenAI API HTTP error: {str(e)}")
            raise UserError(_("OpenAI API error: %s") % str(e))
        except Exception as e:
            _logger.error(f"OpenAI API error: {str(e)}")
            raise UserError(_("OpenAI API error: %s") % str(e))
    
    @staticmethod
    def call_gemini_api(env, prompt, temperature=0.2):
        """Direct Gemini API call"""
        try:
            api_key = env['ir.config_parameter'].sudo().get_param('ai.google_key')
            if not api_key:
                raise UserError(_("Google AI API key not configured"))
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 4000
                }
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=45
            )
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and result['candidates']:
                if 'content' in result['candidates'][0] and result['candidates'][0]['content']['parts']:
                    return [result['candidates'][0]['content']['parts'][0]['text']]
            
            raise UserError(_("Invalid response from Gemini API"))
            
        except requests.exceptions.Timeout:
            _logger.error("Gemini API timeout")
            raise UserError(_("Gemini API timeout. Please try again."))
        except requests.exceptions.HTTPError as e:
            _logger.error(f"Gemini API HTTP error: {str(e)}")
            raise UserError(_("Gemini API error: %s") % str(e))
        except Exception as e:
            _logger.error(f"Gemini API error: {str(e)}")
            raise UserError(_("Gemini API error: %s") % str(e))

    @staticmethod
    def get_provider_from_model(model):
        """Get the provider name from the model name"""
        PROVIDERS_MODELS = {
            'openai': {'gpt-3.5-turbo', 'gpt-4'},
            'google': {'gemini'},
        }
        for provider, models in PROVIDERS_MODELS.items():
            if model in models:
                return provider
        return None
    
    @staticmethod
    def check_api_key_for_provider(env, provider):
        """Check if API key is configured for the provider"""
        try:
            if provider == 'openai':
                api_key = env['ir.config_parameter'].sudo().get_param('ai.openai_key')
                if not api_key:
                    return "OpenAI API key not configured. Please set 'ai.openai_key' in system parameters."
            elif provider == 'google':
                api_key = env['ir.config_parameter'].sudo().get_param('ai.google_key')
                if not api_key:
                    return "Google AI API key not configured. Please set 'ai.google_key' in system parameters."
            else:
                return f"Unknown provider: {provider}"
            return None  # No error
        except Exception as e:
            return f"Failed to check API key: {str(e)}"

    @classmethod
    def call_api_by_provider(cls, env, provider, prompt, model, temperature=0.2):
        """Call API based on provider"""
        if provider == 'openai':
            return cls.call_openai_api(env, prompt, model, temperature)
        elif provider == 'google':
            return cls.call_gemini_api(env, prompt, temperature)
        else:
            raise UserError(_("Unsupported provider: %s") % provider)
