# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AIExtractionWizard(models.TransientModel):
    _name = 'ai.extraction.wizard'
    _description = 'AI Document Extraction Wizard'
    
    ai_agent_id = fields.Many2one(
        'ai.agent', 
        string='AI Agent', 
        required=True,
        help='Select the AI agent to use for document extraction'
    )
    
    record_id = fields.Integer('Record ID', required=True)
    record_model = fields.Char('Record Model', required=True)
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from the active record"""
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if active_model and active_id:
            record = self.env[active_model].browse(active_id)
            res.update({
                'record_id': active_id,
                'record_model': active_model,
            })
            
            # If the record already has an AI agent selected, use it as default
            if hasattr(record, 'ai_agent_id') and record.ai_agent_id:
                res['ai_agent_id'] = record.ai_agent_id.id
        
        return res
    
    def action_extract_document(self):
        """Trigger AI document extraction on the source record"""
        self.ensure_one()
        
        if not self.record_id or not self.record_model:
            raise UserError(_("Missing record information"))
        
        record = self.env[self.record_model].browse(self.record_id)
        
        # Check if record exists
        if not record.exists():
            raise UserError(_("Record not found"))
            
        # Check for attachments
        if not record.ai_has_attachments:
            raise UserError(_("No documents found to extract data from. Please upload documents first."))
            
        # Set AI agent on record
        record.ai_agent_id = self.ai_agent_id
        
        # Execute extraction
        return record.action_extract_document()
