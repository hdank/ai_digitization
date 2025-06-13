# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AIAgent(models.Model):
    _inherit = 'ai.agent'
    
    @api.model
    def _get_llm_model_selection(self):
        """Add 'gemini-2.0-flash' to the LLM model options"""
        selections = super()._get_llm_model_selection()
        # Check if our model is already in the list
        for model_tuple in selections:
            if model_tuple[0] == 'gemini-2.0-flash':
                return selections
        # If not in the list, add it
        selections.append(('gemini-2.0-flash', 'Gemini 2.0 Flash'))
        return selections
    
    # Redefine the llm_model field to use our updated selection method
    llm_model = fields.Selection(
        selection=_get_llm_model_selection,
        string="LLM Model",
        required=True,
    )
    
    def _generate_response(self, prompt, ai_agent, discuss_channel_id):
        """Handle the gemini-2.0-flash model"""
        if ai_agent.llm_model == 'gemini-2.0-flash':
            return self._call_gemini_flash_api(prompt)
        return super()._generate_response(prompt, ai_agent, discuss_channel_id)
        
    def _call_gemini_flash_api(self, prompt):
        """Call the Gemini 2.0 Flash API for document extraction"""
        try:
            # Get the Google API key
            api_key = self.env['ir.config_parameter'].sudo().get_param('ai.google_key')
            if not api_key:
                raise UserError(_("Google AI API key not configured"))
            
            # Use the Google AI API endpoint for Gemini 2.0 Flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            
            # Prepare API payload with optimized settings for document extraction
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,  # Lower temperature for more accurate extraction
                    "maxOutputTokens": 8192,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            # Make the API request
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                timeout=45  # Longer timeout for document processing
            )
            response.raise_for_status()
            
            # Process response
            result = response.json()
            if 'candidates' in result and result['candidates']:
                if 'content' in result['candidates'][0] and result['candidates'][0]['content']['parts']:
                    return [result['candidates'][0]['content']['parts'][0]['text']]
            
            raise UserError(_("Invalid response from Gemini 2.0 Flash API"))
            
        except requests.exceptions.Timeout:
            _logger.error("Gemini 2.0 Flash API timeout")
            raise UserError(_("Gemini 2.0 Flash API timeout. Please try again with a smaller document."))
        except requests.exceptions.HTTPError as e:
            _logger.error(f"Gemini Flash API HTTP error: {str(e)}")
            raise UserError(_("Gemini 2.0 Flash API error: %s") % str(e))
        except Exception as e:
            _logger.error(f"Gemini Flash API error: {str(e)}")
            raise UserError(_("Gemini 2.0 Flash API error: %s") % str(e))
    
