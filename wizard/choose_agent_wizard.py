import json
import base64
import requests
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ChooseAgentWizard(models.TransientModel):
    _name = 'choose.agent.wizard'
    _description = 'Choose AI Agent Wizard'

    action_type = fields.Selection([
        ('chat', 'Chat'),
        ('extract', 'Extract Data')
    ], string='Action Type', required=True, default='chat',
        help='Choose whether to chat with the AI or extract data from attachments')

    agent_id = fields.Many2one('ai.agent', string='AI Agent', required=False)
    original_params = fields.Text(string='Original Parameters')
    
    extraction_result = fields.Text(
        string='Extraction Result',
        readonly=True,
        help='JSON result from data extraction'
    )
    
    state = fields.Selection([
        ('select', 'Select Options'),
        ('result', 'Show Result')
    ], default='select', string='State')

    def action_start_process(self):
        """Start the selected process (chat or extract)"""
        self.ensure_one()
        
        if self.action_type == 'chat':
            return self._open_ai_chat()
        elif self.action_type == 'extract':
            if not self.agent_id:
                raise UserError(_("Please select an AI agent for data extraction"))
            return self._extract_data()

    def _open_ai_chat(self):
        """Open the default AI chat (original functionality)"""
        if not self.original_params:
            raise UserError(_("Missing original parameters"))
            
        # For "Chat" option, just close the wizard and let JS handle opening the chat
        return {
            'type': 'ir.actions.client',
            'tag': 'close_dialog_and_open_chat',
            'params': json.loads(self.original_params),
        }

    def _extract_data(self):
        """Extract data from attachments using the selected AI agent"""
        try:
            # Parse the original parameters to get record info
            if self.original_params:
                params = json.loads(self.original_params)
                record_model = params.get('originalRecordModel')
                record_id = params.get('originalRecordId')
            else:
                raise UserError(_("Missing original parameters"))

            if not record_model or not record_id:
                raise UserError(_("Missing record information"))

            # Get attachments from the record
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', record_model),
                ('res_id', '=', record_id)
            ])

            if not attachments:
                raise UserError(_("No attachments found for this record"))

            # Process attachments and call AI agent for extraction
            extraction_result = self._process_attachments_with_ai(attachments)
            
            # Update wizard state and show result
            self.write({
                'extraction_result': json.dumps(extraction_result, indent=2),
                'state': 'result'
            })
            
            # Return view to show the result
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'choose.agent.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_state': 'result'}
            }

        except Exception as e:
            raise UserError(_("Error during data extraction: %s") % str(e))

    def _process_attachments_with_ai(self, attachments):
        """Process attachments with the selected AI agent"""
        results = []
        
        for attachment in attachments:
            try:
                # Prepare content for AI processing
                if attachment.mimetype and 'text' in attachment.mimetype:
                    # For text files, decode content
                    content = base64.b64decode(attachment.datas).decode('utf-8')
                    file_info = {
                        'attachment_id': attachment.id,
                        'filename': attachment.name,
                        'type': 'text',
                        'content': content[:5000]  # Limit content size
                    }
                elif attachment.mimetype and ('image' in attachment.mimetype or 'pdf' in attachment.mimetype):
                    # For images and PDFs, Gemini can process them directly
                    file_info = {
                        'attachment_id': attachment.id,
                        'filename': attachment.name,
                        'type': 'binary',
                        'mimetype': attachment.mimetype,
                        'size': len(attachment.datas) if attachment.datas else 0
                    }
                else:
                    # For other file types
                    file_info = {
                        'attachment_id': attachment.id,
                        'filename': attachment.name,
                        'type': 'binary',
                        'mimetype': attachment.mimetype,
                        'size': len(attachment.datas) if attachment.datas else 0
                    }

                # Call AI agent for data extraction
                # This will preserve original API errors (missing keys, etc.) from the AI module
                ai_result = self._call_ai_for_extraction(file_info)

                results.append(ai_result)

            except UserError:
                # Re-raise UserError (like missing API key) from original AI module
                raise
            except Exception as e:
                # Only catch non-UserError exceptions for file processing issues
                # Return error in same format as AI result for consistency
                results.append({'error': str(e)})

        return results

    def _call_ai_for_extraction(self, file_info):
        """Call the AI agent to extract data from file"""
        # Parse original parameters to get record info
        record_info = None
        if self.original_params:
            params = json.loads(self.original_params)
            record_info = {
                'model': params.get('originalRecordModel'),
                'id': params.get('originalRecordId'),
                'data': params.get('originalRecordData', {})
            }
        
        return self.agent_id.extract_data_from_attachment(file_info, record_info)

    def action_back_to_selection(self):
        """Go back to selection screen"""
        self.write({'state': 'select'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'choose.agent.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }