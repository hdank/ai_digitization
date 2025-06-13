# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import base64
import logging

_logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects"""
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


class AIDocumentMixin(models.AbstractModel):
    """Abstract model to add AI document extraction capabilities"""
    _name = 'ai.document.mixin'
    _description = 'AI Document Extraction Mixin'
    
    # AI Extraction Fields
    ai_extract_state = fields.Selection([
        ('no_extract', 'No extraction'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Complete'),
        ('error', 'Error'),
    ], string='AI Extract State', default='no_extract', copy=False)
    
    ai_extract_json = fields.Text('Extracted Data (JSON)', copy=False)
    ai_extract_error = fields.Text('Extraction Error', copy=False)
    ai_has_attachments = fields.Boolean('Has Attachments', compute='_compute_ai_has_attachments')
    ai_can_extract = fields.Boolean('Can Extract', compute='_compute_ai_can_extract')
    ai_agent_id = fields.Many2one('ai.agent', string='AI Agent', help='Select the AI agent to use for document extraction')
    
    @api.depends('message_attachment_count', 'message_ids', 'message_ids.attachment_ids')
    def _compute_ai_has_attachments(self):
        """Check if this record has any attachments using multiple fallback methods"""
        for record in self:
            has_attachments = False
            
            # Method 1: Check message_attachment_count if available
            if hasattr(record, 'message_attachment_count') and record.message_attachment_count > 0:
                has_attachments = True
            
            # Method 2: Check message_ids for attachments
            elif hasattr(record, 'message_ids'):
                for message in record.message_ids:
                    if message.attachment_ids:
                        has_attachments = True
                        break
            
            # Method 3: Direct search for attachments
            if not has_attachments:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', record._name),
                    ('res_id', '=', record.id),
                ], limit=1)
                has_attachments = bool(attachments)
            
            record.ai_has_attachments = has_attachments
    
    @api.depends('ai_has_attachments', 'ai_extract_state', 'ai_agent_id')
    def _compute_ai_can_extract(self):
        """Determine if AI extraction can be performed"""
        for record in self:
            # Can extract if we have attachments, an AI agent, and we're not currently processing
            record.ai_can_extract = (
                record.ai_has_attachments and 
                record.ai_agent_id and
                record.ai_extract_state != 'processing'
            )
    
    def action_extract_document(self):
        """Trigger AI document extraction using selected AI agent"""
        self.ensure_one()
        
        if not self.ai_has_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No attachments found to extract data from.',
                    'type': 'warning',
                }
            }
        
        if not self.ai_agent_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Please select an AI agent first.',
                    'type': 'warning',
                }
            }
        
        try:
            # Set state to processing
            self.ai_extract_state = 'processing'
            
            # Get attachments
            attachments = self._get_document_attachments()
            
            if not attachments:
                raise Exception("No valid attachments found for extraction")
            
            # Perform AI extraction using the selected AI agent
            extracted_data = self._perform_ai_extraction_with_agent(attachments)
            
            # Store results
            self.ai_extract_json = json.dumps(extracted_data, indent=2, cls=DateTimeEncoder)
            self.ai_extract_state = 'done'
            self.ai_extract_error = False
            
            # Map extracted data to model fields
            self._map_ai_extracted_data(extracted_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'AI extraction completed successfully!',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            _logger.error(f"AI extraction failed for {self._name} {self.id}: {str(e)}")
            self.ai_extract_state = 'error'
            self.ai_extract_error = str(e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'AI extraction failed: {str(e)}',
                    'type': 'danger',
                }
            }
    
    def _get_document_attachments(self):
        """Get attachments for extraction - prioritize PDF/images"""
        self.ensure_one()
        
        # Search for attachments
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ])
        
        # Filter for extractable file types (PDF, images)
        extractable_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
        extractable_attachments = attachments.filtered(
            lambda a: a.mimetype in extractable_types
        )
        
        return extractable_attachments or attachments  # Fallback to all attachments
    
    def _perform_ai_extraction_with_agent(self, attachments):
        """Perform AI extraction using the selected AI agent"""
        if not self.ai_agent_id:
            raise ValueError("No AI agent selected for extraction")
        
        # Check if AI module is available
        if 'ai.agent' not in self.env:
            raise ImportError("AI module not available")
        
        try:
            ai_agent = self.ai_agent_id
            prompt = self._build_extraction_prompt()
            extraction_results = []
            
            # Process each attachment
            for attachment in attachments:
                try:
                    # Get attachment content
                    attachment_data = self._extract_attachment_content(attachment)
                    
                    # Process through AI
                    result = self._call_ai_agent_properly(ai_agent, prompt, attachment_data)
                    
                    # Store result
                    extraction_results.append({
                        'attachment_name': attachment.name,
                        'attachment_id': attachment.id,
                        'extracted_data': result,
                        'timestamp': fields.Datetime.now().isoformat()
                    })
                except Exception as attachment_error:
                    _logger.warning("Failed to extract from attachment %s: %s", 
                                   attachment.name, str(attachment_error))
                    extraction_results.append({
                        'attachment_name': attachment.name,
                        'attachment_id': attachment.id,
                        'error': str(attachment_error)
                    })
            
            # Format complete result
            return {
                "extraction_timestamp": fields.Datetime.now().isoformat(),
                "model_type": self._name,
                "ai_agent_name": ai_agent.name,
                "ai_agent_id": ai_agent.id,
                "results": extraction_results,
                "status": "success" if extraction_results else "no_results",
                "message": f"Extraction complete using {ai_agent.name}"
            }
            
        except Exception as e:
            _logger.error("AI extraction failed: %s", str(e))
            raise ValueError(f"AI extraction failed: {str(e)}")
    
    def _call_ai_agent_properly(self, agent, prompt, attachment_data):
        """Call the AI agent to process the document using the AI module"""
        try:
            # Create a temporary discussion channel required by the AI agent's _generate_response
            channel = self.env['discuss.channel']._get_or_create_chat([
                self.env.user.partner_id.id,
                agent.partner_id.id
            ])
            
            # Build the combined prompt with document content
            full_prompt = f"{prompt}\n\nDocument content:\n{attachment_data}"
            
            # Call the AI agent's response generation method
            response_messages = agent._generate_response(
                prompt=full_prompt,
                ai_agent=agent,
                discuss_channel_id=channel
            )
            
            # Clean up the temporary channel
            try:
                channel.sudo().unlink()
            except Exception:
                _logger.debug("Non-critical channel cleanup error")
            
            # Process the AI response
            if not response_messages:
                return {"error": "No response received from AI model"}
                
            response_text = response_messages[0] if isinstance(response_messages, list) else str(response_messages)
            
            # Try to extract structured JSON data
            try:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                
                # If no JSON found, return formatted response
                return {
                    "ai_response": response_text,
                    "parsing_note": "Could not find JSON in response"
                }
            except json.JSONDecodeError:
                # Return raw response if JSON parsing fails
                return {
                    "ai_response": response_text,
                    "parsing_note": "JSON parsing failed"
                }
                
        except Exception as e:
            _logger.error("AI agent processing error: %s", str(e))
            return {
                "error": "AI processing failed",
                "error_details": str(e)
            }
    
    def _build_extraction_prompt(self):
        """Build the prompt for AI document extraction"""
        document_type = self._get_odoo_model_name()
        
        return f"""Extract relevant information from the following document and return it as structured JSON data.
