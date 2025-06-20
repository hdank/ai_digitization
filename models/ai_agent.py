from odoo import models, api, fields, _
import logging

from odoo.exceptions import UserError
from ..utils import ExtractionService

_logger = logging.getLogger(__name__)


class AIAgent(models.Model):
    _inherit = 'ai.agent'

    is_document_extraction = fields.Boolean(
        string="Document Extraction Agent",
        default=False,
        help="Mark this agent as specialized in document extraction"
    )

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
    
    def extract_data_from_attachment(self, file_info, record_info=None):
        """Extract structured data from attachment using AI models (Enhanced to support all models)"""
        if not self.llm_model:
            raise UserError(_("No LLM model configured for this agent"))
        
        # Use the ExtractionService to handle all extraction logic
        return ExtractionService.extract_data_from_attachment(self.env, self, file_info, record_info)
    
    @api.model
    def get_available_agents_for_selection(self):
        """Get agents available for user selection"""
        agents = self.search([])
        return [{
            'id': agent.id,
            'name': agent.name,
            'subtitle': agent.subtitle or '',
            'llm_model': agent.llm_model,
            'system_prompt': agent.system_prompt[:100] + '...' if agent.system_prompt and len(agent.system_prompt) > 100 else agent.system_prompt or '',
        } for agent in agents]