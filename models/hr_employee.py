# -*- coding: utf-8 -*-

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'ai.document.mixin']
    _description = 'Employee with AI Document Extraction'
    
    def _map_ai_extracted_data(self, extracted_data):
        """
        Maps extracted JSON data to employee fields.
        
        Even though we don't need to map data automatically to fields,
        this method is required by the AI document mixin to handle the extraction process.
        The extracted data is still stored in ai_extract_json for reference.
        """
        _logger.info(f"AI extraction completed for employee {self.name} (ID: {self.id})")
        # Data mapping can be added here if needed in the future
        return True
    
    def _get_document_type_name(self):
        """Return a human-readable document type name for the extraction prompt"""
        return "Employee Document"