The document relates to a {document_type} record in an enterprise system.

INSTRUCTIONS:
1. Focus on extracting key information relevant to {document_type}
2. Return ONLY valid JSON format (no explanations, no markdown formatting)
3. Use appropriate field names for the JSON properties
4. For dates, use ISO format (YYYY-MM-DD) when possible
5. For unclear or missing information, use null values

The document content follows below."""
    
    def _extract_attachment_content(self, attachment):
        """Extract text content from attachments for AI processing"""
        try:
            # Check for indexed content first (works for PDFs, Word docs, etc.)
            if hasattr(attachment, 'index_content') and attachment.index_content:
                content = attachment.index_content.strip()
                if content and len(content) > 50:  # Meaningful content check
                    doc_type = self._get_document_type_from_mimetype(attachment.mimetype)
                    return f"{doc_type} Content:\n{content}"
            
            # Handle specific file types
            if attachment.mimetype.startswith('text/'):
                # For text files, decode content
                try:
                    content = base64.b64decode(attachment.datas).decode('utf-8')
                    return f"Text Document Content:\n{content}"
                except UnicodeDecodeError:
                    # Try another encoding if UTF-8 fails
                    content = base64.b64decode(attachment.datas).decode('latin-1', errors='replace')
                    return f"Text Document Content:\n{content}"
                        
            # Return metadata for all other file types
            doc_type = self._get_document_type_from_mimetype(attachment.mimetype)
            return f"{doc_type}: {attachment.name}\nType: {attachment.mimetype}\nSize: {attachment.file_size} bytes"
                
        except Exception as e:
            _logger.warning("Content extraction failed for %s: %s", attachment.name, str(e))
            return f"Document: {attachment.name}\nExtraction Error: {str(e)}"
    
    def _get_odoo_model_name(self):
        """Get the name of the Odoo model for document extraction prompts"""
        return self._name
    
    def _get_document_type_name(self):
        """Get a human-readable document type name for the current model"""
        model_name = self._name
        # Convert technical name to human readable
        if model_name == 'hr.employee':
            return "Employee Document"
        elif model_name == 'res.partner':
            return "Partner/Contact Document"
        elif model_name == 'account.move':
            return "Invoice/Bill Document"
        else:
            # Default: convert snake_case to Title Case
            # Remove anything after the first dot
            if '.' in model_name:
                model_name = model_name.split('.')[1]
            return ' '.join(word.capitalize() for word in model_name.split('_')) + " Document"
    
    def _get_document_type_from_mimetype(self, mimetype):
        """Helper method to get human-readable document type name from mimetype"""
        if mimetype == 'application/pdf':
            return "PDF Document"
        elif mimetype.startswith('image/'):
            return "Image Document"
        elif mimetype in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return "Word Document"
        elif mimetype.startswith('text/'):
            return "Text Document"
        elif mimetype.startswith('application/vnd.ms-excel') or mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            return "Excel Document"
        else:
            return "Document"
    
    def _map_ai_extracted_data(self, extracted_data):
        """
        Map extracted JSON data to model fields.
        This should be implemented by inheriting models.
        """
        # Default implementation - do nothing
        # Inheriting models should override this method
        pass

    def action_open_extract_wizard(self):
        """Open the AI extraction wizard to select an AI agent"""
        self.ensure_one()
        
        if not self.ai_has_attachments:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No attachments found to extract data from. Please upload documents first.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'name': _('AI Document Extraction'),
            'type': 'ir.actions.act_window',
            'res_model': 'ai.extraction.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_record_id': self.id,
                'default_record_model': self._name,
                'default_ai_agent_id': self.ai_agent_id.id if self.ai_agent_id else False,
            }
        }